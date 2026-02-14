"""
测试 OKX 连接器（基于 Hummingbot 代码）
"""
import asyncio
from src.connectors.okx_lite import OKXConnector


async def test_okx_connector():
    """测试 OKX 连接器"""

    # 测试配置（使用沙盒环境）
    config = {
        'api_key': 'test_key',
        'secret_key': 'test_secret',
        'passphrase': 'test_pass',
        'registration_sub_domain': 'www',
        'sandbox': True
    }

    async with OKXConnector(config) as connector:
        print("1. 测试连接...")
        connected = await connector.test_connection()
        print(f"连接测试: {'成功' if connected else '失败'}")

        if connected:
            print("\n2. 获取行情...")
            ticker = await connector.get_ticker('BTC-USDT')
            if ticker:
                print(f"BTC-USDT 行情:")
                print(f"  最新价: {ticker['last']}")
                print(f"  买一价: {ticker['bid']}")
                print(f"  卖一价: {ticker['ask']}")

            print("\n3. 获取订单簿...")
            orderbook = await connector.get_order_book('BTC-USDT', limit=5)
            if orderbook:
                print(f"BTC-USDT 订单簿:")
                print(f"  买一: {orderbook['bids'][0]}")
                print(f"  卖一: {orderbook['asks'][0]}")

        print(f"\n连接器状态: {connector.to_dict()}")


if __name__ == "__main__":
    asyncio.run(test_okx_connector())
