@echo off
REM 升级 pip
pip install --upgrade pip
REM 安装依赖模块
pip install requests pandas
REM 运行主程序
python overlay.py
pause
