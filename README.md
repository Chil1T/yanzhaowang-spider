# 研究生招生信息爬虫

## 项目简介
本项目支持两类采集任务：
- 专业目录采集（原功能）
- 调剂信息采集（新增，支持筛选）

## 功能概览
- 支持会计专硕等多个专业目录采集
- 支持全日制/非全日制、详情/院校名单模式
- 支持断点续传与重跑
- 支持调剂信息接口采集（精准/模糊查询）
- 支持省市、学习方式、专项计划等筛选
- 可选抓取“申请条件详情”
- 自动导出 `Excel + CSV`

## 环境要求
- Python 3.8+
- Chrome 浏览器
- 可用的 `chromedriver.exe`

## 安装
```bash
pip install -r requirements.txt
```

## 运行
```bash
python main.py
```

启动后先选模式：
- `1` 专业目录爬虫（原流程）
- `2` 调剂信息爬虫（筛选采集）

也支持模板启动参数（直接进入调剂模板模式）：
```bash
python main.py --transfer-template tj_fuzzy_fulltime_default
```

## 调剂模式说明

### 1) 精准查询
对应参数：
- `ssdm`：省市代码（如 `11` 北京）
- `dwmc`：招生单位关键词
- `xxfs`：学习方式（`1` 全日制，`2` 非全日制）
- `zxjh`：专项计划（`0` 普通，`4` 少骨，`7` 退役）
- `zymc`：专业关键词

### 2) 模糊查询
对应参数：
- `mhcx=1`
- `ssdm2`：省市代码
- `mldm2`：学科门类代码（如 `12` 管理学）
- `xxfs2`：学习方式
- `zxjh2`：专项计划
- `dwmc2`：关键词（招生单位或专业）
- `fhbktj=1`：只看符合申请条件

### 3) 登录方式
调剂模式会先打开浏览器，你在页面手动登录后，回到终端按回车继续。

### 4) 连续抓取（会话复用）
- 调剂模式下，程序会只初始化一次浏览器会话。
- 每次抓取完成后不会自动退出，会询问是否继续下一次抓取。
- 继续抓取时复用当前登录状态，无需重复登录。
- 输入 `n` 才会结束循环并关闭浏览器会话。

### 5) 模板模式（启动参数）
内置模板 `tj_fuzzy_fulltime_default` 固定条件：
- 查询模式：模糊查询
- `ssdm2`：不限
- `xxfs2`：全日制（`1`）
- `zxjh2`：普通计划（`0`）
- 每页条数：`20`

可配置项（可通过命令行设置默认值，运行中也可继续修改）：
- 学科门类：`--mldm2`
- 关键词：`--keyword`
- 是否只看符合申请条件：`--fhbktj`
- 是否抓取详情：`--detail`

示例：
```bash
python main.py --transfer-template tj_fuzzy_fulltime_default --mldm2 08 --keyword 计算机 --fhbktj --detail
```

## 输出
导出文件在 `data/` 目录，文件名会包含：
- 关键词
- 月/日/小时/分钟
- 查询模式（精准/模糊）
- 是否抓取详情
- 你选择的关键筛选参数（省市、学习方式、专项计划、门类等）
- 每页条数

示例：
- `调剂_模糊_计算机_M03D28H17M40_含详情_ssdm2-11_mldm2-08_xxfs2-1_dwmc2-计算机_ps-100.xlsx`

## 配置项
请在 `config.py` 中确认：
- `CHROME_DRIVER_PATH` 指向本机可用驱动
- `TRANSFER_URLS` 和 `TRANSFER_CODE_MAP`（调剂模式）
- `TRANSFER_BROWSER_START_HIDDEN=True` 可将 Selenium 新开窗口离屏隐藏（减少 `data:` 空白页干扰）
- `TRANSFER_SUPPRESS_DRIVER_LOGS=True` 可抑制部分 chromedriver 噪声日志

## 主要文件
- `main.py`：交互入口（模式选择）
- `spider/core.py`：专业目录爬虫
- `spider/transfer_api.py`：调剂接口爬虫
- `handlers/excel_handler.py`：导出处理
