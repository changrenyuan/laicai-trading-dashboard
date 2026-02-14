@echo off
chcp 65001 >nul
title Hummingbot Lite - 启动脚本

echo ========================================
echo    Hummingbot Lite - 启动中...
echo ========================================
echo.

cd /d "%~dp0"

REM 检查虚拟环境是否存在
if not exist venv (
    echo [错误] 虚拟环境不存在
    echo 请先运行 install.bat 安装程序
    pause
    exit /b 1
)

REM 检查 .env 文件是否存在
if not exist .env (
    echo [警告] .env 文件不存在，使用默认配置
    echo 建议运行 install.bat 创建配置文件
    echo.
)

REM 激活虚拟环境
echo 正在激活虚拟环境...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [错误] 激活虚拟环境失败
    pause
    exit /b 1
)

REM 检查 Python 版本
echo Python 版本:
python --version
echo.

REM 检查端口是否被占用
echo 检查端口 5000...
netstat -ano | findstr :5000 >nul
if not errorlevel 1 (
    echo [警告] 端口 5000 已被占用
    echo 请检查是否有其他程序正在使用该端口
    echo 或者修改 .env 文件中的 PORT 配置
    echo.
    choice /C YN /M "是否继续启动？(Y/N)"
    if errorlevel 2 (
        exit /b 0
    )
)

echo.
echo ========================================
echo    Hummingbot Lite 正在启动
echo ========================================
echo.
echo 访问地址: http://localhost:5000
echo 按 Ctrl+C 停止程序
echo.
echo ========================================
echo.

REM 运行程序
python src/main_multi_strategy_demo.py

REM 如果程序意外退出，暂停以查看错误
if errorlevel 1 (
    echo.
    echo ========================================
    echo    程序异常退出
    echo ========================================
    echo 请检查日志文件获取详细错误信息
    echo 日志位置: logs\app.log
    echo.
    pause
)
