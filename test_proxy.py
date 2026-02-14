"""
测试 OKX 代理连接
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.connectors.okx_lite import OKXConnector
from src.connectors.okx_lite.proxy_manager import ProxyManager


async def test_proxy_connection():
    """测试代理连接"""

    print("=" * 60)
    print("OKX 代理连接测试")
    print("=" * 60)

    # 配置选项
    print("\n请选择代理配置:")
    print("1. Clash HTTP 代理 (127.0.0.1:7890)")
    print("2. Clash SOCKS5 代理 (127.0.0.1:7891)")
    print("3. HTTP 代理 (自定义)")
    print("4. 无代理 (直接连接)")
    print("5. 演示模式 (无需 API 密钥)")

    choice = input("\n请输入选项 (1-5): ").strip()

    config = {
        "api_key": input("\n请输入 OKX API Key (可选，演示模式留空): ").strip(),
        "secret_key": input("请输入 OKX Secret Key (可选，演示模式留空): ").strip(),
        "passphrase": input("请输入 OKX Passphrase (可选，演示模式留空): ").strip(),
    }

    # 根据选择配置代理
    if choice == "1":
        config["proxy"] = "clash"
        print("\n✓ 使用 Clash HTTP 代理")
    elif choice == "2":
        config["proxy"] = "clash-socks5"
        print("\n✓ 使用 Clash SOCKS5 代理")
    elif choice == "3":
        proxy_url = input("请输入 HTTP 代理 URL (例如: http://127.0.0.1:7890): ").strip()
        config["proxy"] = proxy_url
        print(f"\n✓ 使用 HTTP 代理: {proxy_url}")
    elif choice == "4":
        print("\n✓ 不使用代理 (直接连接)")
    elif choice == "5":
        print("\n✓ 演示模式 (无需 API 密钥)")
        # 演示模式使用模拟交易所
        from src.main_demo import MockExchange
        exchange = MockExchange()
        print("\n" + "=" * 60)
        print("演示模式测试")
        print("=" * 60)

        ticker = await exchange.get_ticker("BTC-USDT")
        if ticker:
            print(f"\n✅ 模拟行情获取成功:")
            print(f"   BTC-USDT: {ticker['last']}")
            print(f"   买一价: {ticker['bid']}")
            print(f"   卖一价: {ticker['ask']}")

        orderbook = await exchange.get_order_book("BTC-USDT", limit=5)
        if orderbook:
            print(f"\n✅ 模拟订单簿获取成功:")
            print(f"   买盘前5档: {orderbook['bids'][:3]}")
            print(f"   卖盘前5档: {orderbook['asks'][:3]}")

        print("\n" + "=" * 60)
        print("演示模式测试完成！")
        print("=" * 60)
        return
    else:
        print("\n❌ 无效选项")
        return

    # 检查 API 密钥
    if not config["api_key"] or not config["secret_key"] or not config["passphrase"]:
        print("\n⚠️  警告: 缺少 API 密钥")
        print("请提供完整的 API Key、Secret Key 和 Passphrase")
        print("或选择演示模式 (选项5) 进行测试")
        return

    # 测试连接
    print("\n" + "=" * 60)
    print("开始测试...")
    print("=" * 60)

    try:
        async with OKXConnector(config) as okx:
            print("\n1. 测试连接...")
            if await okx.test_connection():
                print("   ✅ 连接成功！")

                print("\n2. 获取行情...")
                ticker = await okx.get_ticker("BTC-USDT")
                if ticker:
                    print(f"   ✅ 行情获取成功:")
                    print(f"      BTC-USDT: {ticker['last']}")
                    print(f"      买一价: {ticker['bid']}")
                    print(f"      卖一价: {ticker['ask']}")
                    print(f"      24h最高: {ticker['high']}")
                    print(f"      24h最低: {ticker['low']}")
                else:
                    print("   ❌ 行情获取失败")

                print("\n3. 获取订单簿...")
                orderbook = await okx.get_order_book("BTC-USDT", limit=5)
                if orderbook:
                    print(f"   ✅ 订单簿获取成功:")
                    print(f"      买盘前3档: {orderbook['bids'][:3]}")
                    print(f"      卖盘前3档: {orderbook['asks'][:3]}")
                else:
                    print("   ❌ 订单簿获取失败")

                print("\n4. 获取余额...")
                balance = await okx.get_balance()
                if balance:
                    print(f"   ✅ 余额获取成功:")
                    for ccy, bal in balance.items():
                        print(f"      {ccy}: {bal['available']} / {bal['total']}")
                else:
                    print("   ❌ 余额获取失败")

                print("\n" + "=" * 60)
                print("测试完成！代理配置正常工作！")
                print("=" * 60)

            else:
                print("   ❌ 连接失败")
                print("\n可能的原因:")
                print("   - 代理未启动或配置错误")
                print("   - API 密钥无效或权限不足")
                print("   - 网络连接问题")

    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


async def test_proxy_availability():
    """测试代理是否可用"""
    print("\n" + "=" * 60)
    print("测试代理可用性")
    print("=" * 60)

    # 测试 Clash HTTP 代理
    print("\n测试 Clash HTTP 代理 (http://127.0.0.1:7890)...")
    if ProxyManager.check_proxy("http://127.0.0.1:7890"):
        print("✅ Clash HTTP 代理可用")
    else:
        print("❌ Clash HTTP 代理不可用")

    # 测试 Clash SOCKS5 代理
    print("\n测试 Clash SOCKS5 代理 (socks5://127.0.0.1:7891)...")
    try:
        if ProxyManager.check_proxy("socks5://127.0.0.1:7891"):
            print("✅ Clash SOCKS5 代理可用")
        else:
            print("❌ Clash SOCKS5 代理不可用")
    except Exception as e:
        print(f"❌ SOCKS5 测试失败 (可能需要安装 aiohttp-socks): {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="测试 OKX 代理连接")
    parser.add_argument("--check-proxy", action="store_true", help="仅测试代理可用性")
    args = parser.parse_args()

    if args.check_proxy:
        asyncio.run(test_proxy_availability())
    else:
        asyncio.run(test_proxy_connection())
