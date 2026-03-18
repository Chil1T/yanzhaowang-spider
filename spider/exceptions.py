#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义异常类
"""


class YanZhaoSpiderError(Exception):
    """爬虫基础异常类"""
    pass


class DriverInitializationError(YanZhaoSpiderError):
    """驱动初始化异常"""
    pass


class LoginError(YanZhaoSpiderError):
    """登录异常"""
    pass


class NavigationError(YanZhaoSpiderError):
    """导航异常"""
    pass


class PageLoadError(YanZhaoSpiderError):
    """页面加载异常"""
    pass


class DataExtractionError(YanZhaoSpiderError):
    """数据提取异常"""
    pass


class ExcelSaveError(YanZhaoSpiderError):
    """Excel保存异常"""
    pass


class URLFetchError(YanZhaoSpiderError):
    """URL获取异常"""
    pass


class ElementNotFoundError(YanZhaoSpiderError):
    """元素未找到异常"""
    
    def __init__(self, element_name: str, page_url: str = ""):
        self.element_name = element_name
        self.page_url = page_url
        super().__init__(f"元素 '{element_name}' 未找到，URL: {page_url}")