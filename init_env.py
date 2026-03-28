#!/usr/bin/env python3
"""
竞赛回收系统 - 环境初始化脚本
用于生成必要的配置文件和目录
"""

import sys
from pathlib import Path

def safe_print(msg):
    """安全的打印函数，防止在 macOS .app 无控制台环境下闪退"""
    if sys.stdout is not None and hasattr(sys.stdout, 'write'):
        try:
            print(msg)
        except Exception:
            pass

def init_environment():
    """初始化环境
    检查并生成必要的文件和目录
    """
    # 直接使用当前工作目录 (main.py 已经统一设置好了)
    current_dir = Path.cwd()
    
    # 检查并生成 students.csv
    students_csv = current_dir / "students.csv"
    if not students_csv.exists():
        safe_print("生成 students.csv 文件...")
        with open(students_csv, "w", encoding="utf-8") as f:
            f.write("exam_id,name,password\n")
            f.write("HA-001,张三,123456\n")
        safe_print(f"已生成: {students_csv}")
    else:
        safe_print(f"students.csv 已存在: {students_csv}")
    
    # 检查并生成 exam_instructions.md
    exam_instructions = current_dir / "exam_instructions.md"
    if not exam_instructions.exists():
        safe_print("生成 exam_instructions.md 文件...")
        with open(exam_instructions, "w", encoding="utf-8") as f:
            f.write("#### 考试规则\n\n")
            f.write("1. 考试时间：120分钟\n")
            f.write("2. 允许使用的语言：C++\n")
            f.write("3. 禁止使用互联网和外部资源\n")
            f.write("4. 代码需在规定时间内上传至系统\n\n")
        safe_print(f"已生成: {exam_instructions}")
    else:
        safe_print(f"exam_instructions.md 已存在: {exam_instructions}")
    
    # 检查 problems.zip
    problems_zip = current_dir / "problems.zip"
    if not problems_zip.exists():
        safe_print("警告: problems.zip 文件不存在")
        safe_print("请将包含竞赛题目的压缩文件放置在当前目录下")
    else:
        safe_print(f"problems.zip 已存在: {problems_zip}")
    
    # 创建上传目录
    data_dir = current_dir / "data"
    data_dir.mkdir(exist_ok=True)
    safe_print(f"数据目录已准备: {data_dir}")
    
    safe_print("环境初始化完成！")

if __name__ == "__main__":
    init_environment()