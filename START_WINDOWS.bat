@echo off
REM 华为杯研赛比赛日初始化入口（Windows）
REM 来源：演进自 v2.1 比赛当天初始化.bat
chcp 65001 >nul
cd /d "%~dp0"
echo === Huaweibei-cool 比赛日初始化 ===
python scripts\contest_init.py %*
pause
