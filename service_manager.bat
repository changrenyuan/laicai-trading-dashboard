@echo off
chcp 65001 >nul
title Hummingbot Lite - 服务管理

echo ========================================
echo    Hummingbot Lite - Windows 服务管理
echo ========================================
echo.

cd /d "%~dp0"

REM 检查 NSSM 是否安装
where nssm >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 NSSM
    echo 请先下载并安装 NSSM: https://nssm.cc/download
    echo.
    pause
    exit /b 1
)

REM 显示菜单
:menu
cls
echo ========================================
echo    Hummingbot Lite - 服务管理
echo ========================================
echo.
echo 1. 安装服务
echo 2. 启动服务
echo 3. 停止服务
echo 4. 卸载服务
echo 5. 查看服务状态
echo 6. 查看服务日志
echo 0. 退出
echo.
set /p choice=请选择操作 (0-6):

if "%choice%"=="1" goto install
if "%choice%"=="2" goto start
if "%choice%"=="3" goto stop
if "%choice%"=="4" goto remove
if "%choice%"=="5" goto status
if "%choice%"=="6" goto logs
if "%choice%"=="0" goto end
goto menu

:install
echo.
echo [安装服务]
echo.
nssm install HummingbotLite "%~dp0venv\Scripts\python.exe" "%~dp0src\main_multi_strategy_demo.py"
nssm set HummingbotLite AppDirectory "%~dp0"
nssm set HummingbotLite DisplayName "Hummingbot Lite"
nssm set HummingbotLite Description "Hummingbot Lite 量化交易机器人"
nssm set HummingbotLite Start SERVICE_AUTO_START
nssm set HummingbotLite AppStdout "%~dp0logs\service_stdout.log"
nssm set HummingbotLite AppStderr "%~dp0logs\service_stderr.log"
nssm set HummingbotLite AppRotateFiles 1
nssm set HummingbotLite AppRotateBytes 1048576
echo.
echo [成功] 服务已安装
echo.
pause
goto menu

:start
echo.
echo [启动服务]
echo.
nssm start HummingbotLite
if errorlevel 1 (
    echo [错误] 启动失败
) else (
    echo [成功] 服务已启动
    echo 访问地址: http://localhost:5000
)
echo.
pause
goto menu

:stop
echo.
echo [停止服务]
echo.
nssm stop HummingbotLite
if errorlevel 1 (
    echo [错误] 停止失败
) else (
    echo [成功] 服务已停止
)
echo.
pause
goto menu

:remove
echo.
echo [卸载服务]
echo.
nssm stop HummingbotLite
nssm remove HummingbotLite confirm
echo.
echo [成功] 服务已卸载
echo.
pause
goto menu

:status
echo.
echo [服务状态]
echo.
nssm status HummingbotLite
echo.
echo 服务详细信息:
nssm dump HummingbotLite
echo.
pause
goto menu

:logs
echo.
echo [服务日志]
echo.
if exist logs\service_stdout.log (
    echo 标准输出日志:
    type logs\service_stdout.log
) else (
    echo [提示] 日志文件不存在
)
echo.
if exist logs\service_stderr.log (
    echo 错误输出日志:
    type logs\service_stderr.log
)
echo.
pause
goto menu

:end
echo.
echo 退出
exit /b 0
