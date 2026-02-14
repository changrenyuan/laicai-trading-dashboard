# Hummingbot Lite - Windows 运行指南

## 一、前置要求

### 1. 安装 Python
- 下载 Python 3.10 或更高版本：https://www.python.org/downloads/
- **重要**：安装时勾选 "Add Python to PATH"
- 验证安装：
```powershell
python --version
# 或
python3 --version
```

### 2. 安装 Git（可选，如果从 GitHub 克隆）
- 下载：https://git-scm.com/download/win

## 二、安装项目

### 1. 获取项目代码

**方法1：使用 Git 克隆**
```powershell
cd C:\
git clone <你的项目地址>
cd hummingbot-lite
```

**方法2：直接下载压缩包**
- 下载项目 ZIP 文件
- 解压到 `C:\hummingbot-lite`

### 2. 创建虚拟环境（推荐）

```powershell
cd C:\hummingbot-lite

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\activate

# 成功激活后，命令行前会显示 (venv)
```

### 3. 安装依赖

```powershell
# 确保 virtualenv 已激活
pip install --upgrade pip
pip install -r requirements.txt
```

## 三、配置文件

### 1. 创建 .env 文件

在项目根目录创建 `.env` 文件，内容如下：

```env
# OKX API 配置
OKX_API_KEY=your_api_key_here
OKX_API_SECRET=your_api_secret_here
OKX_API_PASSPHRASE=your_passphrase_here
OKX_SANDBOX=true

# 交易配置
DEFAULT_TRADING_PAIR=BTC-USDT
DEFAULT_ORDER_AMOUNT=0.001

# 风控配置
MAX_POSITION_SIZE=0.1
MAX_DAILY_LOSS=1000

# 服务器配置
HOST=0.0.0.0
PORT=5000
```

### 2. 获取 OKX API 密钥（实盘交易）

1. 访问 https://www.okx.com/
2. 注册/登录账号
3. 进入 "API" 页面
4. 创建 API Key，配置权限：
   - 读取权限：勾选
   - 交易权限：勾选
   - 提现权限：**不勾选**（安全考虑）
5. 记录 API Key、Secret 和 Passphrase
6. 更新 `.env` 文件中的对应值

**注意**：首次使用建议设置 `OKX_SANDBOX=true` 使用模拟环境测试

## 四、运行项目

### 方法1：命令行运行

```powershell
# 1. 激活虚拟环境
cd C:\hummingbot-lite
.\venv\Scripts\activate

# 2. 运行程序
python src/main_multi_strategy_demo.py
```

### 方法2：使用批处理文件（推荐）

创建 `start.bat` 文件：

```batch
@echo off
chcp 65001
echo ========================================
echo    Hummingbot Lite - 启动脚本
echo ========================================
echo.

cd /d "%~dp0"

REM 激活虚拟环境
if exist venv\Scripts\activate.bat (
    echo 正在激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo [错误] 虚拟环境不存在，请先运行 install.bat
    pause
    exit /b 1
)

REM 运行程序
echo.
echo 正在启动 Hummingbot Lite...
echo.
python src/main_multi_strategy_demo.py

REM 如果程序退出，暂停以查看错误信息
pause
```

创建 `install.bat` 文件：

```batch
@echo off
chcp 65001
echo ========================================
echo    Hummingbot Lite - 安装脚本
echo ========================================
echo.

cd /d "%~dp0"

REM 创建虚拟环境
echo [1/3] 创建虚拟环境...
python -m venv venv
if errorlevel 1 (
    echo [错误] 创建虚拟环境失败
    pause
    exit /b 1
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 升级 pip
echo [2/3] 升级 pip...
python -m pip install --upgrade pip

REM 安装依赖
echo [3/3] 安装依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 安装依赖失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo    安装完成！
echo ========================================
echo.
echo 下一步：
echo   1. 编辑 .env 文件配置 API 密钥
echo   2. 运行 start.bat 启动程序
echo.
pause
```

**使用方法：**
1. 首次运行：双击 `install.bat`
2. 配置 `.env` 文件
3. 启动程序：双击 `start.bat`

## 五、访问 Web UI

启动成功后，在浏览器中访问：

```
http://localhost:5000
```

## 六、常见问题处理

### 问题1：'python' 不是内部或外部命令

