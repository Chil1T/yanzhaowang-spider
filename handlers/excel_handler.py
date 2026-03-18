#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel处理模块
"""
import os
import time
from typing import List, Dict, Any, Optional, Callable

import pandas as pd

from spider.exceptions import ExcelSaveError


class ExcelHandler:
    """Excel处理器"""
    
    def __init__(self, filename: str, status_callback: Optional[Callable] = None):
        self.filename = filename
        self.status_callback = status_callback
        self.max_retries = 5
        self.retry_delay = 2
        
        # 确保data目录存在
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        data_dir = os.path.dirname(os.path.abspath(self.filename))
        if data_dir and not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir, exist_ok=True)
                if self.status_callback:
                    self.status_callback(f"创建数据目录: {data_dir}", "info")
            except Exception as e:
                if self.status_callback:
                    self.status_callback(f"创建数据目录失败: {e}", "warning")
    
    def save_data(self, data: List[Dict[str, Any]]) -> bool:
        """
        保存数据到Excel文件
        
        Args:
            data: 数据列表
        
        Returns:
            是否保存成功
        """
        if not data:
            if self.status_callback:
                self.status_callback("没有数据可保存", "warning")
            return False
        
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                df = pd.DataFrame(data)
                
                # 确保目录存在
                self._ensure_data_dir()
                
                # 保存Excel文件
                df.to_excel(self.filename, index=False, engine='openpyxl')
                
                # 同时保存CSV备份
                csv_filename = self.filename.replace('.xlsx', '.csv')
                df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                
                if self.status_callback:
                    self.status_callback(f"✓ 数据已保存到 {os.path.basename(self.filename)}，共{len(data)}条记录", "success")
                
                return True
                
            except PermissionError as e:
                retry_count += 1
                if self.status_callback:
                    self.status_callback(
                        f"文件被占用，第{retry_count}次重试保存 {os.path.basename(self.filename)}",
                        "warning"
                    )
                time.sleep(self.retry_delay)
                
            except Exception as e:
                if self.status_callback:
                    self.status_callback(f"保存数据失败: {e}", "error")
                return False
        
        if self.status_callback:
            self.status_callback(f"文件保存失败，已重试{self.max_retries}次", "error")
        return False
    
    def load_existing_data(self) -> List[Dict[str, Any]]:
        """
        加载已有的Excel数据
        
        Returns:
            数据列表
        """
        try:
            if os.path.exists(self.filename):
                df = pd.read_excel(self.filename)
                data = df.to_dict('records')
                if self.status_callback:
                    self.status_callback(f"加载已有数据: {os.path.basename(self.filename)}，{len(data)}条记录", "info")
                return data
            else:
                if self.status_callback:
                    self.status_callback(f"未找到数据文件: {os.path.basename(self.filename)}", "info")
                return []
        except Exception as e:
            if self.status_callback:
                self.status_callback(f"读取Excel文件失败: {e}", "warning")
            return []
    
    def delete_file(self) -> bool:
        """删除Excel文件"""
        try:
            if os.path.exists(self.filename):
                os.remove(self.filename)
                # 同时删除CSV文件
                csv_filename = self.filename.replace('.xlsx', '.csv')
                if os.path.exists(csv_filename):
                    os.remove(csv_filename)
                if self.status_callback:
                    self.status_callback(f"已删除文件: {os.path.basename(self.filename)}", "info")
                return True
        except Exception as e:
            if self.status_callback:
                self.status_callback(f"删除文件失败: {e}", "error")
        return False
    
    def get_record_count(self) -> int:
        """获取已有记录数"""
        try:
            if os.path.exists(self.filename):
                df = pd.read_excel(self.filename)
                return len(df)
        except:
            pass
        return 0
    
    def get_file_path(self) -> str:
        """获取文件路径"""
        return self.filename
    
    def get_file_info(self) -> Dict[str, Any]:
        """获取文件信息"""
        info = {
            "filename": os.path.basename(self.filename),
            "path": self.filename,
            "exists": os.path.exists(self.filename),
            "size": 0,
            "record_count": 0
        }
        
        if info["exists"]:
            info["size"] = os.path.getsize(self.filename)
            info["record_count"] = self.get_record_count()
        
        return info