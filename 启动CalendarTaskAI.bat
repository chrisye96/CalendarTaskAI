@echo off
REM CalendarTaskAI 启动脚本（备选方案）
REM 注意：此脚本会短暂闪现命令行窗口

cd /d "%~dp0"
start "" pythonw main.py
