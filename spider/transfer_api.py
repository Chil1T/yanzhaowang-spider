#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调剂信息 API 爬虫（会话复用版）
"""
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import config
from handlers.excel_handler import ExcelHandler
from handlers.logger_handler import LoggerHandler
from spider.exceptions import DriverInitializationError, LoginError
from spider.utils import resolve_chromedriver_path


DEFAULT_TRANSFER_EXPORT_BASE_FIELDS = [
    "ID",
    "省市代码",
    "招生单位代码",
    "招生单位",
    "院系所代码",
    "院系所",
    "专业代码",
    "专业",
    "研究方向代码",
    "研究方向",
    "学习方式代码",
    "学习方式",
    "专项计划代码",
    "专项计划",
    "余额状态",
    "缺额人数",
    "发布时间",
    "备注",
    "申请条件摘要",
]

DEFAULT_TRANSFER_EXPORT_DETAIL_FIELDS = [
    "详情_特殊说明",
    "详情_初试学位类型要求",
    "详情_初试门类一级学科专业要求",
    "详情_初试科目要求",
    "详情_总分要求",
    "详情_政治要求",
    "详情_外语要求",
    "详情_科目三要求",
    "详情_科目四要求",
    "详情_考生编号",
    "详情_本科门类代码",
    "详情_本科门类",
    "详情_本科专业代码",
    "详情_本科专业",
    "详情_学习方式代码",
]


class TransferApiSpider:
    """调剂信息 API 爬虫（支持连续抓取并复用登录态）"""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.logger = LoggerHandler(__name__)
        self.driver: Optional[webdriver.Chrome] = None
        self.cookie_header = ""
        self.session_ready = False
        self.start_hidden = bool(getattr(config, "TRANSFER_BROWSER_START_HIDDEN", True))
        self.suppress_driver_logs = bool(getattr(config, "TRANSFER_SUPPRESS_DRIVER_LOGS", True))
        self.hidden_position = getattr(config, "TRANSFER_BROWSER_HIDDEN_POSITION", (-32000, -32000))
        self.visible_position = getattr(config, "TRANSFER_BROWSER_VISIBLE_POSITION", (80, 60))
        self.visible_size = getattr(config, "TRANSFER_BROWSER_VISIBLE_SIZE", (1366, 900))

        # 单次任务配置（每次 run_task 覆盖）
        self.query_mode = "precise"
        self.filters: Dict[str, str] = {}
        self.include_detail = False
        self.page_size = 20
        self.output_file = ""
        self.rows: List[Dict[str, Any]] = []
        self.export_base_fields = self._resolve_export_fields(
            getattr(config, "TRANSFER_EXPORT_BASE_FIELDS", DEFAULT_TRANSFER_EXPORT_BASE_FIELDS),
            DEFAULT_TRANSFER_EXPORT_BASE_FIELDS,
        )
        self.export_detail_fields = self._resolve_export_fields(
            getattr(config, "TRANSFER_EXPORT_DETAIL_FIELDS", DEFAULT_TRANSFER_EXPORT_DETAIL_FIELDS),
            DEFAULT_TRANSFER_EXPORT_DETAIL_FIELDS,
        )

        self._setup_driver()

    def _resolve_export_fields(self, configured: Any, fallback: List[str]) -> List[str]:
        """解析导出字段配置并回退默认值"""
        if not isinstance(configured, list):
            return list(fallback)

        fields: List[str] = []
        for field in configured:
            field_name = str(field).strip()
            if field_name and field_name not in fields:
                fields.append(field_name)

        return fields if fields else list(fallback)

    def _setup_driver(self):
        """初始化浏览器驱动"""
        def build_options(minimal: bool) -> Options:
            opts = Options()
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--remote-allow-origins=*")
            opts.add_argument("--no-first-run")
            opts.add_argument("--no-default-browser-check")
            opts.add_argument("--disable-logging")
            opts.add_argument("--log-level=3")

            if self.headless:
                opts.add_argument("--headless")
                opts.add_argument("--disable-gpu")

            if self.start_hidden and not self.headless:
                opts.add_argument(
                    f"--window-position={self.hidden_position[0]},{self.hidden_position[1]}"
                )
                opts.add_argument("--window-size=1280,900")

            if minimal:
                opts.add_argument("--disable-extensions")
                opts.add_argument("--disable-background-networking")
            else:
                opts.add_argument("--disable-blink-features=AutomationControlled")
                opts.add_experimental_option(
                    "excludeSwitches",
                    ["enable-automation", "enable-logging"],
                )
                opts.add_experimental_option("useAutomationExtension", False)
                opts.add_argument(
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            return opts

        def start_with_executable(executable_path: str, strategy_name: str) -> Optional[webdriver.Chrome]:
            for minimal in (False, True):
                try:
                    service = Service(
                        executable_path=executable_path,
                        log_output=(subprocess.DEVNULL if self.suppress_driver_logs else None),
                    )
                    return webdriver.Chrome(service=service, options=build_options(minimal))
                except Exception as e:
                    mode_name = "最小参数" if minimal else "默认参数"
                    errors.append(f"{strategy_name}({mode_name})失败: {e}")
            return None

        def start_with_manager(strategy_name: str) -> Optional[webdriver.Chrome]:
            for minimal in (False, True):
                try:
                    service = Service(
                        log_output=(subprocess.DEVNULL if self.suppress_driver_logs else None)
                    )
                    return webdriver.Chrome(service=service, options=build_options(minimal))
                except Exception as e:
                    mode_name = "最小参数" if minimal else "默认参数"
                    errors.append(f"{strategy_name}({mode_name})失败: {e}")
            return None

        errors: List[str] = []

        configured_driver = getattr(config, "CHROME_DRIVER_PATH", "")
        if configured_driver:
            if os.path.exists(configured_driver):
                self.driver = start_with_executable(configured_driver, "配置路径驱动")
            else:
                errors.append(f"配置路径不存在: {configured_driver}")

        if self.driver is None:
            self.driver = start_with_manager("Selenium Manager")

        if self.driver is None:
            try:
                manager_path = ChromeDriverManager().install()
                driver_path = resolve_chromedriver_path(manager_path)
                self.driver = start_with_executable(driver_path, "webdriver-manager")
            except Exception as e:
                errors.append(f"webdriver-manager 安装失败: {e}")

        if self.driver is None:
            error_text = " | ".join(errors) if errors else "未知错误"
            raise DriverInitializationError(f"初始化浏览器失败: {error_text}")

        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        if self.start_hidden and not self.headless:
            self._hide_browser_window()

    def _hide_browser_window(self):
        """将浏览器窗口移到屏幕外，减少干扰"""
        if not self.driver or self.headless:
            return
        try:
            x, y = int(self.hidden_position[0]), int(self.hidden_position[1])
            self.driver.set_window_position(x, y)
        except Exception:
            pass

    def _show_browser_window(self):
        """将浏览器窗口恢复到可见区域，用于手动登录"""
        if not self.driver or self.headless:
            return
        try:
            x, y = int(self.visible_position[0]), int(self.visible_position[1])
            width, height = int(self.visible_size[0]), int(self.visible_size[1])
            self.driver.set_window_position(x, y)
            self.driver.set_window_size(width, height)
            self.driver.maximize_window()
        except Exception:
            pass

    def _build_cookie_header(self) -> str:
        """从浏览器提取 Cookie 字符串"""
        assert self.driver is not None
        cookies = self.driver.get_cookies()
        parts = []
        for cookie in cookies:
            name = cookie.get("name", "")
            value = cookie.get("value", "")
            if name:
                parts.append(f"{name}={value}")
        return "; ".join(parts)

    def _ensure_logged_in(self):
        """确保已登录。首次必登，后续复用会话。"""
        assert self.driver is not None
        self.driver.get(config.TRANSFER_URLS["query_page"])
        time.sleep(2)

        current_url = self.driver.current_url
        page_title = self.driver.title
        page_source = self.driver.page_source

        need_login = (
            "account.chsi.com.cn" in current_url
            or "登录" in page_title
            or "调剂意向余额查询" not in page_source
        )

        if need_login:
            if self.session_ready:
                self.logger.warning("检测到登录态失效，请重新登录")
            self._show_browser_window()
            self.logger.warning("=" * 60)
            self.logger.warning("请在浏览器中完成登录，登录后按回车继续...")
            self.logger.warning("=" * 60)
            input()
            self.driver.get(config.TRANSFER_URLS["query_page"])
            time.sleep(2)

            current_url = self.driver.current_url
            page_source = self.driver.page_source
            if "account.chsi.com.cn" in current_url or "调剂意向余额查询" not in page_source:
                raise LoginError("未检测到有效登录态，请确认登录成功")

        self.cookie_header = self._build_cookie_header()
        self.session_ready = True
        if self.start_hidden:
            self._hide_browser_window()

    def _request_json(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """发送请求并解析 JSON"""
        body = None
        if data is not None:
            encoded = urllib.parse.urlencode(data)
            body = encoded.encode("utf-8")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": config.TRANSFER_URLS["query_page"],
            "Origin": "https://yz.chsi.com.cn",
            "Cookie": self.cookie_header,
            "Accept-Encoding": "identity",
        }

        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded;charset=UTF-8"

        req = urllib.request.Request(
            url=url,
            data=body,
            headers=headers,
            method=method,
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return json.loads(text)

    def _sanitize_filename_part(self, value: str) -> str:
        """清理文件名片段"""
        if value is None:
            return ""
        cleaned = re.sub(r"[\\/:*?\"<>|]", "_", str(value).strip())
        cleaned = re.sub(r"\s+", "", cleaned)
        return cleaned[:24]

    def _build_output_filename(self) -> str:
        """构建导出文件名（含关键词+月日小时+筛选参数）"""
        now = time.localtime()
        month = f"{now.tm_mon:02d}"
        day = f"{now.tm_mday:02d}"
        hour = f"{now.tm_hour:02d}"
        minute = f"{now.tm_min:02d}"

        keyword = self.filters.get("zymc") or self.filters.get("dwmc2") or self.filters.get("dwmc") or "关键词空"
        keyword = self._sanitize_filename_part(keyword)
        mode_name = "精准" if self.query_mode == "precise" else "模糊"
        detail_flag = "含详情" if self.include_detail else "仅列表"

        parts = []
        if self.query_mode == "precise":
            keys = ["ssdm", "dwmc", "xxfs", "zxjh", "zymc"]
        else:
            keys = ["ssdm2", "mldm2", "xxfs2", "zxjh2", "dwmc2", "fhbktj"]

        for key in keys:
            value = self.filters.get(key, "")
            if value:
                parts.append(f"{key}-{self._sanitize_filename_part(value)}")

        parts.append(f"ps-{self.page_size}")
        params_part = "_".join(parts)[:120] if parts else "默认参数"

        return (
            f"data/调剂_{mode_name}_{keyword}_M{month}D{day}H{hour}M{minute}_"
            f"{detail_flag}_{params_part}.xlsx"
        )

    def _build_query_payload(self, start: int) -> Dict[str, str]:
        """构建查询参数"""
        if self.query_mode == "precise":
            return {
                "orderBy": self.filters.get("orderBy", ""),
                "ssdm": self.filters.get("ssdm", ""),
                "dwmc": self.filters.get("dwmc", ""),
                "xxfs": self.filters.get("xxfs", ""),
                "zxjh": self.filters.get("zxjh", ""),
                "zymc": self.filters.get("zymc", ""),
                "start": str(start),
                "pageSize": str(self.page_size),
            }

        return {
            "mhcx": "1",
            "orderBy": self.filters.get("orderBy", ""),
            "ssdm2": self.filters.get("ssdm2", ""),
            "mldm2": self.filters.get("mldm2", ""),
            "xxfs2": self.filters.get("xxfs2", ""),
            "zxjh2": self.filters.get("zxjh2", ""),
            "dwmc2": self.filters.get("dwmc2", ""),
            "fhbktj": self.filters.get("fhbktj", ""),
            "start": str(start),
            "pageSize": str(self.page_size),
        }

    def _parse_list_response(
        self, response: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """解析列表响应"""
        msg = response.get("msg", {})
        data = msg.get("data", {})
        vo_list = data.get("vo_list", {})
        items = vo_list.get("vos", []) or []
        paging = vo_list.get("pagenation", {}) or {}
        return items, paging

    def _build_row(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """构建输出行"""
        xxfs_code = str(item.get("xxfs", "") or "")
        zxjh_code = str(item.get("zxjh", "") or "")

        row = {
            "ID": item.get("id", ""),
            "省市代码": item.get("ssdm", ""),
            "招生单位代码": item.get("dwdm", ""),
            "招生单位": item.get("dwmc", ""),
            "院系所代码": item.get("yxsdm", ""),
            "院系所": item.get("yxsmc", ""),
            "专业代码": item.get("zydm", ""),
            "专业": item.get("zymc", ""),
            "研究方向代码": item.get("yjfxdm", ""),
            "研究方向": item.get("yjfxmc", ""),
            "学习方式代码": xxfs_code,
            "学习方式": config.TRANSFER_CODE_MAP["xxfs"].get(xxfs_code, xxfs_code),
            "专项计划代码": zxjh_code,
            "专项计划": config.TRANSFER_CODE_MAP["zxjh"].get(zxjh_code, zxjh_code),
            "余额状态": item.get("zt", ""),
            "缺额人数": item.get("qers", ""),
            "发布时间": item.get("fbsjStr", ""),
            "备注": item.get("bz", ""),
            "申请条件摘要": item.get("sfmzyq", ""),
        }
        return row

    def _fetch_detail(self, item_id: str) -> Dict[str, Any]:
        """获取申请条件详情"""
        if not item_id:
            return {}

        ts = int(time.time() * 1000)
        url = f"{config.TRANSFER_URLS['detail_api']}?id={item_id}&_t={ts}"
        response = self._request_json(url=url, method="GET")
        data = response.get("msg", {}).get("data", {})
        vo = data.get("vo", {}) or {}
        qexxvo = vo.get("qexxvo", {}) or {}
        ksxxvo = vo.get("ksxxvo", {}) or {}

        return {
            "详情_特殊说明": vo.get("wyyq", ""),
            "详情_初试学位类型要求": vo.get("xwlxyq", ""),
            "详情_初试门类一级学科专业要求": vo.get("kmlyq", ""),
            "详情_初试科目要求": vo.get("kskmyq", ""),
            "详情_总分要求": vo.get("zfyq", ""),
            "详情_政治要求": vo.get("zzllcjyq", ""),
            "详情_外语要求": vo.get("wgycjyq", ""),
            "详情_科目三要求": vo.get("ywk1cjyq", ""),
            "详情_科目四要求": vo.get("ywk2cjyq", ""),
            "详情_考生编号": ksxxvo.get("ksbh", ""),
            "详情_本科门类代码": ksxxvo.get("bkmldm", ""),
            "详情_本科门类": ksxxvo.get("bkmlmc", ""),
            "详情_本科专业代码": ksxxvo.get("bkzydm", ""),
            "详情_本科专业": ksxxvo.get("bkzymc", ""),
            "详情_学习方式代码": qexxvo.get("xxfs", ""),
        }

    def _build_export_row(
        self,
        base_row: Dict[str, Any],
        detail_row: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """按配置字段构建最终导出行"""
        merged_row = dict(base_row)
        if detail_row:
            merged_row.update(detail_row)

        export_fields = list(self.export_base_fields)
        if self.include_detail:
            export_fields.extend(self.export_detail_fields)

        if not export_fields:
            return merged_row

        result: Dict[str, Any] = {}
        for field in export_fields:
            result[field] = merged_row.get(field, "")
        return result

    def run_task(
        self,
        query_mode: str,
        filters: Dict[str, str],
        include_detail: bool,
        page_size: int,
    ) -> Tuple[bool, str, int]:
        """
        运行单次任务（保留会话，不关闭浏览器）

        Returns:
            (是否成功, 输出文件路径, 记录数)
        """
        self.query_mode = query_mode
        self.filters = filters or {}
        self.include_detail = include_detail
        self.page_size = max(1, int(page_size))
        self.rows = []
        self.output_file = self._build_output_filename()
        excel_handler = ExcelHandler(self.output_file)

        try:
            self._ensure_logged_in()
            self.cookie_header = self._build_cookie_header()
            self.logger.info("开始采集调剂信息...")

            start = 0
            page_index = 1
            seen_starts = set()

            while True:
                if start in seen_starts:
                    self.logger.warning(f"检测到重复分页偏移 start={start}，提前结束")
                    break
                seen_starts.add(start)

                payload = self._build_query_payload(start=start)
                response = self._request_json(
                    url=config.TRANSFER_URLS["query_api"],
                    method="POST",
                    data=payload,
                )
                items, paging = self._parse_list_response(response)

                if not items:
                    if page_index == 1:
                        self.logger.warning("当前条件未查到数据")
                    else:
                        self.logger.warning(f"第{page_index}页无数据，结束")
                    break

                for item in items:
                    base_row = self._build_row(item)
                    detail_row = None
                    if self.include_detail:
                        detail_row = self._fetch_detail(str(item.get("id", "")))
                    row = self._build_export_row(base_row, detail_row)
                    self.rows.append(row)

                self.logger.info(
                    f"第{page_index}页完成：本页{len(items)}条，累计{len(self.rows)}条"
                )
                excel_handler.save_data(self.rows)

                if not paging.get("nextPageAvailable", False):
                    break

                next_start = paging.get("startOfNextPage")
                if isinstance(next_start, int):
                    start = next_start
                else:
                    start += self.page_size
                page_index += 1

            if self.rows:
                excel_handler.save_data(self.rows)
                self.logger.success(f"采集完成，共{len(self.rows)}条")
            else:
                self.logger.warning("本次未产生有效记录")
            self.logger.info(f"输出文件: {self.output_file}")
            return True, self.output_file, len(self.rows)

        except Exception as e:
            self.logger.error(f"采集失败: {e}")
            if self.rows:
                excel_handler.save_data(self.rows)
            return False, self.output_file, len(self.rows)

    def close(self):
        """手动关闭浏览器会话"""
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
