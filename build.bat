@echo off
chcp 65001 >nul
echo =========================================
echo       竞赛回收系统 - 自动打包脚本 (Windows)
echo =========================================

echo.
echo [1/3] 正在清理旧的编译文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist main.spec del /q main.spec

echo.
echo [2/3] 正在执行 PyInstaller 打包...
pyinstaller --noconfirm --onedir --windowed --icon="static/icon.ico" --add-data "templates;templates" --add-data "static;static" --hidden-import server --hidden-import uvicorn --hidden-import aiofiles main.py

echo.
echo [3/3] 正在清理打包产生的沉余文件...
if exist build rmdir /s /q build
if exist main.spec del /q main.spec

echo.
echo =========================================
echo 打包完成！
echo 你的程序已生成在 dist\main 目录下。
echo 注意：请记得将 problems.zip 和 students.csv 放在该目录中配合使用！
echo =========================================
pause
