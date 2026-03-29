#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心爬虫类
"""
import time
import random
from typing import List, Dict, Any, Optional, Callable, Tuple
import os
import queue

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

import config
from models.data_models import (
    University, ProgramDetail, SimpleUniversityInfo,
    detail_to_dict, simple_info_to_dict, university_to_dict
)
from spider.exceptions import (
    DriverInitializationError, LoginError, NavigationError,
    PageLoadError, DataExtractionError, URLFetchError,
    ElementNotFoundError
)
from spider.utils import (
    parse_university_name, extract_total_records, calculate_pages,
    random_sleep, format_timestamp, safe_get_text, resolve_chromedriver_path
)
from handlers.logger_handler import LoggerHandler
from handlers.excel_handler import ExcelHandler
from handlers.progress_handler import ProgressHandler


class YanZhaoScraper:
    """研招网爬虫主类"""
    
    def __init__(
        self,
        major_code: str = "125300",
        study_mode: str = "1",
        info_type: str = "details",
        headless: bool = False,
        progress_callback: Optional[Callable] = None,
        status_callback: Optional[Callable] = None
    ):
        """
        初始化爬虫
        
        Args:
            major_code: 专业代码
            study_mode: 学习方式（1=全日制，2=非全日制）
            info_type: 信息类型（details=硕士点详情，universities=仅研招院校）
            headless: 是否使用无头模式
            progress_callback: 进度回调函数
            status_callback: 状态回调函数
        """
        self.major_code = major_code
        self.study_mode = study_mode
        self.info_type = info_type
        self.headless = headless
        self.major_info = config.MAJOR_CONFIG.get(major_code, config.MAJOR_CONFIG["125300"])
        
        # 回调
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        
        # 控制标志
        self.is_paused = False
        self.is_stopped = False
        self.is_running = False
        self.status_queue = queue.Queue()
        
        # 初始化处理器
        self.logger = LoggerHandler(__name__)
        if status_callback:
            self.logger.set_status_callback(status_callback)
        
        # 生成文件名
        study_mode_name = config.STUDY_MODE[self.study_mode]
        info_type_name = config.INFO_TYPE[self.info_type]
        self.excel_filename = f"data/研究生招生信息_{self.major_info['name']}_{study_mode_name}_{info_type_name}.xlsx"
        
        # 初始化Excel处理器和进度处理器
        self.excel_handler = ExcelHandler(self.excel_filename, status_callback)
        self.progress_handler = ProgressHandler(self.excel_filename)
        
        # 加载已有进度
        self.current_page = self.progress_handler.load_progress()
        self.data = self.progress_handler.data.copy()
        
        # 驱动相关
        self.driver = None
        self.wait = None
        self.target_url = None
        self.total_pages = 1
        
        # 初始化驱动
        self._setup_driver()
        
        self.logger.success(f"初始化完成 - 专业：{self.major_info['name']}，起始页：第{self.current_page}页，已有记录：{len(self.data)}条")
    
    def _setup_driver(self):
        """设置Chrome驱动"""
        def build_options(minimal: bool) -> Options:
            opts = Options()
            opts.add_argument('--no-sandbox')
            opts.add_argument('--disable-dev-shm-usage')
            opts.add_argument('--remote-allow-origins=*')
            opts.add_argument('--no-first-run')
            opts.add_argument('--no-default-browser-check')

            if self.headless:
                opts.add_argument('--headless')
                opts.add_argument('--disable-gpu')
            if minimal:
                opts.add_argument('--disable-extensions')
                opts.add_argument('--disable-background-networking')
            else:
                opts.add_argument('--disable-blink-features=AutomationControlled')
                opts.add_experimental_option("excludeSwitches", ["enable-automation"])
                opts.add_experimental_option('useAutomationExtension', False)
                opts.add_argument(
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
            return opts

        def start_with_executable(executable_path: str, strategy_name: str) -> Optional[webdriver.Chrome]:
            for minimal in (False, True):
                try:
                    service = Service(executable_path=executable_path)
                    return webdriver.Chrome(service=service, options=build_options(minimal))
                except Exception as e:
                    mode_name = "最小参数" if minimal else "默认参数"
                    errors.append(f"{strategy_name}({mode_name})失败: {e}")
            return None

        def start_with_manager(strategy_name: str) -> Optional[webdriver.Chrome]:
            for minimal in (False, True):
                try:
                    return webdriver.Chrome(options=build_options(minimal))
                except Exception as e:
                    mode_name = "最小参数" if minimal else "默认参数"
                    errors.append(f"{strategy_name}({mode_name})失败: {e}")
            return None

        if self.headless:
            self.logger.info("启用无头模式，浏览器将在后台运行")
        else:
            self.logger.info("启用可视模式，将显示浏览器窗口")

        errors = []

        # 策略1：优先使用配置路径
        configured_driver = getattr(config, "CHROME_DRIVER_PATH", "")
        if configured_driver:
            if os.path.exists(configured_driver):
                self.driver = start_with_executable(configured_driver, "配置路径驱动")
            else:
                errors.append(f"配置路径不存在: {configured_driver}")

        # 策略2：Selenium Manager
        if self.driver is None:
            self.driver = start_with_manager("Selenium Manager")

        # 策略3：webdriver-manager
        if self.driver is None:
            try:
                manager_path = ChromeDriverManager().install()
                driver_path = resolve_chromedriver_path(manager_path)
                self.driver = start_with_executable(driver_path, "webdriver-manager")
            except Exception as e:
                errors.append(f"webdriver-manager 安装失败: {e}")

        if self.driver is None:
            error_msg = "Chrome驱动初始化失败: " + (" | ".join(errors) if errors else "未知错误")
            self.logger.error(error_msg)
            raise DriverInitializationError(error_msg)

        # 隐藏自动化特征
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self.wait = WebDriverWait(self.driver, config.DEFAULT_CONFIG["timeout"])

        mode_text = "无头模式" if self.headless else "可视模式"
        self.logger.success(f"Chrome驱动初始化成功 ({mode_text})")
    
    def _update_progress(self, status: str = "运行中"):
        """更新进度"""
        if self.progress_callback:
            progress_info = self.progress_handler.get_progress_info(self.total_pages, status)
            self.progress_callback({
                'current_page': progress_info.current_page,
                'total_pages': progress_info.total_pages,
                'records_count': progress_info.records_count,
                'progress_percentage': progress_info.progress_percentage,
                'status': progress_info.status
            })
    
    def _check_stop_signal(self) -> bool:
        """检查停止信号"""
        return self.is_stopped
    
    def _wait_if_paused(self):
        """如果暂停则等待"""
        while self.is_paused and not self.is_stopped:
            time.sleep(0.1)
    
    def pause(self):
        """暂停爬虫"""
        self.is_paused = True
        self.logger.warning("爬虫已暂停")
    
    def resume(self):
        """恢复爬虫"""
        self.is_paused = False
        self.logger.info("爬虫已恢复")
    
    def stop(self):
        """停止爬虫"""
        self.is_stopped = True
        self.logger.warning("正在停止爬虫...")
    
    def _inject_cookies(self):
        """注入Cookie"""
        self.logger.info("正在注入Cookie...")
        
        # 清除现有Cookie
        self.driver.delete_all_cookies()
        
        # 注入配置中的Cookie
        success_count = 0
        for cookie in config.LOGIN_COOKIES:
            try:
                self.driver.add_cookie(cookie)
                success_count += 1
            except Exception as e:
                self.logger.debug(f"Cookie {cookie.get('name')} 注入失败: {e}")
        
        self.logger.info(f"Cookie注入完成，成功{success_count}/{len(config.LOGIN_COOKIES)}个")
    
    def get_target_url(self) -> str:
        """
        获取目标URL
        
        Returns:
            目标URL
        """
        try:
            self.logger.info("正在获取专业对应的目标页面...")
            
            # 访问专业库首页
            self.driver.get(config.URLS["base"])
            time.sleep(config.DEFAULT_CONFIG["wait_time"]["page_load"])
            
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 选择专业学位
            self.logger.info("选择专业学位...")
            try:
                WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.XPATH, config.SELECTORS["professional_degree"]))
                )
                
                elements = self.driver.find_elements(By.XPATH, config.SELECTORS["professional_degree"])
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        element.click()
                        break
                time.sleep(2)
            except Exception as e:
                self.logger.warning(f"选择专业学位失败: {e}")
            
            # 选择学习方式
            study_mode_name = config.STUDY_MODE[self.study_mode]
            self.logger.info(f"选择学习方式：{study_mode_name}...")
            try:
                xpath = config.SELECTORS["study_mode"].format(mode=study_mode_name)
                element = self.driver.find_element(By.XPATH, xpath)
                self.driver.execute_script("arguments[0].click();", element)
                time.sleep(2)
            except Exception as e:
                self.logger.warning(f"选择{study_mode_name}失败: {e}")
            
            # 选择专业类别
            category = self.major_info["category"]
            self.logger.info(f"选择专业类别：{category}...")
            try:
                time.sleep(2)
                xpath = config.SELECTORS["category"].format(category=category)
                element = self.driver.find_element(By.XPATH, xpath)
                self.driver.execute_script("arguments[0].click();", element)
                time.sleep(3)
            except Exception as e:
                self.logger.error(f"选择专业类别失败: {e}")
                raise URLFetchError(f"选择专业类别失败: {e}")
            
            # 等待专业列表加载
            self.logger.info("等待专业列表加载...")
            time.sleep(5)
            
            # 查找开设院校链接
            self.logger.info("查找开设院校链接...")
            
            # 策略1：直接查找包含zydetail的链接
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    if href and 'zydetail.do' in href and self.major_code in href:
                        self.logger.success("成功获取目标URL")
                        return href
                except:
                    continue
            
            # 策略2：查找文本为"开设院校"的链接
            try:
                xpath = config.SELECTORS["open_schools_link"]
                elements = self.driver.find_elements(By.XPATH, xpath)
                for element in elements:
                    href = element.get_attribute('href')
                    if href and 'zydetail.do' in href:
                        self.logger.success("成功获取目标URL")
                        return href
            except:
                pass
            
            # 使用备用URL
            self.logger.warning("未找到开设院校链接，使用备用URL")
            if self.major_code in config.BACKUP_URL_TEMPLATE:
                return config.BACKUP_URL_TEMPLATE[self.major_code].format(
                    study_mode=self.study_mode
                )
            
            raise URLFetchError(f"无法获取专业 {self.major_code} 的URL")
            
        except Exception as e:
            self.logger.error(f"获取目标URL失败: {e}")
            raise
    
    def login_and_navigate(self) -> bool:
        """
        登录并导航到目标页面 - 添加手动登录等待
        """
        try:
            # 获取目标URL
            if not self.target_url:
                self.target_url = self.get_target_url()
            
            # 访问目标URL
            self.logger.info(f"正在访问目标页面: {self.target_url}")
            self.driver.get(self.target_url)
            time.sleep(config.DEFAULT_CONFIG["wait_time"]["page_load"])
            
            # 注入Cookie
            self._inject_cookies()
            
            # 刷新页面使Cookie生效
            self.driver.refresh()
            self.logger.success("Cookie注入成功，页面已刷新")
            time.sleep(3)
            
            # ===== 在这里添加手动登录等待 =====
            self.logger.warning("=" * 60)
            self.logger.warning("请在浏览器中完成手动登录（扫码或账号密码）")
            self.logger.warning("登录成功后，按回车键继续...")
            self.logger.warning("=" * 60)
            
            # 等待用户按回车
            input()  # 这会暂停程序，等待用户输入
            
            self.logger.info("继续执行爬虫...")
            # ===== 等待结束 =====
            
            # 检测总页数
            self._detect_total_pages()
            
            # 验证登录状态
            page_source = self.driver.page_source
            if "个相关招生单位" in page_source or "个人中心" in page_source:
                self.logger.success("登录态验证成功")
            else:
                self.logger.warning("Cookie可能未生效或页面结构改变")
            
            return True
            
        except Exception as e:
            self.logger.error(f"登录导航过程出错: {e}")
            return False
    
    def _detect_total_pages(self):
        """检测总页数"""
        self.logger.info("正在检测总页数...")
        total_pages = 1
        
        # 等待页面完全加载
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
        time.sleep(3)
        
        # 方法1：从Vue应用获取
        try:
            js_result = self.driver.execute_script("""
                try {
                    var app = null;
                    var appDiv = document.getElementById('app') || document.querySelector('.app-wrapper');
                    if (appDiv && appDiv.__vue__) {
                        app = appDiv.__vue__;
                    }
                    
                    if (!app) {
                        var allElements = document.querySelectorAll('*');
                        for (var i = 0; i < allElements.length; i++) {
                            if (allElements[i].__vue__ && 
                                allElements[i].__vue__.form && 
                                typeof allElements[i].__vue__.form.totalPage !== 'undefined') {
                                app = allElements[i].__vue__;
                                break;
                            }
                        }
                    }
                    
                    if (app && app.form && app.form.totalPage > 0) {
                        return app.form.totalPage;
                    }
                    return null;
                } catch (e) {
                    return null;
                }
            """)
            
            if js_result and js_result > 0:
                total_pages = int(js_result)
                self.logger.success(f"从Vue应用获取到总页数：{total_pages}页")
                self.total_pages = total_pages
                return
        except Exception as e:
            self.logger.warning(f"从Vue应用获取总页数失败: {e}")
        
        # 方法2：从记录数计算
        try:
            elements = self.driver.find_elements(By.XPATH, config.SELECTORS["total_records"])
            for element in elements:
                text = element.text.strip()
                total_records = extract_total_records(text)
                if total_records:
                    total_pages = calculate_pages(total_records, config.DEFAULT_CONFIG["page_size"])
                    self.logger.success(f"从记录数计算总页数：{total_records}条记录 → {total_pages}页")
                    self.total_pages = total_pages
                    return
        except Exception as e:
            self.logger.warning(f"从记录数计算总页数失败: {e}")
        
        # 默认值
        self.total_pages = 33
        self.logger.warning(f"使用默认总页数：{self.total_pages}页")
    
    def navigate_to_page(self, page_num: int) -> bool:
        """
        导航到指定页面
        
        Args:
            page_num: 目标页码
        
        Returns:
            是否成功
        """
        try:
            self.logger.info(f"尝试导航到第{page_num}页")
            
            current_page = self._get_current_page()
            if current_page == page_num:
                self.current_page = page_num
                self.logger.info(f"已在第{page_num}页")
                return True
            
            # 使用页码链接导航
            page_links = self.driver.find_elements(By.XPATH, f"//li/a[text()='{page_num}']")
            if page_links:
                page_links[0].click()
                time.sleep(config.DEFAULT_CONFIG["wait_time"]["page_load"])
                
                actual_page = self._get_current_page()
                if actual_page == page_num:
                    self.current_page = page_num
                    self.logger.info(f"成功导航到第{page_num}页")
                    return True
            
            # 使用下一页按钮逐步导航
            if current_page < page_num:
                self.logger.info(f"使用下一页按钮从第{current_page}页导航到第{page_num}页")
                attempts = 0
                
                while current_page < page_num and attempts < 20:
                    next_buttons = self.driver.find_elements(
                        By.XPATH,
                        "//li[contains(@class, 'next')]/a | //a[contains(text(), '下一页')]"
                    )
                    
                    if next_buttons:
                        next_buttons[0].click()
                        time.sleep(config.DEFAULT_CONFIG["wait_time"]["element_load"])
                        attempts += 1
                        
                        new_page = self._get_current_page()
                        if new_page > current_page:
                            current_page = new_page
                        else:
                            break
                    else:
                        break
                
                if current_page == page_num:
                    self.current_page = page_num
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"导航到第{page_num}页失败: {e}")
            return False
    
    def _get_current_page(self) -> int:
        """获取当前页码"""
        try:
            # 从Vue应用获取
            js_result = self.driver.execute_script("""
                try {
                    var app = null;
                    var appDiv = document.getElementById('app') || document.querySelector('.app-wrapper');
                    if (appDiv && appDiv.__vue__) {
                        app = appDiv.__vue__;
                    }
                    
                    if (!app) {
                        var allElements = document.querySelectorAll('*');
                        for (var i = 0; i < allElements.length; i++) {
                            if (allElements[i].__vue__ && 
                                allElements[i].__vue__.form && 
                                typeof allElements[i].__vue__.form.curPage !== 'undefined') {
                                app = allElements[i].__vue__;
                                break;
                            }
                        }
                    }
                    
                    if (app && app.form && app.form.curPage > 0) {
                        return app.form.curPage;
                    }
                    return null;
                } catch (e) {
                    return null;
                }
            """)
            
            if js_result and js_result > 0:
                return int(js_result)
            
            # 从分页导航获取
            elements = self.driver.find_elements(
                By.XPATH,
                "//li[contains(@class, 'active')]//a | //li[contains(@class, 'current')]//a"
            )
            
            for element in elements:
                text = element.text.strip()
                if text.isdigit():
                    return int(text)
            
            return 1
            
        except Exception as e:
            self.logger.warning(f"获取当前页码失败: {e}")
            return 1
    
    def get_universities(self) -> List[University]:
        """
        获取当前页面的院校列表
        
        Returns:
            院校列表
        """
        try:
            time.sleep(config.DEFAULT_CONFIG["wait_time"]["element_load"])
            
            if self.info_type == "universities":
                return self._get_universities_simple()
            else:
                return self._get_universities_detailed()
                
        except Exception as e:
            self.logger.error(f"获取院校列表失败: {e}")
            return []
    
    def _get_universities_simple(self) -> List[University]:
        """获取院校列表（简单模式）"""
        universities = []
        
        # 获取院校名称
        name_elements = self.driver.find_elements(By.XPATH, config.SELECTORS["university_name"])
        
        names = []
        for elem in name_elements:
            text = safe_get_text(elem)
            if text and ('大学' in text or '学院' in text) and '(' in text and text.startswith('('):
                names.append(text)
        
        self.logger.info(f"简单模式：找到{len(names)}个院校名称")
        
        for i, name in enumerate(names):
            university = University(
                name=name,
                index=i + 1,
                mode='simple'
            )
            universities.append(university)
            self.logger.debug(f"找到院校: {name}")
        
        return universities
    
    def _get_universities_detailed(self) -> List[University]:
        """获取院校列表（详细模式）"""
        universities = []
        
        # 查找展开按钮
        expand_buttons = self.driver.find_elements(By.XPATH, config.SELECTORS["expand_button"])
        
        if not expand_buttons:
            self.logger.error("详细模式：未找到展开按钮")
            return []
        
        # 获取院校名称
        name_elements = self.driver.find_elements(By.XPATH, config.SELECTORS["university_name"])
        
        names = []
        for elem in name_elements:
            text = safe_get_text(elem)
            if text and ('大学' in text or '学院' in text) and '(' in text and text.startswith('('):
                names.append(text)
        
        self.logger.info(f"详细模式：找到{len(expand_buttons)}个展开按钮，{len(names)}个院校名称")
        
        for i, (button, name) in enumerate(zip(expand_buttons, names)):
            try:
                parent = button.find_element(By.XPATH, "./ancestor::*[.//img][1]")
                
                university = University(
                    name=name,
                    element=parent,
                    expand_button=button,
                    index=i + 1,
                    mode='detailed'
                )
                universities.append(university)
                
            except Exception as e:
                self.logger.warning(f"处理第{i+1}个院校时出错: {e}")
                continue
        
        return universities
    
    def process_university(self, university: University) -> List[Dict[str, Any]]:
        """
        处理单个院校
        
        Args:
            university: 院校对象
        
        Returns:
            数据记录列表
        """
        if university.mode == 'simple':
            return self._process_university_simple(university)
        else:
            return self._process_university_detailed(university)
    
    def _process_university_simple(self, university: University) -> List[Dict[str, Any]]:
        """处理单个院校（简单模式）"""
        self.logger.info(f"简单模式：处理院校 {university.name}")
        
        code, display_name = parse_university_name(university.name)
        
        info = SimpleUniversityInfo(
            招生单位=university.name,
            院校代码=code,
            院校名称=display_name,
            页码=self.current_page,
            院校序号=university.index,
            爬取时间=format_timestamp(),
            信息类型=config.INFO_TYPE[self.info_type]
        )
        
        self.logger.info(f"成功获取院校信息 - {display_name} ({code})")
        return [simple_info_to_dict(info)]
    
    def _process_university_detailed(self, university: University) -> List[Dict[str, Any]]:
        """处理单个院校（详细模式）"""
        self.logger.info(f"详细模式：开始处理院校: {university.name}")
        
        try:
            # 点击展开按钮
            if university.expand_button:
                university.expand_button.click()
                time.sleep(config.DEFAULT_CONFIG["wait_time"]["element_load"])
            
            # 查找详情链接
            detail_links = self.driver.find_elements(By.XPATH, config.SELECTORS["detail_link"])
            
            if not detail_links:
                self.logger.warning(f"院校 {university.name} 没有找到详情链接")
                return []
            
            university_data = []
            original_window = self.driver.current_window_handle
            
            # 处理每个详情链接
            for i, detail_link in enumerate(detail_links):
                try:
                    self.logger.info(f"处理 {university.name} 的第{i+1}个硕士点")
                    
                    # 点击详情链接
                    detail_link.click()
                    time.sleep(config.DEFAULT_CONFIG["wait_time"]["element_load"])
                    
                    # 切换到新窗口
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    
                    # 提取详情信息
                    details = self._extract_program_details(university.name, i + 1)
                    
                    if details:
                        details['信息类型'] = config.INFO_TYPE[self.info_type]
                        university_data.append(details)
                    
                    # 关闭详情窗口
                    self.driver.close()
                    self.driver.switch_to.window(original_window)
                    time.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"处理第{i+1}个硕士点失败: {e}")
                    # 确保返回主窗口
                    try:
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                            self.driver.switch_to.window(original_window)
                    except:
                        pass
            
            # 收起院校
            try:
                collapse_buttons = self.driver.find_elements(By.XPATH, config.SELECTORS["collapse_button"])
                if collapse_buttons:
                    collapse_buttons[0].click()
                    time.sleep(1)
            except Exception as e:
                self.logger.warning(f"收起院校失败: {e}")
            
            return university_data
            
        except Exception as e:
            self.logger.error(f"处理院校 {university.name} 失败: {e}")
            return []
    
    def _extract_program_details(self, university_name: str, program_index: int) -> Dict[str, Any]:
        """提取硕士点详情"""
        try:
            time.sleep(config.DEFAULT_CONFIG["wait_time"]["element_load"])
            
            details = ProgramDetail(
                院校名称=university_name,
                页码=self.current_page,
                硕士点序号=program_index
            )
            
            # 提取每个字段
            for field_name, selectors in config.DETAIL_SELECTORS.items():
                for selector in selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        value = element.text.strip()
                        if value:
                            setattr(details, field_name, value)
                            self.logger.debug(f"找到 {field_name}: {value}")
                            break
                    except:
                        continue
                    
                if not getattr(details, field_name):
                    self.logger.warning(f"未找到字段: {field_name}")
            
            return detail_to_dict(details)
            
        except Exception as e:
            self.logger.error(f"提取详情失败: {e}")
            return {}
    
    def run(
        self,
        start_page: Optional[int] = None,
        end_page: Optional[int] = None,
        max_universities_per_page: Optional[int] = None
    ) -> bool:
        """运行爬虫"""
        try:
            self.is_running = True
            self.is_stopped = False
            
            # 登录并导航
            if not self.login_and_navigate():
                self.logger.error("登录失败")
                return False
            
            # 设置页面范围
            if start_page is None:
                start_page = self.current_page
            
            if end_page is None:
                end_page = self.total_pages
            elif end_page > self.total_pages:
                end_page = self.total_pages
            
            if start_page > end_page:
                self.logger.warning(f"起始页({start_page})大于结束页({end_page})，调整为从第{end_page}页开始")
                start_page = end_page
            
            self.logger.success(f"页面范围确认：第{start_page}页到第{end_page}页（共{self.total_pages}页）")
            self._update_progress("初始化中")
            
            # 遍历页面
            for page_num in range(start_page, end_page + 1):
                if self._check_stop_signal():
                    break
                
                self._wait_if_paused()
                
                self.logger.info(f"开始处理第{page_num}页 (共{self.total_pages}页)")
                self._update_progress("正在爬取")
                
                try:
                    # 导航到页面
                    if not self.navigate_to_page(page_num):
                        self.logger.error(f"导航到第{page_num}页失败")
                        continue
                    
                    # 双重验证页码
                    actual_page = self._get_current_page()
                    if actual_page != page_num:
                        self.logger.warning(f"页码不一致：期望第{page_num}页，实际第{actual_page}页")
                        self.current_page = actual_page
                    
                    # 获取院校列表
                    universities = self.get_universities()
                    if not universities:
                        self.logger.warning(f"第{self.current_page}页没有找到院校")
                        continue
                    
                    # 限制每页处理数量
                    if max_universities_per_page:
                        universities = universities[:max_universities_per_page]
                    
                    page_data_count = 0
                    
                    # 处理每个院校
                    for univ_index, university in enumerate(universities, 1):
                        if self._check_stop_signal():
                            break
                        
                        self._wait_if_paused()
                        
                        self.logger.info(f"处理院校 {univ_index}/{len(universities)}: {university.name}")
                        
                        university_data = self.process_university(university)
                        
                        if university_data:
                            self.data.extend(university_data)
                            self.progress_handler.update_data(university_data)
                            page_data_count += len(university_data)
                            
                            self.logger.info(f"院校 {university.name} 完成，获得{len(university_data)}条记录")
                        
                        random_sleep(*config.DEFAULT_CONFIG["wait_time"]["between_universities"])
                    
                    if self._check_stop_signal():
                        break
                    
                    # 每页完成后保存数据
                    if page_data_count > 0:
                        self.logger.info(f"第{page_num}页完成，获得{page_data_count}条记录，正在保存数据...")
                        self.excel_handler.save_data(self.data)
                        self.logger.info(f"第{page_num}页完成，当前总记录数: {len(self.data)}")
                    else:
                        self.logger.warning(f"第{page_num}页没有获取到数据")
                    
                    random_sleep(*config.DEFAULT_CONFIG["wait_time"]["between_pages"])
                    
                except Exception as e:
                    self.logger.error(f"处理第{page_num}页失败: {e}")
                    # 发生错误时也尝试保存数据
                    self.excel_handler.save_data(self.data)
                    continue
            
            # 最终保存
            self.logger.info("爬虫运行结束，正在保存最终数据...")
            self.excel_handler.save_data(self.data)
            
            if self._check_stop_signal():
                self.logger.warning(f"爬虫已停止，共获取{len(self.data)}条记录")
            else:
                self.logger.success(f"爬虫运行完成，共获取{len(self.data)}条记录")
            
            # 显示文件保存位置
            file_info = self.excel_handler.get_file_info()
            self.logger.info(f"数据已保存到: {file_info['path']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"爬虫运行失败: {e}")
            self._emergency_save()
            return False
            
        finally:
            self.is_running = False
            self._cleanup()
    
    def _emergency_save(self):
        """紧急保存"""
        try:
            if self.data:
                self.excel_handler.save_data(self.data)
                self.logger.info(f"紧急保存完成: {self.excel_filename}")
        except Exception as e:
            self.logger.error(f"紧急保存失败: {e}")
    
    def _cleanup(self):
        """清理资源"""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info("浏览器已关闭")
        except:
            pass
    
    def test_url_access(self) -> bool:
        """
        测试URL访问
        
        Returns:
            是否成功
        """
        try:
            self.logger.info("开始测试URL获取和页面访问...")
            
            # 测试URL获取
            self.logger.info("测试第1步：获取目标URL")
            target_url = self.get_target_url()
            
            if target_url:
                self.logger.success(f"URL获取成功")
            else:
                self.logger.error("URL获取失败")
                return False
            
            # 测试页面访问
            self.logger.info("测试第2步：直接访问目标页面")
            self.driver.get(target_url)
            time.sleep(5)
            
            # 检查页面内容
            if "个相关招生单位" in self.driver.page_source or "开设专业" in self.driver.page_source:
                self.logger.success("页面访问成功，内容正常")
                
                # 检查页面结构
                expand_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(text(), '展开')] | //*[contains(text(), '展开')]"
                )
                if expand_buttons:
                    self.logger.success(f"找到{len(expand_buttons)}个展开按钮")
                else:
                    self.logger.warning("未找到展开按钮，但页面基本正常")
                
                return True
            else:
                self.logger.warning("页面内容异常，可能需要登录")
                
                if "登录" in self.driver.page_source.lower():
                    self.logger.info("页面提示需要登录，这是正常的")
                    return True
                else:
                    self.logger.error("页面结构可能已变化")
                    return False
                    
        except Exception as e:
            self.logger.error(f"测试失败: {e}")
            return False
    
    def __del__(self):
        """析构函数"""
        self._cleanup()
