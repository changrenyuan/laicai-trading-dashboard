@echo off
chcp 65001 >nul
title Hummingbot Lite - 停止脚本

echo ========================================
echo    Hummingbot Lite - 停止程序
echo ========================================
echo.

REM 查找 Python 进程中运行 main_multi_strategy_demo.py 的进程
echo 正在查找运行中的 Hummingbot Lite 进程...
echo.

for /f "tokens=2" %%i in ('tasklist ^| findstr python.exe') do (
    set PID=%%i
    echo 找到进程 ID: !PID!
    
    REM 尝试优雅关闭
    taskkill /PID !PID! /T >nul 2>&1
    
    if errorlevel 1 (
        echo [警告] 进程 !PID! 无法正常关闭
    ) else (
        echo [成功] 进程 !PID! 已关闭
    )
)

echo.
tasklist | findstr python.exe >nul
if not errorlevel 1 (
    echo [提示] 还有其他 Python 进程在运行
) else (
    echo [成功] 所有 Hummingbot Lite 进程已关闭
)

echo.
echo ========================================
echo.
pause
