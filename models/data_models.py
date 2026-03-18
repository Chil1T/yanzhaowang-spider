#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class University:
    """院校模型"""
    name: str
    code: str = ""
    display_name: str = ""
    page: int = 0
    index: int = 0
    mode: str = "simple"
    element: Any = None
    expand_button: Any = None


@dataclass
class ProgramDetail:
    """硕士点详情模型"""
    招生单位: str = ""
    考试方式: str = ""
    院系所: str = ""
    学习方式: str = ""
    研究方向: str = ""
    拟招生人数: str = ""
    页码: int = 0
    院校名称: str = ""
    硕士点序号: int = 0
    爬取时间: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    信息类型: str = "硕士点详情"


@dataclass
class SimpleUniversityInfo:
    """简单院校信息模型"""
    招生单位: str = ""
    院校代码: str = ""
    院校名称: str = ""
    页码: int = 0
    院校序号: int = 0
    爬取时间: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    信息类型: str = "仅研招院校"


@dataclass
class ProgressInfo:
    """进度信息模型"""
    current_page: int
    total_pages: int
    records_count: int
    progress_percentage: float
    status: str


@dataclass
class ScraperConfig:
    """爬虫配置模型"""
    major_code: str
    study_mode: str
    info_type: str
    major_info: Dict
    headless: bool = False
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    max_universities_per_page: Optional[int] = None


def university_to_dict(university: University) -> Dict:
    """将University对象转换为字典"""
    result = asdict(university)
    # 移除不可序列化的元素
    result.pop('element', None)
    result.pop('expand_button', None)
    return result


def dict_to_university(data: Dict) -> University:
    """将字典转换为University对象"""
    return University(
        name=data.get('name', ''),
        code=data.get('code', ''),
        display_name=data.get('display_name', ''),
        page=data.get('page', 0),
        index=data.get('index', 0),
        mode=data.get('mode', 'simple')
    )


def detail_to_dict(detail: ProgramDetail) -> Dict:
    """将ProgramDetail对象转换为字典"""
    return asdict(detail)


def simple_info_to_dict(info: SimpleUniversityInfo) -> Dict:
    """将SimpleUniversityInfo对象转换为字典"""
    return asdict(info)