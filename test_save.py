#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据保存功能
"""
import os
from handlers.excel_handler import ExcelHandler
from handlers.progress_handler import ProgressHandler
from datetime import datetime

def test_excel_handler():
    """测试Excel处理器"""
    print("=" * 50)
    print("测试Excel处理器")
    print("=" * 50)
    
    # 创建测试数据
    test_data = [
        {
            "招生单位": "(10001)北京大学",
            "院校代码": "10001",
            "院校名称": "北京大学",
            "页码": 1,
            "院校序号": 1,
            "爬取时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "信息类型": "测试数据"
        },
        {
            "招生单位": "(10002)清华大学",
            "院校代码": "10002",
            "院校名称": "清华大学",
            "页码": 1,
            "院校序号": 2,
            "爬取时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "信息类型": "测试数据"
        }
    ]
    
    # 测试保存
    filename = "data/测试数据_会计专硕_全日制_硕士点详情.xlsx"
    handler = ExcelHandler(filename)
    
    print(f"\n1. 保存数据到 {filename}")
    success = handler.save_data(test_data)
    print(f"   保存结果: {'成功' if success else '失败'}")
    
    # 测试加载
    print(f"\n2. 加载数据")
    loaded_data = handler.load_existing_data()
    print(f"   加载了 {len(loaded_data)} 条记录")
    
    # 测试文件信息
    print(f"\n3. 文件信息")
    info = handler.get_file_info()
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    return handler

def test_progress_handler():
    """测试进度处理器"""
    print("\n" + "=" * 50)
    print("测试进度处理器")
    print("=" * 50)
    
    filename = "data/测试数据_会计专硕_全日制_硕士点详情.xlsx"
    handler = ProgressHandler(filename)
    
    print(f"\n1. 加载进度")
    start_page = handler.load_progress()
    print(f"   应从第 {start_page} 页开始")
    print(f"   已有数据: {len(handler.data)} 条")
    
    print(f"\n2. 获取进度摘要")
    summary = handler.get_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")

def main():
    """主函数"""
    # 确保data目录存在
    if not os.path.exists("data"):
        os.makedirs("data")
        print("创建 data 目录")
    
    # 运行测试
    test_excel_handler()
    test_progress_handler()
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
    print("\n检查 data 目录下的文件：")
    for file in os.listdir("data"):
        size = os.path.getsize(os.path.join("data", file))
        print(f"  - {file} ({size} bytes)")

if __name__ == "__main__":
    main()