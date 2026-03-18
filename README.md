# 研究生招生信息爬虫

## 项目简介
这是一个用于爬取中国研究生招生信息网（研招网）硕士专业目录的爬虫工具。支持断点续传、多专业选择、学习方式选择、信息类型选择等功能。

## 功能特点
- ✅ 支持多个专业（会计专硕、审计专硕、图书情报、物流工程与管理、工业工程与管理）
- ✅ 支持全日制/非全日制选择
- ✅ 支持硕士点详情/仅研招院校两种信息类型
- ✅ 断点续传：自动从上次中断的位置继续
- ✅ 暂停/恢复/停止功能
- ✅ 自动保存Excel和CSV格式
- ✅ 文件占用检测和重试机制
- ✅ 详细的日志输出

## 项目结构
```text
yanzhao_spider/
├── main.py                 # 主程序入口
├── README.md               # 项目说明文档
├── spider/
│   ├── __init__.py
│   ├── core.py             # 核心爬虫类
│   ├── utils.py            # 工具函数
│   └── exceptions.py       # 自定义异常
├── models/
│   ├── __init__.py
│   └── data_models.py      # 数据模型
├── handlers/
│   ├── handler.py          # Excel处理
│   ├── progress_handler.py # 进度处理
│   └── logger_handler.py   # 日志处理
└── data/                   # 数据存储目录
```
## 安装说明

### 环境要求
- Python 3.8+
- Chrome浏览器

### 安装步骤
1. 克隆或下载本项目
2. 安装依赖包：
   ```bash
   pip install -r requirements.txt




