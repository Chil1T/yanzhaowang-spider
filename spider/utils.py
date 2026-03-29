#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数
"""
import re
import time
import random
import os
from typing import Optional, Tuple, Any
from datetime import datetime


def parse_university_name(raw_name: str) -> Tuple[str, str]:
    """
    解析院校名称，提取代码和显示名称
    
    Args:
        raw_name: 原始院校名称，如 "(10001)北京大学"
    
    Returns:
        (code, display_name) 元组
    """
    code = ""
    display_name = raw_name
    
    if raw_name.startswith('(') and ')' in raw_name:
        parts = raw_name.split(')', 1)
        if len(parts) == 2:
            code = parts[0][1:]  # 去掉左括号
            display_name = parts[1]
    
    return code, display_name


def extract_total_records(text: str) -> Optional[int]:
    """
    从文本中提取总记录数
    
    Args:
        text: 如 "查询到323个相关招生单位"
    
    Returns:
        总记录数，如果未找到返回None
    """
    match = re.search(r'查询到\s*(\d+)\s*个相关招生单位', text)
    if match:
        return int(match.group(1))
    return None


def calculate_pages(total_records: int, page_size: int = 10) -> int:
    """
    计算总页数
    
    Args:
        total_records: 总记录数
        page_size: 每页记录数
    
    Returns:
        总页数
    """
    return (total_records + page_size - 1) // page_size


def random_sleep(min_seconds: float, max_seconds: float):
    """随机休眠"""
    time.sleep(random.uniform(min_seconds, max_seconds))


def format_timestamp() -> str:
    """格式化当前时间戳"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def safe_get_text(element) -> str:
    """安全获取元素文本"""
    try:
        return element.text.strip()
    except:
        return ""


def safe_get_attribute(element, attr: str) -> str:
    """安全获取元素属性"""
    try:
        return element.get_attribute(attr) or ""
    except:
        return ""


def generate_filename(major_name: str, study_mode: str, info_type: str) -> str:
    """
    生成文件名
    
    Args:
        major_name: 专业名称
        study_mode: 学习方式
        info_type: 信息类型
    
    Returns:
        文件名
    """
    return f"研究生招生信息_{major_name}_{study_mode}_{info_type}.xlsx"


def resolve_chromedriver_path(candidate_path: str) -> str:
    """
    纠正 webdriver-manager 可能返回的非可执行路径，
    尽量定位到真正的 chromedriver.exe。

    Args:
        candidate_path: webdriver-manager 返回路径

    Returns:
        可执行驱动路径（找不到则返回原路径）
    """
    if not candidate_path:
        return candidate_path

    normalized = os.path.normpath(candidate_path)

    # 已经是 chromedriver.exe
    if os.path.isfile(normalized) and os.path.basename(normalized).lower() == "chromedriver.exe":
        return normalized

    # 如果是文件（例如 THIRD_PARTY_NOTICES.chromedriver），则在同目录找 exe
    if os.path.isfile(normalized):
        search_dir = os.path.dirname(normalized)
    else:
        search_dir = normalized

    try:
        hits = []
        for root, _, files in os.walk(search_dir):
            for filename in files:
                if filename.lower() == "chromedriver.exe":
                    hits.append(os.path.join(root, filename))

        if hits:
            hits.sort(key=len)
            return os.path.normpath(hits[0])
    except Exception:
        pass

    return normalized
