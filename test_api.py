#!/usr/bin/env python3
"""
API 测试脚本
测试所有后端 API 端点
"""
import asyncio
import aiohttp
import json
from datetime import datetime


class APITester:
    """API 测试类"""

    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = None
        self.test_results = []

    async def init(self):
        """初始化会话"""
        self.session = aiohttp.ClientSession()

    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()

    async def test_get(self, endpoint, description):
        """测试 GET 请求"""
        url = f"{self.base_url}{endpoint}"
        print(f"\n{'='*60}")
        print(f"测试: {description}")
        print(f"端点: {endpoint}")
        print(f"{'='*60}")

        try:
            async with self.session.get(url) as response:
                status = response.status
                data = await response.json()

                print(f"状态码: {status}")
                print(f"响应:")
                print(json.dumps(data, indent=2, ensure_ascii=False))

                self.test_results.append({
                    "endpoint": endpoint,
                    "description": description,
                    "method": "GET",
                    "status": status,
                    "success": status == 200
                })

                return data
        except Exception as e:
            print(f"错误: {e}")
            self.test_results.append({
                "endpoint": endpoint,
                "description": description,
                "method": "GET",
                "status": 0,
                "success": False,
                "error": str(e)
            })
            return None

    async def test_post(self, endpoint, data, description):
        """测试 POST 请求"""
        url = f"{self.base_url}{endpoint}"
        print(f"\n{'='*60}")
        print(f"测试: {description}")
        print(f"端点: {endpoint}")
        print(f"请求体:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"{'='*60}")

        try:
            async with self.session.post(url, json=data) as response:
                status = response.status
                response_data = await response.json()

                print(f"状态码: {status}")
                print(f"响应:")
                print(json.dumps(response_data, indent=2, ensure_ascii=False))

                self.test_results.append({
                    "endpoint": endpoint,
                    "description": description,
                    "method": "POST",
                    "status": status,
                    "success": status == 200
                })

                return response_data
        except Exception as e:
            print(f"错误: {e}")
            self.test_results.append({
                "endpoint": endpoint,
                "description": description,
                "method": "POST",
                "status": 0,
                "success": False,
                "error": str(e)
            })
            return None

    async def run_all_tests(self):
        """运行所有测试"""
        print(f"\n{'#'*60}")
        print(f"开始 API 测试")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*60}")

        # ==================== 基础接口 ====================

        await self.test_get("/api/status", "获取系统状态")

        # ==================== 账户相关 API ====================

        await self.test_get("/api/equity", "获取账户权益")
        await self.test_get("/api/balance", "获取账户余额")

        # ==================== 仓位相关 API ====================

        await self.test_get("/api/positions", "获取所有仓位")
        await self.test_get("/api/positions/BTC-USDT", "获取 BTC-USDT 仓位")

        # ==================== 订单相关 API ====================

        await self.test_get("/api/orders/active", "获取活跃订单")
        await self.test_get("/api/trades/history", "获取成交历史")
        await self.test_get("/api/trades/history?limit=5", "获取成交历史（限制 5 条）")
        await self.test_get("/api/trades/history?symbol=BTC-USDT", "获取 BTC-USDT 成交历史")

        # ==================== 市场数据 API ====================

        await self.test_get("/api/orderbook/BTC-USDT", "获取 BTC-USDT 订单簿")
        await self.test_get("/api/orderbook/BTC-USDT?limit=10", "获取 BTC-USDT 订单簿（限制 10 条）")
        await self.test_get("/api/ticker/BTC-USDT", "获取 BTC-USDT Ticker")
        await self.test_get("/api/klines?symbol=BTC-USDT&interval=1h&limit=10", "获取 BTC-USDT K 线数据")

        # ==================== PnL 相关 API ====================

        await self.test_get("/api/pnl/history", "获取 PnL 历史")
        await self.test_get("/api/pnl/history?limit=10", "获取 PnL 历史（限制 10 条）")

        # ==================== 策略相关 API ====================

        await self.test_get("/api/strategies", "获取可用策略列表")
        await self.test_get("/api/strategy-instances", "获取策略实例列表")

        # 创建策略实例
        await self.test_post(
            "/api/strategy-instances",
            {
                "strategy_name": "market_maker",
                "instance_name": "test_strategy",
                "config": {
                    "symbol": "BTC-USDT",
                    "exchange": "okx",
                    "order_amount": 0.001,
                    "spread": 0.001
                }
            },
            "创建策略实例"
        )

        # ==================== 回测相关 API ====================

        await self.test_post(
            "/api/backtest/run",
            {
                "strategy": "market_maker",
                "config": {
                    "symbol": "BTC-USDT",
                    "order_amount": 0.001
                },
                "start_time": int((datetime.now().timestamp() - 86400 * 7)),
                "end_time": int(datetime.now().timestamp())
            },
            "运行回测"
        )

        # ==================== 系统管理 API ====================

        await self.test_get("/api/stats/realtime", "获取实时统计数据")

        # ==================== 总结 ====================

        self.print_summary()

    def print_summary(self):
        """打印测试总结"""
        print(f"\n{'#'*60}")
        print(f"测试总结")
        print(f"{'#'*60}")

        total = len(self.test_results)
        success = sum(1 for r in self.test_results if r["success"])
        failed = total - success

        print(f"总测试数: {total}")
        print(f"成功: {success}")
        print(f"失败: {failed}")
        print(f"成功率: {(success/total*100):.2f}%")

        if failed > 0:
            print(f"\n失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['description']} ({result['endpoint']})")


async def main():
    """主函数"""
    tester = APITester(base_url="http://localhost:5000")
    await tester.init()
    await tester.run_all_tests()
    await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
