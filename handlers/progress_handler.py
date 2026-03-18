#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进度处理模块
"""
from typing import List, Dict, Any, Optional, Set
import os
import pandas as pd

from models.data_models import ProgressInfo


class ProgressHandler:
    """进度处理器"""
    
    def __init__(self, excel_filename: str):
        self.excel_filename = excel_filename
        self.current_page = 1
        self.data: List[Dict[str, Any]] = []
    
    def load_progress(self) -> int:
        """
        加载已有进度，返回应该开始的页码
        
        Returns:
            应该开始的页码
        """
        try:
            if os.path.exists(self.excel_filename):
                df = pd.read_excel(self.excel_filename)
                self.data = df.to_dict('records')
                
                if not self.data:
                    print("数据文件为空，将从第1页开始")
                    return 1
                
                print(f"发现已有数据文件 {os.path.basename(self.excel_filename)}，加载了 {len(self.data)} 条记录")
                
                # 分析已完成的页面
                completed_pages: Set[int] = set()
                for record in self.data:
                    page = record.get('页码', 0)
                    if isinstance(page, (int, float)):
                        completed_pages.add(int(page))
                
                if not completed_pages:
                    return 1
                
                max_completed_page = max(completed_pages)
                
                # 检查最后一页的院校数量是否完整
                last_page_records = [
                    r for r in self.data 
                    if r.get('页码') == max_completed_page
                ]
                
                # 统计最后一页的院校数量（通过院校名称去重）
                last_page_universities: Set[str] = set()
                for record in last_page_records:
                    university_name = record.get('招生单位', '') or record.get('院校名称', '')
                    if university_name:
                        last_page_universities.add(university_name)
                
                university_count = len(last_page_universities)
                
                # 如果最后一页院校数量<10个，说明该页不完整，从该页重新开始
                if university_count < 10:
                    print(f"检测到第{max_completed_page}页仅有{university_count}个院校（不完整），将从第{max_completed_page}页重新开始")
                    # 移除不完整页面的数据
                    self.data = [
                        r for r in self.data 
                        if r.get('页码') != max_completed_page
                    ]
                    self.current_page = max_completed_page
                    return max_completed_page
                else:
                    self.current_page = max_completed_page + 1
                    print(f"第{max_completed_page}页有{university_count}个院校（完整），将从第{self.current_page}页继续爬取")
                    return self.current_page
            
            print(f"未找到数据文件 {os.path.basename(self.excel_filename)}，将从头开始")
            return 1
            
        except Exception as e:
            print(f"加载进度失败: {e}")
            self.data = []
            return 1
    
    def get_progress_info(self, total_pages: int, status: str = "运行中") -> ProgressInfo:
        """
        获取进度信息
        
        Args:
            total_pages: 总页数
            status: 状态
        
        Returns:
            进度信息对象
        """
        progress_percentage = (self.current_page - 1) / total_pages * 100 if total_pages > 0 else 0
        
        return ProgressInfo(
            current_page=self.current_page,
            total_pages=total_pages,
            records_count=len(self.data),
            progress_percentage=progress_percentage,
            status=status
        )
    
    def update_data(self, new_data: List[Dict[str, Any]]):
        """更新数据"""
        self.data.extend(new_data)
    
    def set_current_page(self, page: int):
        """设置当前页码"""
        self.current_page = page
    
    def save_progress(self) -> bool:
        """
        保存进度（实际是保存数据到Excel）
        
        Returns:
            是否成功
        """
        from handlers.excel_handler import ExcelHandler
        
        excel_handler = ExcelHandler(self.excel_filename)
        return excel_handler.save_data(self.data)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        return {
            "current_page": self.current_page,
            "total_records": len(self.data),
            "data_file": os.path.basename(self.excel_filename)
        }