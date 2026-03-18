#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志处理模块
"""
import logging
import sys
from typing import Optional, Callable


class LoggerHandler:
    """日志处理器"""
    
    def __init__(self, name: str = __name__, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 清除已有的处理器
        self.logger.handlers.clear()
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        
        # 回调函数
        self.status_callback: Optional[Callable] = None
    
    def set_status_callback(self, callback: Callable):
        """设置状态回调函数"""
        self.status_callback = callback
    
    def info(self, message: str):
        """记录信息日志"""
        self.logger.info(message)
        if self.status_callback:
            self.status_callback(message, "info")
    
    def warning(self, message: str):
        """记录警告日志"""
        self.logger.warning(message)
        if self.status_callback:
            self.status_callback(message, "warning")
    
    def error(self, message: str):
        """记录错误日志"""
        self.logger.error(message)
        if self.status_callback:
            self.status_callback(message, "error")
    
    def success(self, message: str):
        """记录成功日志（使用info级别）"""
        self.logger.info(f"✓ {message}")
        if self.status_callback:
            self.status_callback(f"✓ {message}", "success")
    
    def debug(self, message: str):
        """记录调试日志"""
        self.logger.debug(message)
        if self.status_callback:
            self.status_callback(message, "debug")