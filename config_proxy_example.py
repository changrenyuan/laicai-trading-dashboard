"""
OKX 连接器代理配置示例

支持多种代理配置方式：
"""

# ============================================================================
# 配置 1: Clash 代理（最简单）
# ============================================================================
# Clash 默认端口: HTTP=7890, SOCKS5=7891

config_clash_http = {
    "api_key": "your-api-key",
    "secret_key": "your-secret-key",
    "passphrase": "your-passphrase",
    "proxy": "clash"  # 或 "clash-http"
}

config_clash_socks5 = {
    "api_key": "your-api-key",
    "secret_key": "your-secret-key",
    "passphrase": "your-passphrase",
    "proxy": "clash-socks5"
}

# ============================================================================
# 配置 2: 直接指定端口号
# ============================================================================
# 使用端口号会自动使用 HTTP 代理协议

config_port = {
    "api_key": "your-api-key",
    "secret_key": "your-secret-key",
    "passphrase": "your-passphrase",
    "proxy": "7890"  # 等同于 http://127.0.0.1:7890
}

# ============================================================================
# 配置 3: HTTP 代理（完整 URL）
# ============================================================================

config_http_proxy = {
    "api_key": "your-api-key",
    "secret_key": "your-secret-key",
    "passphrase": "your-passphrase",
    "proxy": "http://127.0.0.1:7890"
}

# ============================================================================
# 配置 4: SOCKS5 代理（需要安装 aiohttp-socks）
# ============================================================================
# 安装: pip install aiohttp-socks

config_socks5_proxy = {
    "api_key": "your-api-key",
    "secret_key": "your-secret-key",
    "passphrase": "your-passphrase",
    "proxy": "socks5://127.0.0.1:7891"
}

# ============================================================================
# 配置 5: 无代理（适用于可以直接访问 OKX 的地区）
# ============================================================================

config_no_proxy = {
    "api_key": "your-api-key",
    "secret_key": "your-secret-key",
    "passphrase": "your-passphrase",
    # 不配置 proxy 字段
}

# ============================================================================
# 使用示例
# ============================================================================

async def test_connection():
    """测试连接"""
    from src.connectors.okx_lite import OKXConnector

    # 选择一个配置（这里使用 Clash HTTP 代理）
    config = config_clash_http

    async with OKXConnector(config) as okx:
        # 测试连接
        if await okx.test_connection():
            print("✅ 连接 OKX 成功！")

            # 获取行情
            ticker = await okx.get_ticker("BTC-USDT")
            if ticker:
                print(f"BTC-USDT: {ticker['last']}")

        else:
            print("❌ 连接失败，请检查代理配置")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_connection())
