@echo off
chcp 65001 >nul
title Hummingbot Lite - 状态检查

echo ========================================
echo    Hummingbot Lite - 系统状态检查
echo ========================================
echo.

REM 1. 检查 Python
echo [1/6] Python 环境:
python --version 2>nul
if errorlevel 1 (
    echo   [错误] Python 未安装或未添加到 PATH
) else (
    echo   [正常] Python 已安装
)
echo.

REM 2. 检查虚拟环境
echo [2/6] 虚拟环境:
if exist venv (
    echo   [正常] 虚拟环境已创建
    dir venv\Scripts\python.exe >nul 2>&1
    if errorlevel 1 (
        echo   [警告] 虚拟环境可能不完整
    )
) else (
    echo   [错误] 虚拟环境不存在，请运行 install.bat
)
echo.

REM 3. 检查依赖包
echo [3/6] 依赖包:
if exist venv (
    call venv\Scripts\activate.bat >nul 2>&1
    pip show fastapi >nul 2>&1
    if errorlevel 1 (
        echo   [错误] 依赖包未安装或安装不完整
    ) else (
        echo   [正常] 依赖包已安装
        pip list | findstr /i "fastapi uvicorn ccxt" >nul 2>&1
    )
) else (
    echo   [跳过] 虚拟环境不存在
)
echo.

REM 4. 检查配置文件
echo [4/6] 配置文件:
if exist .env (
    echo   [正常] .env 文件存在
    findstr "OKX_API_KEY" .env | findstr "your_api_key_here" >nul
    if not errorlevel 1 (
        echo   [警告] .env 中的 API 密钥未配置
    )
) else (
    echo   [警告] .env 文件不存在（使用默认配置）
)
echo.

REM 5. 检查端口占用
echo [5/6] 端口 5000:
netstat -ano | findstr :5000 >nul
if errorlevel 1 (
    echo   [正常] 端口 5000 未被占用
) else (
    echo   [警告] 端口 5000 已被占用
    netstat -ano | findstr :5000
)
echo.

REM 6. 检查运行状态
echo [6/6] 运行状态:
tasklist | findstr python.exe >nul
if errorlevel 1 (
    echo   [空闲] 没有 Python 进程在运行
) else (
    echo   [运行中] 检测到 Python 进程
    tasklist | findstr python.exe
)
echo.

REM 7. 检查日志文件
echo [7/7] 日志文件:
if exist logs\app.log (
    echo   [正常] 日志文件存在
    for %%A in (logs\app.log) do echo   大小: %%~zA 字节
) else (
    echo   [提示] 日志文件尚未创建
)
echo.

REM 8. 测试 API 连接
echo [8/8] API 连接测试:
if exist venv (
    call venv\Scripts\activate.bat >nul 2>&1
    curl -s http://localhost:5000/api/strategies >nul 2>&1
    if errorlevel 1 (
        echo   [离线] API 服务未响应
    ) else (
        echo   [在线] API 服务正常运行
        echo   访问地址: http://localhost:5000
    )
) else (
    echo   [跳过] 虚拟环境不存在
)
echo.

echo ========================================
echo    状态检查完成
echo ========================================
echo.

REM 提供修复建议
echo 修复建议：
echo   1. 如果虚拟环境不存在：运行 install.bat
echo   2. 如果依赖包未安装：运行 install.bat
echo   3. 如果端口被占用：运行 stop.bat 或修改 .env 中的 PORT
echo   4. 如果 API 密钥未配置：编辑 .env 文件
echo.

pause
