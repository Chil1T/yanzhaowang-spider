#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件 - 支持自动解析Cookie字符串
"""
import re
from typing import List, Dict, Optional

# ============================================
# 1. 直接粘贴您的完整Cookie字符串（最简单的方式）
# ============================================
COOKIE_STRING = """ your cookie string here"""

# ============================================
# 2. 自动解析函数 - 将Cookie字符串转换为字典列表
# ============================================
def parse_cookie_string(cookie_str: str) -> List[Dict[str, str]]:
    """
    解析Cookie字符串，转换为字典列表格式
    
    Args:
        cookie_str: Cookie字符串，格式如 "name1=value1; name2=value2"
    
    Returns:
        Cookie字典列表，每个字典包含name和value字段
    """
    cookies = []
    
    # 清理字符串：去除换行和多余空格
    cookie_str = cookie_str.replace('\n', '').strip()
    
    # 按分号分割
    pairs = cookie_str.split(';')
    
    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue
        
        # 按等号分割
        if '=' in pair:
            name, value = pair.split('=', 1)
            name = name.strip()
            value = value.strip()
            
            if name and value:
                cookies.append({
                    'name': name,
                    'value': value
                })
    
    return cookies

# ============================================
# 3. 自动生成的Cookie字典列表
# ============================================
# 通过解析COOKIE_STRING自动生成
AUTO_GENERATED_COOKIES = parse_cookie_string(COOKIE_STRING)

# 如果您想手动指定，可以在这里添加或修改
CUSTOM_COOKIES = [
    # 在这里手动添加特殊的Cookie配置
]

# ============================================
# 4. 最终使用的Cookie配置
# ============================================
# 优先使用自定义Cookie，如果没有则使用自动生成的
FINAL_COOKIES = CUSTOM_COOKIES if CUSTOM_COOKIES else AUTO_GENERATED_COOKIES

# 为了方便直接使用，也提供列表形式
LOGIN_COOKIES = FINAL_COOKIES

# ============================================
# 5. Cookie管理配置
# ============================================
USE_COOKIE_FILE = True  # 是否将Cookie保存到文件
COOKIE_FILE_PATH = "data/cookies.json"  # Cookie文件保存路径
AUTO_REFRESH_COOKIE = False  # 是否自动刷新Cookie（需要手动更新）

# ============================================
# 专业配置映射（保持不变）
# ============================================
MAJOR_CONFIG = {
    "125300": {
        "name": "会计专硕",
        "category": "1253",
        "full_name": "会计"
    },
    "125700": {
        "name": "审计专硕", 
        "category": "1257",
        "full_name": "审计"
    },
    "125500": {
        "name": "图书情报",
        "category": "1255", 
        "full_name": "图书情报"
    },
    "125604": {
        "name": "物流工程与管理",
        "category": "1256",
        "full_name": "物流工程与管理"
    },
    "125603": {
        "name": "工业工程与管理",
        "category": "1256",
        "full_name": "工业工程与管理"
    }
}

# ============================================
# 学习方式映射
# ============================================
STUDY_MODE = {
    "1": "全日制",
    "2": "非全日制"
}

# ============================================
# 信息类型映射
# ============================================
INFO_TYPE = {
    "details": "硕士点详情",
    "universities": "仅研招院校"
}

# ============================================
# Chrome驱动配置
# ============================================
CHROME_DRIVER_PATH = r'C:\Users\86157\.wdm\drivers\chromedriver\win64\146.0.7680.76\chromedriver-win32\chromedriver.exe'

# ============================================
# 爬虫默认配置
# ============================================
DEFAULT_CONFIG = {
    "page_size": 10,  # 每页显示数量
    "max_retries": 5,  # 最大重试次数
    "timeout": 30,  # 超时时间（秒）
    "wait_time": {
        "page_load": 3,
        "element_load": 2,
        "between_pages": (3, 6),
        "between_universities": (2, 4)
    }
}

# ============================================
# URL配置
# ============================================
URLS = {
    "base": "https://yz.chsi.com.cn/zsml/",
    "detail": "https://yz.chsi.com.cn/zsml/zydetail.do"
}

# ============================================
# 备用URL模板
# ============================================
BACKUP_URL_TEMPLATE = {
    "125300": "https://yz.chsi.com.cn/zsml/zydetail.do?zydm=125300&zymc=%E4%BC%9A%E8%AE%A1&xwlx=zyxw&mldm=12&mlmc=%E7%AE%A1%E7%90%86%E5%AD%A6&yjxkdm=1253&yjxkmc=%E4%BC%9A%E8%AE%A1&xxfs={study_mode}&tydxs=&jsggjh=&sign=73f11afdfd7ae989f9112d36b83036c9",
    "125700": "https://yz.chsi.com.cn/zsml/zydetail.do?zydm=125700&zymc=%E5%AE%A1%E8%AE%A1&xwlx=zyxw&mldm=12&mlmc=%E7%AE%A1%E7%90%86%E5%AD%A6&yjxkdm=1257&yjxkmc=%E5%AE%A1%E8%AE%A1&xxfs={study_mode}&tydxs=&jsggjh="
}

# ============================================
# XPath选择器配置
# ============================================
SELECTORS = {
    "professional_degree": "//*[contains(text(), '专业学位')]",
    "study_mode": "//*[text()='{mode}']",
    "category": "//*[contains(text(), '({category})')]",
    "open_schools_link": "//a[contains(@href, 'zydetail.do')]",
    "expand_button": "//a[contains(text(), '展开')]",
    "collapse_button": "//a[contains(text(), '收起')]",
    "detail_link": "//a[contains(text(), '详情')]",
    "university_name": "//*[contains(text(), '大学') or contains(text(), '学院')]",
    "total_records": "//*[contains(text(), '查询到') and contains(text(), '个相关招生单位')]"
}

# ============================================
# 详情页字段选择器
# ============================================
DETAIL_SELECTORS = {
    '招生单位': [
        "//div[contains(text(), '招生单位：')]/following-sibling::div",
        "//div[contains(text(), '招生单位')]/following-sibling::div[1]",
        "//*[contains(text(), '招生单位：')]/following-sibling::*[1]"
    ],
    '考试方式': [
        "//div[contains(text(), '考试方式：')]/following-sibling::div",
        "//div[contains(text(), '考试方式')]/following-sibling::div[1]",
        "//*[contains(text(), '考试方式：')]/following-sibling::*[1]"
    ],
    '院系所': [
        "//div[contains(text(), '院系所：')]/following-sibling::div",
        "//div[contains(text(), '院系所')]/following-sibling::div[1]",
        "//*[contains(text(), '院系所：')]/following-sibling::*[1]"
    ],
    '学习方式': [
        "//div[contains(text(), '学习方式：')]/following-sibling::div",
        "//div[contains(text(), '学习方式')]/following-sibling::div[1]",
        "//*[contains(text(), '学习方式：')]/following-sibling::*[1]"
    ],
    '研究方向': [
        "//div[contains(text(), '研究方向：')]/following-sibling::div",
        "//div[contains(text(), '研究方向')]/following-sibling::div[1]",
        "//*[contains(text(), '研究方向：')]/following-sibling::*[1]"
    ],
    '拟招生人数': [
        "//div[contains(text(), '拟招生人数：')]/following-sibling::div",
        "//div[contains(text(), '拟招生人数')]/following-sibling::div[1]",
        "//*[contains(text(), '拟招生人数：')]/following-sibling::*[1]"
    ]
}

# ============================================
# 调试配置
# ============================================
DEBUG = {
    "save_page_source": False,  # 是否保存页面源码用于调试
    "verbose_logging": False,   # 是否输出详细日志
    "test_mode": False          # 是否测试模式
}


# ============================================
# 导出函数：方便在其他模块中获取Cookie
# ============================================
def get_cookies() -> List[Dict[str, str]]:
    """
    获取配置的Cookie列表
    
    Returns:
        Cookie字典列表
    """
    return LOGIN_COOKIES


def get_cookie_string() -> str:
    """
    获取原始Cookie字符串
    
    Returns:
        Cookie字符串
    """
    return COOKIE_STRING


def print_cookie_info():
    """打印Cookie信息（用于调试）"""
    print("=" * 50)
    print("Cookie配置信息")
    print("=" * 50)
    print(f"Cookie字符串长度: {len(COOKIE_STRING)}")
    print(f"解析出的Cookie数量: {len(AUTO_GENERATED_COOKIES)}")
    print("\n解析出的Cookie列表:")
    for i, cookie in enumerate(AUTO_GENERATED_COOKIES, 1):
        print(f"  {i:2d}. {cookie['name']:30s} = {cookie['value'][:30]}...")
    print("=" * 50)

#登录设置
LOGIN_MODE = {
    "auto": "自动Cookie登录",
    "manual": "手动扫码登录"
}

# 选择登录方式: "auto" 或 "manual"
CURRENT_LOGIN_MODE = "manual"  # 改为 manual 使用手动扫码登录

# 手动登录等待时间（秒）
MANUAL_LOGIN_TIMEOUT = 60  # 等待扫码的最大时间
MANUAL_LOGIN_CHECK_INTERVAL = 2  # 检查间隔

# 如果直接运行此文件，打印Cookie信息
if __name__ == "__main__":
    print_cookie_info()