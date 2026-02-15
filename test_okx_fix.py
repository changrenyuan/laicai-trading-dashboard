#!/usr/bin/env python3
"""
测试 OKX 连接器修复后的功能
"""
import asyncio
import os
from dotenv import load_dotenv
from src.connectors.okx_lite.connector import OKXConnector

async def run_tests(connector: OKXConnector):
    """运行测试"""
    # 测试获取行情（公开 API，不需要认证）
    print("📊 测试获取行情（公开 API）...")
    ticker = await connector.get_ticker("BTC-USDT")
    if ticker:
        print(f"✅ BTC-USDT 行情: {ticker}")
    else:
        print("❌ 获取行情失败")
    print()

    # 测试获取订单簿（公开 API）
    print("📚 测试获取订单簿（公开 API）...")
    orderbook = await connector.get_order_book("BTC-USDT", limit=5)
    if orderbook:
        print(f"✅ BTC-USDT 订单簿:")
        print(f"   买一: {orderbook['bids'][0] if orderbook['bids'] else 'N/A'}")
        print(f"   卖一: {orderbook['asks'][0] if orderbook['asks'] else 'N/A'}")
    else:
        print("❌ 获取订单簿失败")
    print()

    # 测试获取交易账户余额（需要认证）
    print("💰 测试获取交易账户余额（需要认证）...")
    trading_balance = await connector.get_balance()
    if trading_balance:
        print(f"✅ 交易账户余额: {trading_balance}")
    else:
        print("❌ 获取交易账户余额失败")
    print()

    # 测试获取资产余额（需要认证）
    print("💳 测试获取资产余额（需要认证）...")
    asset_balance = await connector.get_asset_balance()
    if asset_balance:
        print(f"✅ 资产余额: {asset_balance}")
    else:
        print("❌ 获取资产余额失败")
    print()

    # 如果有 USDT 余额，可以测试创建订单（仅演示，不实际执行）
    usdt_balance = trading_balance.get('USDT', {}).get('available', 0)
    if usdt_balance > 10:
        print(f"💰 当前 USDT 可用余额: {usdt_balance}")
        print("⚠️  演示订单创建（实际不执行）:")
        print("   - 币对: BTC-USDT")
        print("   - 方向: 买入")
        print("   - 类型: 限价单")
        print("   - 数量: 0.001 BTC")
        print("   - 价格: 当前买价 - 5%")
        # 实际取消注释以下代码来测试订单创建
        # bid_price = ticker['bid'] * Decimal('0.95')
        # order_id = await connector.create_order(
        #     symbol="BTC-USDT",
        #     side="buy",
        #     size=0.001,
        #     price=float(bid_price),
        #     order_type="limit"
        # )
        # if order_id:
        #     print(f"✅ 订单创建成功: {order_id}")
        #     # 取消订单
        #     success = await connector.cancel_order(order_id)
        #     print(f"✅ 订单取消成功: {success}")
        # else:
        #     print("❌ 订单创建失败")
    else:
        print(f"💰 当前 USDT 可用余额: {usdt_balance}")
        print("⚠️  余额不足，跳过订单测试")
    print()

    print(f"{'='*60}")
    print("🎉 测试完成")
    print(f"{'='*60}")

async def test_okx_connector():
    """测试 OKX 连接器"""
    load_dotenv()

    # 从环境变量读取配置
    api_key = os.getenv("OKX_API_KEY")
    secret_key = os.getenv("OKX_SECRET_KEY")
    passphrase = os.getenv("OKX_PASSPHRASE")
    sandbox = os.getenv("OKX_SANDBOX", "false").lower() == "true"

    print(f"\n{'='*60}")
    print(f"🧪 OKX 连接器测试")
    print(f"{'='*60}")
    print(f"环境: {'模拟盘' if sandbox else '实盘'}")
    print(f"{'='*60}\n")

    if not all([api_key, secret_key, passphrase]):
        print("❌ 缺少环境变量: OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE")
        return

    connector = OKXConnector({
        'api_key': api_key,
        'secret_key': secret_key,
        'passphrase': passphrase,
        'sandbox': sandbox
    })

    try:
        print("🔗 初始化 OKX 连接器...")
        async with connector:
            print("✅ 连接器初始化成功\n")
            await run_tests(connector)
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_okx_connector())
