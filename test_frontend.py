#!/usr/bin/env python3
"""
前端功能测试脚本
模拟前端调用后端API，验证数据流和功能完整性
"""
import requests
import json
from typing import Dict, Any

# 基础URL（通过Vite proxy）
BASE_URL = "http://localhost:5173/api"

def test_api_endpoint(endpoint: str, description: str) -> bool:
    """测试单个API端点"""
    try:
        url = f"{BASE_URL}{endpoint}"
        print(f"\n{'='*60}")
        print(f"测试: {description}")
        print(f"URL: {url}")
        print('='*60)

        response = requests.get(url, timeout=5)
        response.raise_for_status()

        data = response.json()
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ 失败: {e}")
        return False

def test_market_data_api(symbol: str) -> bool:
    """测试市场数据API"""
    try:
        # 测试订单簿
        orderbook_url = f"{BASE_URL}/orderbook/{symbol}"
        print(f"\n{'='*60}")
        print(f"测试: 获取订单簿 ({symbol})")
        print(f"URL: {orderbook_url}")
        print('='*60)

        response = requests.get(orderbook_url, params={'limit': 5}, timeout=5)
        response.raise_for_status()
        data = response.json()
        print(f"✅ 订单簿数据: {json.dumps(data, indent=2, ensure_ascii=False)}")

        # 测试Ticker
        ticker_url = f"{BASE_URL}/ticker/{symbol}"
        print(f"\n测试: 获取 Ticker ({symbol})")
        print(f"URL: {ticker_url}")

        response = requests.get(ticker_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        print(f"✅ Ticker 数据: {json.dumps(data, indent=2, ensure_ascii=False)}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ 失败: {e}")
        return False

def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("Hummingbot Web UI - 前后端联调测试")
    print("="*60)

    results = []

    # 测试系统API
    results.append(("系统状态", test_api_endpoint("/status", "系统状态")))
    results.append(("账户权益", test_api_endpoint("/equity", "账户权益")))
    results.append(("账户余额", test_api_endpoint("/balance", "账户余额")))
    results.append(("仓位列表", test_api_endpoint("/positions", "仓位列表")))
    results.append(("活跃订单", test_api_endpoint("/orders/active", "活跃订单")))
    results.append(("成交历史", test_api_endpoint("/trades/history", "成交历史")))
    results.append(("PnL历史", test_api_endpoint("/pnl/history", "PnL历史")))
    results.append(("可用策略", test_api_endpoint("/strategies", "可用策略")))
    results.append(("策略实例", test_api_endpoint("/strategy-instances", "策略实例")))
    results.append(("实时统计", test_api_endpoint("/stats/realtime", "实时统计")))

    # 测试市场数据API
    results.append(("市场数据", test_market_data_api("BTC-USDT")))

    # 打印测试结果汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name:20s} {status}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过！前后端联调成功！")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