**解决方法：**
```powershell
# 尝试使用 py 命令
py --version

# 或使用 python3
python3 --version

# 如果都不行，重新安装 Python，确保勾选 "Add Python to PATH"
```

### 问题2：pip 安装依赖失败

**解决方法：**
```powershell
# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用阿里云镜像
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

### 问题3：端口 5000 被占用

**解决方法：**
```powershell
# 查看占用 5000 端口的进程
netstat -ano | findstr :5000

# 结束进程（替换 PID 为实际进程 ID）
taskkill /PID <进程ID> /F

# 或修改 .env 文件中的 PORT=5001
```

### 问题4：虚拟环境激活失败

**PowerShell 执行策略限制：**
```powershell
# 临时允许执行脚本
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# 然后再激活
.\venv\Scripts\activate.ps1
```

**或使用 CMD：**
```cmd
venv\Scripts\activate.bat
```

### 问题5：缺少 C++ 编译器（某些包需要）

**解决方法：**
1. 下载 Microsoft C++ Build Tools：https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. 安装 "Desktop development with C++"
3. 重新运行 pip install

### 问题6：WebSocket 连接失败

**检查防火墙：**
```powershell
# 允许 Python 通过防火墙
New-NetFirewallRule -DisplayName "Python" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

## 七、开发模式运行

如需热重载（代码修改后自动重启）：

```powershell
# 安装 watchdog
pip install watchdog

# 使用 watchdog 运行
watchmedo auto-restart --directory=./src --pattern="*.py" --recursive -- python src/main_multi_strategy_demo.py
```

## 八、后台运行（Windows 服务）

### 使用 NSSM（推荐）

1. 下载 NSSM：https://nssm.cc/download
2. 安装服务：
```powershell
nssm install HummingbotLite "C:\hummingbot-lite\venv\Scripts\python.exe" "C:\hummingbot-lite\src\main_multi_strategy_demo.py"
nssm set HummingbotLite AppDirectory "C:\hummingbot-lite"
nssm set HummingbotLite DisplayName "Hummingbot Lite"
nssm start HummingbotLite
```

### 使用 Python 后台脚本

创建 `run_background.py`：
```python
import subprocess
import sys
import os

# 隐藏控制台
startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startupinfo.wShowWindow = subprocess.SW_HIDE

# 运行程序
script = os.path.join(os.path.dirname(__file__), "src", "main_multi_strategy_demo.py")
subprocess.Popen([sys.executable, script], startupinfo=startupinfo)
```

## 九、日志查看

日志位置：
```
C:\hummingbot-lite\logs\
```

实时查看日志：
```powershell
# PowerShell
Get-Content logs\app.log -Wait -Tail 50

# 或使用 tail for Windows
tail -f logs\app.log
```

## 十、卸载

```powershell
# 1. 停止服务（如果安装为服务）
nssm stop HummingbotLite
nssm remove HummingbotLite confirm

# 2. 删除项目目录
Remove-Item -Recurse -Force C:\hummingbot-lite
```

## 十一、快速启动指南（完整流程）

```powershell
# 1. 安装 Python 3.10+ 并添加到 PATH

# 2. 获取项目代码
cd C:\
git clone <项目地址>
cd hummingbot-lite

# 3. 创建虚拟环境并安装依赖
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# 4. 配置 .env 文件
# 复制 .env.example 为 .env 并编辑

# 5. 启动程序
python src/main_multi_strategy_demo.py

# 6. 访问 http://localhost:5000
```

## 十二、系统要求

- **操作系统**：Windows 10/11（64位）
- **Python**：3.10 或更高版本
- **内存**：最少 2GB RAM，推荐 4GB+
- **磁盘空间**：最少 500MB
- **网络**：稳定的互联网连接

## 十三、性能优化建议

1. **使用 SSD**：将项目放在 SSD 上提升性能
2. **关闭杀毒软件实时扫描**：将项目目录添加到白名单
3. **增加 Python 内存限制**：如果遇到内存不足
4. **使用 PowerShell 7**：比传统 PowerShell 更快

## 十四、技术支持

遇到问题？
1. 查看 `logs/` 目录下的日志文件
2. 检查 .env 配置是否正确
3. 确保所有依赖已正确安装
4. 检查防火墙和端口设置

---

**提示**：首次使用建议在模拟环境（OKX_SANDBOX=true）下测试，熟悉操作后再切换到实盘环境。
