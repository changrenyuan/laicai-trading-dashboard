# Windows + Clash 代理配置说明

## 1. Clash 默认端口

Clash 常用的代理端口：
- **HTTP 代理**：`127.0.0.1:7890`
- **SOCKS5 代理**：`127.0.0.1:7891`
- **控制面板**：`http://127.0.0.1:9090/ui`

> 注意：你的 Clash 端口可能不同，请在 Clash 设置中查看

## 2. 配置方法

### 方法一：系统代理（推荐）

1. 打开 Clash，开启 **系统代理**
2. 确认端口设置（通常是 7890）
3. 系统会自动使用 Clash 代理

### 方法二：环境变量配置

**Windows CMD：**
```cmd
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
```

**Windows PowerShell：**
```powershell
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
```

**永久设置（系统环境变量）：**
1. 右键"此电脑" → 属性 → 高级系统设置 → 环境变量
2. 新建系统变量：
   - 变量名：`HTTP_PROXY`
   - 变量值：`http://127.0.0.1:7890`
   - 变量名：`HTTPS_PROXY`
   - 变量值：`http://127.0.0.1:7890`

### 方法三：后端代码配置（Python）

修改 `start_backend.py`，添加代理配置：

```python
import aiohttp
import os

# 设置代理
proxies = os.environ.get('HTTP_PROXY') or 'http://127.0.0.1:7890'

# 创建带代理的 HTTP session
session = aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(limit=10),
    timeout=aiohttp.ClientTimeout(total=10)
)

# 请求时使用代理
async with session.get(url, proxy=proxies) as response:
    data = await response.json()
```

## 3. 验证代理是否生效

```python
import requests

proxies = {
    'http': 'http://127.0.0.1:7890',
    'https': 'http://127.0.0.1:7890'
}

try:
    response = requests.get('https://www.google.com', proxies=proxies, timeout=5)
    print('代理生效，状态码:', response.status_code)
except Exception as e:
    print('代理未生效，错误:', e)
```

## 4. 当前项目使用说明

### 后端（Python）

后端连接真实交易所时使用代理，在 `src/exchanges/okx_mock.py` 或真实交易所代码中配置：

```python
# 在 aiohttp 请求中使用代理
async with self._session.get(url, proxy='http://127.0.0.1:7890') as response:
    return await response.json()
```

### 前端（Vue）

前端通过 Vite Proxy 转发请求到后端，不需要额外配置 Clash。

但如果前端需要直接访问外部 API（如 WebSocket 连接交易所），可以在 `.env.development` 中配置：

```env
# API 代理配置（后端 API）
VITE_API_BASE_URL=

# 如果前端需要直接访问外部 API
VITE_EXTERNAL_API_PROXY=http://127.0.0.1:7890
```

## 5. 常见问题

### Q1: 代理端口不是 7890 怎么办？
A: 在 Clash 设置中查看实际端口，替换上面的配置。

### Q2: 后端无法连接交易所？
A: 检查后端代码中是否正确配置了代理。

### Q3: 前端刷新账户余额失败？
A: 检查：
1. 后端服务是否正常运行（http://localhost:5000）
2. 浏览器控制台是否有错误（F12 → Console）
3. 网络请求是否成功（F12 → Network）
4. 后端日志是否有错误

## 6. 快速测试

### 测试后端 API
```bash
curl http://localhost:5000/api/status
```

### 测试前端（通过代理）
打开浏览器访问：http://localhost:5173

### 查看调试日志
- 前端：打开浏览器控制台（F12），查看 `[API Client]` 和 `[Account Store]` 开头的日志
- 后端：查看控制台输出或日志文件

---

**提示**：如果使用 Mock 交易所（当前默认），不需要配置代理也能运行。只有连接真实交易所时才需要代理。
