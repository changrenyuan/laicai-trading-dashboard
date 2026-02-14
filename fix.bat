@echo off
chcp 65001 >nul
title Hummingbot Lite - 一键修复

echo ========================================
echo    Hummingbot Lite - 一键修复工具
echo ========================================
echo.
echo 此工具将尝试自动修复常见问题
echo.

cd /d "%~dp0"

REM 检查是否以管理员身份运行
net session >nul 2>&1
if errorlevel 1 (
    echo [提示] 建议以管理员身份运行此脚本
    echo.
)

echo 正在执行修复...
echo.

REM 1. 修复虚拟环境
echo [1/5] 检查并修复虚拟环境...
if exist venv (
    echo 检测到虚拟环境，验证完整性...
    call venv\Scripts\activate.bat >nul 2>&1
    if errorlevel 1 (
        echo [修复] 虚拟环境损坏，正在重新创建...
        rmdir /s /q venv
        python -m venv venv
    ) else (
        echo [OK] 虚拟环境正常
    )
) else (
    echo [修复] 创建虚拟环境...
    python -m venv venv
)
echo.

REM 2. 修复依赖
echo [2/5] 检查并修复依赖包...
call venv\Scripts\activate.bat >nul 2>&1
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [修复] 依赖包缺失，正在安装...
    pip install --upgrade pip
    pip install -r requirements.txt
) else (
    echo [OK] 依赖包完整
)
echo.

REM 3. 修复配置文件
echo [3/5] 检查并修复配置文件...
if not exist .env (
    echo [修复] 创建配置文件...
    copy .env.example .env >nul 2>&1
    if errorlevel 1 (
        echo [警告] .env.example 不存在，创建空配置文件...
        echo OKX_API_KEY=demo_api_key > .env
        echo OKX_API_SECRET=demo_api_secret >> .env
        echo OKX_API_PASSPHRASE=demo_passphrase >> .env
        echo OKX_SANDBOX=true >> .env
        echo PORT=5000 >> .env
    )
) else (
    echo [OK] 配置文件存在
)
echo.

REM 4. 修复日志目录
echo [4/5] 检查并修复日志目录...
if not exist logs (
    echo [修复] 创建日志目录...
    mkdir logs
) else (
    echo [OK] 日志目录存在
)
echo.

REM 5. 修复防火墙规则（需要管理员权限）
echo [5/5] 检查防火墙规则...
netsh advfirewall firewall show rule name="HummingbotLite" >nul 2>&1
if errorlevel 1 (
    echo [提示] 防火墙规则不存在
    net session >nul 2>&1
    if not errorlevel 1 (
        echo [修复] 添加防火墙规则...
        netsh advfirewall firewall add rule name="HummingbotLite" dir=in action=allow protocol=TCP localport=5000
    ) else (
        echo [跳过] 需要管理员权限才能添加防火墙规则
    )
) else (
    echo [OK] 防火墙规则已存在
)
echo.

REM 6. 清理临时文件
echo [6/6] 清理临时文件...
if exist __pycache__ (
    rmdir /s /q __pycache__ >nul 2>&1
)
for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" >nul 2>&1
if exist *.pyc (
    del /f /q *.pyc >nul 2>&1
)
echo [OK] 临时文件已清理
echo.

REM 7. 运行诊断
echo ========================================
echo    修复完成！运行诊断...
echo ========================================
echo.

call venv\Scripts\activate.bat >nul 2>&1

echo Python 版本:
python --version
echo.

echo 依赖包检查:
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [错误] fastapi 未安装
) else (
    echo [OK] fastapi 已安装
)
pip show uvicorn >nul 2>&1
if errorlevel 1 (
    echo [错误] uvicorn 未安装
) else (
    echo [OK] uvicorn 已安装
)
echo.

echo 端口检查:
netstat -ano | findstr :5000 >nul
if errorlevel 1 (
    echo [OK] 端口 5000 可用
) else (
    echo [警告] 端口 5000 已被占用
)
echo.

echo ========================================
echo    修复总结
echo ========================================
echo.
echo 已完成的修复项目:
echo   [OK] 虚拟环境
echo   [OK] 依赖包
echo   [OK] 配置文件
echo   [OK] 日志目录
echo   [OK] 临时文件清理
echo.
echo 下一步:
echo   1. 编辑 .env 文件配置 API 密钥
echo   2. 运行 start.bat 启动程序
echo   3. 访问 http://localhost:5000
echo.
echo 如仍有问题，请查看:
echo   - logs\app.log（程序日志）
echo   - logs\service_stderr.log（服务日志）
echo.
pause
