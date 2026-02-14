@echo off
chcp 65001 >nul
title Hummingbot Lite - 安装脚本

echo ========================================
echo    Hummingbot Lite - 安装脚本
echo ========================================
echo.

cd /d "%~dp0"

REM 检查 Python 是否安装
echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    echo 注意：安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)
python --version
echo.

REM 检查虚拟环境是否存在
if exist venv (
    echo [警告] 虚拟环境已存在，是否重新创建？
    echo 选择 Y 删除并重新创建，选择 N 保留现有环境
    choice /C YN /M "请选择 (Y/N)"
    if errorlevel 2 (
        echo 使用现有虚拟环境...
        goto install_deps
    )
    echo 正在删除现有虚拟环境...
    rmdir /s /q venv
)

REM 创建虚拟环境
echo [2/5] 创建虚拟环境...
python -m venv venv
if errorlevel 1 (
    echo [错误] 创建虚拟环境失败
    pause
    exit /b 1
)
echo 虚拟环境创建成功！
echo.

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 升级 pip
echo [3/5] 升级 pip...
python -m pip install --upgrade pip
echo.

REM 安装依赖
echo [4/5] 安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 安装依赖失败，请检查网络连接
    echo 提示：可以使用国内镜像源加速安装
    echo pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    pause
    exit /b 1
)
echo.

:install_deps
REM 创建 .env 文件
echo [5/5] 配置文件检查...
if not exist .env (
    echo 正在创建 .env 配置文件...
    copy .env.example .env
    echo [提示] 请编辑 .env 文件配置您的 API 密钥
    echo.
) else (
    echo .env 配置文件已存在
    echo.
)

echo ========================================
echo    安装完成！
echo ========================================
echo.
echo 下一步操作：
echo   1. 编辑 .env 文件配置 API 密钥（实盘交易必需）
echo   2. 双击 start.bat 启动程序
echo   3. 在浏览器访问 http://localhost:5000
echo.
echo [提示] 首次使用建议在模拟环境测试
echo.
pause
