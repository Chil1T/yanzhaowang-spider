#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研究生招生信息爬虫 - 主程序入口
"""
import argparse
import os
import sys
from typing import Dict, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from spider.core import YanZhaoScraper
from spider.transfer_api import TransferApiSpider


def parse_cli_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="研究生招生信息爬虫")
    parser.add_argument(
        "--transfer-template",
        default="",
        help="调剂模板ID，例如: tj_fuzzy_fulltime_default",
    )
    parser.add_argument(
        "--mldm2",
        default="",
        help="模板模式下的学科门类代码（模糊查询参数）",
    )
    parser.add_argument(
        "--keyword",
        default="",
        help="模板模式下的关键词（招生单位或专业）",
    )
    parser.add_argument(
        "--fhbktj",
        action="store_true",
        help="模板模式下默认只看符合申请条件的余额",
    )
    parser.add_argument(
        "--detail",
        action="store_true",
        help="模板模式下默认抓取申请条件详情",
    )
    return parser.parse_args()


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


def select_spider_mode() -> str:
    """选择爬虫模式"""
    print("\n爬虫模式：")
    print("1. 专业目录爬虫（原功能）")
    print("2. 调剂信息爬虫（支持筛选）")

    choice = input("请选择模式 (1/2)，默认为1: ").strip()
    if choice not in ["1", "2"]:
        return "1"
    return choice


def select_transfer_query_mode() -> str:
    """选择调剂查询模式"""
    print("\n调剂查询模式：")
    print("1. 精准查询（专业关键词）")
    print("2. 模糊查询（学科门类+关键词）")

    choice = input("请选择查询模式 (1/2)，默认为1: ").strip()
    return "fuzzy" if choice == "2" else "precise"


def select_transfer_xxfs() -> str:
    """选择学习方式筛选"""
    print("\n学习方式筛选：")
    print("0. 不限")
    print("1. 全日制")
    print("2. 非全日制")
    choice = input("请选择 (0/1/2)，默认为0: ").strip() or "0"

    mapping = {"0": "", "1": "1", "2": "2"}
    return mapping.get(choice, "")


def select_transfer_zxjh() -> str:
    """选择专项计划筛选"""
    print("\n专项计划筛选：")
    print("0. 不限")
    print("1. 普通计划")
    print("2. 少数民族骨干计划")
    print("3. 退役大学生计划")
    choice = input("请选择 (0/1/2/3)，默认为0: ").strip() or "0"

    mapping = {"0": "", "1": "0", "2": "4", "3": "7"}
    return mapping.get(choice, "")


def select_transfer_filters(query_mode: str) -> dict:
    """采集调剂筛选参数"""
    if query_mode == "precise":
        print("\n精准查询参数：")
        zymc = input("专业关键词（例如：会计，默认会计）: ").strip() or "会计"
        ssdm = input("省市代码（例如：11，北京；留空=不限）: ").strip()
        dwmc = input("招生单位关键词（留空=不限）: ").strip()
        xxfs = select_transfer_xxfs()
        zxjh = select_transfer_zxjh()

        return {
            "orderBy": "",
            "ssdm": ssdm,
            "dwmc": dwmc,
            "xxfs": xxfs,
            "zxjh": zxjh,
            "zymc": zymc,
        }

    print("\n模糊查询参数：")
    mldm2 = input("学科门类代码（例如：12管理学，默认12）: ").strip() or "12"
    dwmc2 = input("关键词（招生单位或专业，默认会计）: ").strip() or "会计"
    ssdm2 = input("省市代码（例如：11，北京；留空=不限）: ").strip()
    xxfs2 = select_transfer_xxfs()
    zxjh2 = select_transfer_zxjh()
    fhbktj_input = input("是否只看符合申请条件的余额？(y/n，默认n): ").strip().lower()
    fhbktj = "1" if fhbktj_input == "y" else ""

    return {
        "orderBy": "",
        "ssdm2": ssdm2,
        "mldm2": mldm2,
        "xxfs2": xxfs2,
        "zxjh2": zxjh2,
        "dwmc2": dwmc2,
        "fhbktj": fhbktj,
    }


def format_transfer_task_summary(
    query_mode: str,
    filters: dict,
    include_detail: bool,
    page_size: int,
) -> str:
    """格式化本次调剂任务摘要"""
    if query_mode == "precise":
        items = [
            f"模式=精准查询",
            f"专业关键词={filters.get('zymc', '') or '空'}",
            f"省市={filters.get('ssdm', '') or '不限'}",
            f"招生单位关键词={filters.get('dwmc', '') or '不限'}",
            f"学习方式={filters.get('xxfs', '') or '不限'}",
            f"专项计划={filters.get('zxjh', '') or '不限'}",
        ]
    else:
        items = [
            f"模式=模糊查询",
            f"关键词={filters.get('dwmc2', '') or '空'}",
            f"学科门类={filters.get('mldm2', '') or '不限'}",
            f"省市={filters.get('ssdm2', '') or '不限'}",
            f"学习方式={filters.get('xxfs2', '') or '不限'}",
            f"专项计划={filters.get('zxjh2', '') or '不限'}",
            f"符合条件={('是' if filters.get('fhbktj') else '否')}",
        ]

    items.append(f"每页={page_size}")
    items.append(f"详情={('是' if include_detail else '否')}")
    return " | ".join(items)


def select_yes_no(prompt: str, default: bool = False) -> bool:
    """读取是/否输入并支持默认值"""
    default_text = "y" if default else "n"
    raw = input(f"{prompt}(y/n，默认{default_text}): ").strip().lower()
    if raw == "":
        return default
    return raw == "y"


def resolve_transfer_template(template_name: str) -> Dict[str, object]:
    """解析调剂模板配置"""
    normalized = (template_name or "").strip().lower()
    alias = {
        "tj_fuzzy_fulltime_default": "tj_fuzzy_fulltime_default",
        "fuzzy_fulltime_default": "tj_fuzzy_fulltime_default",
        "fuzzy-default": "tj_fuzzy_fulltime_default",
    }
    template_id = alias.get(normalized, "")
    if not template_id:
        raise ValueError(
            "不支持的模板ID。可用模板：tj_fuzzy_fulltime_default"
        )

    return {
        "id": template_id,
        "query_mode": "fuzzy",
        "page_size": 20,
        "fixed_filters": {
            "orderBy": "",
            "ssdm2": "",    # 省市不限
            "xxfs2": "1",   # 全日制
            "zxjh2": "0",   # 普通计划
        },
        "mldm2_default": "12",
        "keyword_default": "会计",
    }


def run_transfer_template_mode(cli_args):
    """运行调剂模板模式（连续抓取，会话复用）"""
    template = resolve_transfer_template(cli_args.transfer_template)

    print("\n" + "=" * 60)
    print("调剂信息爬虫（模板模式）")
    print("=" * 60)
    print("模板：调剂-模糊查询-省市不限-学习方式全日制-专项计划普通-每页20")

    scraper = None
    task_index = 1

    current_mldm2 = cli_args.mldm2.strip() or template["mldm2_default"]
    current_keyword = cli_args.keyword.strip() or template["keyword_default"]
    current_fhbktj = bool(cli_args.fhbktj)
    current_detail = bool(cli_args.detail)

    try:
        scraper = TransferApiSpider(headless=False)
        print("浏览器会话已启动，将复用当前登录状态进行连续抓取。")

        while True:
            print("\n" + "-" * 60)
            print(f"模板任务第 {task_index} 次抓取")
            print("-" * 60)

            current_mldm2 = input(
                f"学科门类代码（默认{current_mldm2}）: "
            ).strip() or current_mldm2
            current_keyword = input(
                f"关键词（招生单位或专业，默认{current_keyword}）: "
            ).strip() or current_keyword
            current_fhbktj = select_yes_no(
                "是否只看符合申请条件的余额？",
                default=current_fhbktj,
            )
            current_detail = select_yes_no(
                "是否抓取申请条件详情？",
                default=current_detail,
            )

            filters = dict(template["fixed_filters"])
            filters.update(
                {
                    "mldm2": current_mldm2,
                    "dwmc2": current_keyword,
                    "fhbktj": "1" if current_fhbktj else "",
                }
            )

            summary = format_transfer_task_summary(
                query_mode="fuzzy",
                filters=filters,
                include_detail=current_detail,
                page_size=template["page_size"],
            )
            print(f"\n本次参数：{summary}")

            success, output_file, row_count = scraper.run_task(
                query_mode="fuzzy",
                filters=filters,
                include_detail=current_detail,
                page_size=template["page_size"],
            )

            if success:
                print(f"\n✓ 第 {task_index} 次采集完成，共 {row_count} 条")
                print(f"导出文件：{output_file}")
            else:
                print(f"\n✗ 第 {task_index} 次采集失败，已保存 {row_count} 条（如有）")
                print(f"导出文件：{output_file}")

            if not select_yes_no("\n是否继续下一次抓取？", default=True):
                break
            task_index += 1

    except KeyboardInterrupt:
        print("\n\n用户中断调剂模板抓取")
    finally:
        if scraper is not None:
            scraper.close()
            print("浏览器会话已关闭")


def run_transfer_mode():
    """运行调剂信息爬虫（连续抓取，会话复用）"""
    print("\n" + "=" * 60)
    print("调剂信息爬虫（接口模式）")
    print("=" * 60)

    scraper = None
    task_index = 1

    try:
        scraper = TransferApiSpider(headless=False)
        print("浏览器会话已启动，将复用当前登录状态进行连续抓取。")

        while True:
            print("\n" + "-" * 60)
            print(f"开始第 {task_index} 次调剂抓取")
            print("-" * 60)

            query_mode = select_transfer_query_mode()
            filters = select_transfer_filters(query_mode)

            page_size_input = input("\n每页条数（默认20）: ").strip()
            try:
                page_size = int(page_size_input) if page_size_input else 20
            except ValueError:
                page_size = 20
            if page_size <= 0:
                page_size = 20

            include_detail_input = input("是否抓取申请条件详情？(y/n，默认n): ").strip().lower()
            include_detail = include_detail_input == "y"

            summary = format_transfer_task_summary(
                query_mode=query_mode,
                filters=filters,
                include_detail=include_detail,
                page_size=page_size,
            )
            print(f"\n本次参数：{summary}")

            success, output_file, row_count = scraper.run_task(
                query_mode=query_mode,
                filters=filters,
                include_detail=include_detail,
                page_size=page_size,
            )

            if success:
                print(f"\n✓ 第 {task_index} 次采集完成，共 {row_count} 条")
                print(f"导出文件：{output_file}")
            else:
                print(f"\n✗ 第 {task_index} 次采集失败，已保存 {row_count} 条（如有）")
                print(f"导出文件：{output_file}")

            continue_input = input("\n是否继续下一次抓取？(y/n，默认y): ").strip().lower()
            if continue_input == "n":
                break
            task_index += 1

    except KeyboardInterrupt:
        print("\n\n用户中断调剂抓取")
    finally:
        if scraper is not None:
            scraper.close()
            print("浏览器会话已关闭")


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
    cli_args = parse_cli_args()
    print_header()
    
    try:
        if cli_args.transfer_template:
            run_transfer_template_mode(cli_args)
            print("\n" + "=" * 60)
            print("程序结束")
            print("=" * 60)
            return

        spider_mode = select_spider_mode()

        if spider_mode == "2":
            run_transfer_mode()
            print("\n" + "=" * 60)
            print("程序结束")
            print("=" * 60)
            return

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
