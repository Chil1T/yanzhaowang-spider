#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研究生招生信息爬虫 - 主程序入口
"""
import os
import sys
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from spider.core import YanZhaoScraper


def print_header():
    """打印标题"""
    print("\n" + "=" * 60)
    print("     研究生招生信息爬虫 - 专业版（支持断点续传）")
    print("=" * 60)


def select_major() -> str:
    """
    选择专业
    
    Returns:
        专业代码
    """
    print("\n可用专业：")
    codes = list(config.MAJOR_CONFIG.keys())
    for i, code in enumerate(codes, 1):
        info = config.MAJOR_CONFIG[code]
        print(f"{i}. {info['name']} ({code})")
    
    try:
        choice = input(f"\n请选择专业 (1-{len(codes)})，默认为1: ").strip()
        if choice == "":
            choice = "1"
        choice_idx = int(choice) - 1
        return codes[choice_idx]
    except (ValueError, IndexError):
        print("无效选择，使用默认专业：会计专硕")
        return "125300"


def select_study_mode() -> str:
    """
    选择学习方式
    
    Returns:
        学习方式代码
    """
    print("\n学习方式：")
    print("1. 全日制")
    print("2. 非全日制")
    
    try:
        choice = input("请选择学习方式 (1/2)，默认为1: ").strip()
        if choice == "":
            choice = "1"
        if choice not in ["1", "2"]:
            choice = "1"
        return choice
    except:
        return "1"


def select_info_type() -> str:
    """
    选择信息类型
    
    Returns:
        信息类型代码
    """
    print("\n信息类型：")
    print("1. 硕士点详情（包含专业详细信息）")
    print("2. 仅研招院校（只获取院校名单）")
    
    try:
        choice = input("请选择信息类型 (1/2)，默认为1: ").strip()
        if choice == "":
            choice = "1"
        if choice == "1":
            return "details"
        else:
            return "universities"
    except:
        return "details"


def select_run_mode(scraper: YanZhaoScraper) -> str:
    """
    选择运行模式
    
    Args:
        scraper: 爬虫实例
    
    Returns:
        运行模式代码
    """
    print("\n" + "=" * 60)
    print("运行模式选择：")
    print(f"  已有数据：{len(scraper.data)}条记录")
    print(f"  下次将从第{scraper.current_page}页开始")
    print(f"  剩余页面：{33 - scraper.current_page + 1}页")
    print("-" * 40)
    print("1. 继续之前的任务（推荐）")
    print("2. 重新开始（会覆盖已有数据）")
    print("3. 仅测试运行（第1页，前2个院校）")
    print("4. 退出程序")
    
    return input("请输入选择 (1/2/3/4): ").strip()


def run_test_mode(major_code: str, study_mode: str, info_type: str):
    """运行测试模式"""
    print("\n" + "=" * 60)
    print("测试模式：第1页，前2个院校")
    print("=" * 60)
    
    scraper = YanZhaoScraper(
        major_code=major_code,
        study_mode=study_mode,
        info_type=info_type
    )
    
    try:
        success = scraper.run(start_page=1, end_page=1, max_universities_per_page=2)
        
        if success:
            print(f"\n✓ 测试运行成功！获取到 {len(scraper.data)} 条记录")
            return True
        else:
            print("\n✗ 测试运行失败！")
            return False
            
    except KeyboardInterrupt:
        print("\n\n用户中断测试")
        if scraper.data:
            scraper._emergency_save()
            print(f"已保存 {len(scraper.data)} 条记录")
        return False
    except Exception as e:
        print(f"\n✗ 测试运行出错: {e}")
        return False


def run_full_mode(
    major_code: str,
    study_mode: str,
    info_type: str,
    start_page: Optional[int] = None
):
    """运行完整模式"""
    print("\n" + "=" * 60)
    print("完整模式：爬取所有页面")
    print("=" * 60)
    
    scraper = YanZhaoScraper(
        major_code=major_code,
        study_mode=study_mode,
        info_type=info_type
    )
    
    try:
        print("开始完整运行...")
        scraper.run(start_page=start_page)
        print(f"\n✓ 完整运行完成！总共获取到 {len(scraper.data)} 条记录")
        
    except KeyboardInterrupt:
        print("\n\n用户中断完整运行")
        if scraper.data:
            scraper._emergency_save()
            print(f"已保存 {len(scraper.data)} 条记录")
    except Exception as e:
        print(f"\n✗ 完整运行出错: {e}")
        if scraper.data:
            scraper._emergency_save()
            print(f"已保存 {len(scraper.data)} 条记录")


def main():
    """主函数"""
    print_header()
    
    try:
        # 选择参数
        major_code = select_major()
        study_mode = select_study_mode()
        info_type = select_info_type()
        
        study_mode_name = config.STUDY_MODE[study_mode]
        info_type_name = config.INFO_TYPE[info_type]
        major_name = config.MAJOR_CONFIG[major_code]['name']
        
        print(f"\n已选择：{major_name} - {study_mode_name} - {info_type_name}")
        
        # 创建临时爬虫实例检查进度
        temp_scraper = YanZhaoScraper(
            major_code=major_code,
            study_mode=study_mode,
            info_type=info_type
        )
        
        # 选择运行模式
        run_choice = select_run_mode(temp_scraper)
        
        if run_choice == '1':
            # 继续之前的任务
            run_full_mode(major_code, study_mode, info_type, temp_scraper.current_page)
            
        elif run_choice == '2':
            # 重新开始
            print("\n重新开始任务，将清空已有数据...")
            
            # 删除Excel文件
            scraper = YanZhaoScraper(
                major_code=major_code,
                study_mode=study_mode,
                info_type=info_type
            )
            scraper.excel_handler.delete_file()
            
            run_full_mode(major_code, study_mode, info_type, 1)
            
        elif run_choice == '3':
            # 仅测试运行
            test_success = run_test_mode(major_code, study_mode, info_type)
            
            if test_success:
                user_input = input("\n测试成功，是否继续完整运行所有页面？(y/n): ").strip().lower()
                if user_input == 'y':
                    run_full_mode(major_code, study_mode, info_type)
            else:
                print("\n测试失败，请检查问题后重试")
                
        elif run_choice == '4':
            print("\n程序退出")
            return
        else:
            print("\n无效选择，程序退出")
            return
            
    except KeyboardInterrupt:
        print("\n\n用户中断程序")
    except Exception as e:
        print(f"\n程序运行出错: {e}")
    
    print("\n" + "=" * 60)
    print("程序结束")
    print("=" * 60)


if __name__ == "__main__":
    main()