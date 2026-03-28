#!/bin/bash

echo "========================================="
echo "      竞赛回收系统 - 自动打包脚本 (macOS/Linux)"
echo "========================================="
echo ""

echo "[1/3] 正在清理旧的编译文件..."
rm -rf build dist main.spec

echo ""
echo "[2/3] 正在执行 PyInstaller 打包..."
# 注意：macOS/Linux 下的路径分隔符是冒号 ":"
pyinstaller --noconfirm --onedir --windowed --icon="static/icon.icns" --add-data "templates:templates" --add-data "static:static" --hidden-import server --hidden-import uvicorn --hidden-import aiofiles main.py

echo ""
echo "[3/3] 正在清理打包产生的沉余文件..."
rm -rf build main.spec

echo ""
echo "========================================="
echo "打包完成！"
if [ "$(uname)" == "Darwin" ]; then
    echo "你的程序已生成在 dist/main.app (或 dist/main 目录) 中。"
else
    echo "你的程序已生成在 dist/main 目录下。"
fi
echo "注意：请记得将 problems.zip 和 students.csv 放在程序同级目录中配合使用！"
echo "========================================="
