# 代理配置指南

OKX 交易所在中国大陆需要通过代理访问。本系统支持多种代理配置方式。

## 支持的代理类型

### 1. Clash 代理（推荐）

Clash 是最常用的代理工具，默认端口配置：
- HTTP 代理端口：7890
- SOCKS5 代理端口：7891

#### 配置示例

```python
config = {
    "api_key": "your-api-key",
    "secret_key": "your-secret-key",
    "passphrase": "your-passphrase",
    "proxy": "clash"  # 或 "clash-http"
}
```

使用 SOCKS5 代理（需要安装 `aiohttp-socks`）：

```python
config = {
    "api_key": "your-api-key",
    "secret_key": "your-secret-key",
    "passphrase": "your-passphrase",
    "proxy": "clash-socks5"
}
```

### 2. HTTP 代理

使用完整的 HTTP 代理 URL：

```python
config = {
    "api_key": "your-api-key",
    "secret_key": "your-secret-key",
    "passphrase": "your-passphrase",
    "proxy": "http://127.0.0.1:7890"
}
```

或指定其他代理地址：

```python
config = {
    "api_key": "your-api-key",
    "secret_key": "your-secret-key",
    "passphrase": "your-passphrase",
    "proxy": "http://192.168.1.100:8080"
}
```

### 3. SOCKS5 代理

使用 SOCKS5 代理（需要安装 `aiohttp-socks`）：

```bash
pip install aiohttp-socks
```

```python
config = {
    "api_key": "your-api-key",
    "secret_key": "your-secret-key",
    "passphrase": "your-passphrase",
    "proxy": "socks5://127.0.0.1:7891"
}
```

### 4. 端口号（快捷方式）

直接指定端口号，自动使用 HTTP 协议：

```python
config = {
    "api_key": "your-api-key",
    "secret_key": "your-secret-key",
    "passphrase": "your-passphrase",
    "proxy": "7890"  # 等同于 http://127.0.0.1:7890
}
```

## 使用示例

### 基础使用

```python
from src.connectors.okx_lite import OKXConnector

config = {
    "api_key": "your-api-key",
    "secret_key": "your-secret-key",
    "passphrase": "your-passphrase",
    "proxy": "clash"  # 使用 Clash HTTP 代理
}

async def main():
    async with OKXConnector(config) as okx:
        # 测试连接
        if await okx.test_connection():
            print("✅ 连接成功！")

            # 获取行情
            ticker = await okx.get_ticker("BTC-USDT")
            print(f"BTC 价格: {ticker['last']}")

        else:
            print("❌ 连接失败，请检查代理配置")

import asyncio
asyncio.run(main())
```

### 完整示例

查看 `config_proxy_example.py` 获取更多示例。

## 代理测试

在正式使用前，建议先测试代理是否可用：

```python
from src.connectors.okx_lite.proxy_manager import ProxyManager

# 测试 Clash 代理
proxy_url = "http://127.0.0.1:7890"
if ProxyManager.check_proxy(proxy_url):
    print("代理可用")
else:
    print("代理不可用")
```

## 常见问题

### 1. 连接超时

**问题**：`TimeoutError` 或 `ConnectionError`

**解决方案**：
- 确认代理软件（Clash 等）已启动
- 检查代理端口是否正确
- 测试代理是否可以访问 OKX

### 2. SOCKS5 代理报错

**问题**：`ModuleNotFoundError: No module named 'aiohttp_socks'`

**解决方案**：
```bash
pip install aiohttp-socks
```

### 3. 认证失败

**问题**：401 或 403 错误

**解决方案**：
- 检查 API Key、Secret、Passphrase 是否正确
- 确认 IP 白名单设置（如启用）
- 检查账户权限

### 4. 沙盒环境连接

如需测试沙盒环境：

```python
config = {
    "api_key": "your-sandbox-api-key",
    "secret_key": "your-sandbox-secret-key",
    "passphrase": "your-sandbox-passphrase",
    "sandbox": True,
    "proxy": "clash"
}
```

## Clash 配置示例

### 安装 Clash

1. 下载 Clash：https://github.com/Dreamacro/clash/releases
2. 配置订阅地址
3. 启动 Clash

### 默认端口

Clash 默认端口配置：
- HTTP 代理：`127.0.0.1:7890`
- SOCKS5 代理：`127.0.0.1:7891`

### 使用系统代理

如果系统已设置代理（环境变量），系统会自动检测：

```bash
# Linux/Mac
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890

# Windows
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
```

## 性能优化

### 使用 SOCKS5

SOCKS5 代理通常比 HTTP 代理性能更好：

```python
config = {
    "api_key": "your-api-key",
    "secret_key": "your-secret-key",
    "passphrase": "your-passphrase",
    "proxy": "socks5://127.0.0.1:7891"  # Clash SOCKS5 端口
}
```

### 连接池复用

连接器内部已实现连接池复用，无需额外配置。

## 安全建议

1. **不要泄露 API 密钥**：确保配置文件不在版本控制中
2. **使用 IP 白名单**：在 OKX 设置中启用 IP 白名单
3. **限制 API 权限**：只授予必要的权限（交易、读取）
4. **定期轮换密钥**：定期更换 API 密钥
5. **使用沙盒测试**：先在沙盒环境测试策略

## 参考资料

- [OKX API 文档](https://www.okx.com/docs-v5/)
- [Clash 官方文档](https://lancellc.gitbook.io/clash/)
- [aiohttp 文档](https://docs.aiohttp.org/)
