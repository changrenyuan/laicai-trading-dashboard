@echo off
chcp 65001 >nul
title Hummingbot Lite - 环境测试

echo ========================================
echo    Hummingbot Lite - 环境测试
echo ========================================
echo.

cd /d "%~dp0"

REM 检查虚拟环境
if not exist venv (
    echo [错误] 虚拟环境不存在
    echo 请先运行 install.bat 安装程序
    pause
    exit /b 1
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 运行测试
echo 正在运行环境测试...
echo.
python test_environment.py

REM 根据测试结果提供建议
echo.
echo ========================================
echo    测试完成
echo ========================================
echo.
echo 如果测试全部通过，可以：
echo   - 运行 start.bat 启动程序
echo   - 访问 http://localhost:5000
echo.
echo 如果测试失败，可以：
echo   - 运行 fix.bat 自动修复
echo   - 查看 WINDOWS_INSTALL.md 了解详细配置
echo.
pause
