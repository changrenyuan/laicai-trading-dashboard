# Hummingbot Lite PowerShell 启动脚本
# 使用方法：右键 -> 使用 PowerShell 运行

# 设置编码为 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 颜色函数
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-ColorOutput Green "========================================"
Write-ColorOutput Green "   Hummingbot Lite - PowerShell 启动"
Write-ColorOutput Green "========================================"
Write-Host ""

# 切换到脚本所在目录
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptPath

# 检查 Python
Write-Host "检查 Python 环境..."
try {
    $pythonVersion = python --version 2>&1
    Write-ColorOutput Cyan "  $pythonVersion"
} catch {
    Write-ColorOutput Red "  [错误] Python 未安装或未添加到 PATH"
    Write-Host "  请从 https://www.python.org/downloads/ 下载安装"
    pause
    exit 1
}

# 检查虚拟环境
Write-Host ""
Write-Host "检查虚拟环境..."
if (Test-Path "venv") {
    Write-ColorOutput Cyan "  [OK] 虚拟环境已存在"
} else {
    Write-ColorOutput Red "  [错误] 虚拟环境不存在"
    Write-Host "  请运行 install.bat 创建虚拟环境"
    pause
    exit 1
}

# 激活虚拟环境
Write-Host ""
Write-Host "激活虚拟环境..."
& ".\venv\Scripts\Activate.ps1"

# 检查端口
Write-Host ""
Write-Host "检查端口 5000..."
$portInUse = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-ColorOutput Yellow "  [警告] 端口 5000 已被占用"
    $response = Read-Host "  是否继续? (Y/N)"
    if ($response -ne "Y" -and $response -ne "y") {
        exit 0
    }
} else {
    Write-ColorOutput Cyan "  [OK] 端口 5000 可用"
}

# 检查配置文件
Write-Host ""
Write-Host "检查配置文件..."
if (Test-Path ".env") {
    Write-ColorOutput Cyan "  [OK] .env 文件存在"
} else {
    Write-ColorOutput Yellow "  [提示] .env 文件不存在，使用默认配置"
}

# 启动程序
Write-Host ""
Write-ColorOutput Green "========================================"
Write-ColorOutput Green "   启动 Hummingbot Lite"
Write-ColorOutput Green "========================================"
Write-Host ""
Write-ColorOutput Cyan "访问地址: http://localhost:5000"
Write-Host "按 Ctrl+C 停止程序"
Write-Host ""
Write-ColorOutput Green "========================================"
Write-Host ""

try {
    python src\main_multi_strategy_demo.py
} catch {
    Write-Host ""
    Write-ColorOutput Red "程序异常退出"
    Write-Host "请检查日志文件: logs\app.log"
    pause
}
