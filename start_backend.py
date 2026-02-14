#!/usr/bin/env python3
"""
快速启动后端服务器用于测试
"""
import asyncio
import logging
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.event_bus import EventBus
from src.core.position import PositionManager
from src.core.risk_manager import RiskManager
from src.core.strategy_manager import StrategyManager
from src.core.websocket_log_handler import setup_websocket_logging
from src.ui.web_multi_strategy import WebServer


async def main():
    """主函数"""
    print("="*60)
    print("启动 Hummingbot Web API 服务器")
    print("="*60)

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # 创建核心组件
    event_bus = EventBus()
    position_manager = PositionManager()
    risk_config = {
        "max_daily_loss": 0.05,
        "max_position_size": 0.1,
        "max_order_size": 0.01
    }
    risk_manager = RiskManager(risk_config)

    # 设置日志处理器
    ws_log_handler = setup_websocket_logging("INFO")

    # 创建模拟 Bot 实例
    class MockBot:
        def __init__(self):
            self.is_running = True
            self.event_bus = event_bus
            self.position_manager = position_manager
            self.risk_manager = risk_manager
            self.strategy_manager = StrategyManager(event_bus, position_manager, risk_manager)
            self.exchange = MockExchange()
            self.strategy = None

    class MockExchange:
        def __init__(self):
            self.exchange_name = "okx"

        def to_dict(self):
            return {
                "exchange_name": self.exchange_name,
                "connected": True
            }

        async def get_balance(self):
            return {
                "USDT": {"total": 10000.0, "available": 9500.0, "frozen": 500.0},
                "BTC": {"total": 0.1, "available": 0.08, "frozen": 0.02},
                "ETH": {"total": 2.0, "available": 1.8, "frozen": 0.2}
            }

        async def get_open_orders(self, symbol=None):
            return []

        async def cancel_all_orders(self, symbol=None):
            return 0

        async def get_order_book(self, symbol, limit=20):
            import random
            from datetime import datetime

            base_price = 50000.0 if 'BTC' in symbol else (3000.0 if 'ETH' in symbol else 150.0)

            bids = []
            asks = []

            for i in range(limit):
                bid_price = base_price - (i + 1) * (base_price * 0.0001)
                ask_price = base_price + (i + 1) * (base_price * 0.0001)
                bid_amount = random.uniform(0.001, 1.0)
                ask_amount = random.uniform(0.001, 1.0)

                bids.append([bid_price, bid_amount])
                asks.append([ask_price, ask_amount])

            return {
                "symbol": symbol,
                "bids": bids,
                "asks": asks,
                "timestamp": datetime.now().timestamp()
            }

        async def get_ticker(self, symbol):
            import random
            from datetime import datetime

            base_price = 50000.0 if 'BTC' in symbol else (3000.0 if 'ETH' in symbol else 150.0)
            price_change = random.uniform(-500, 500)

            return {
                "symbol": symbol,
                "last_price": round(base_price + price_change, 2),
                "best_bid": round(base_price + price_change - 1, 2),
                "best_ask": round(base_price + price_change + 1, 2),
                "bid_qty": random.uniform(0.1, 2.0),
                "ask_qty": random.uniform(0.1, 2.0),
                "price_change_24h": round(price_change, 2),
                "price_change_pct_24h": round(price_change / base_price * 100, 2),
                "volume_24h": random.uniform(1000, 5000),
                "high_24h": round(base_price + 1000, 2),
                "low_24h": round(base_price - 1000, 2),
                "timestamp": datetime.now().timestamp()
            }

        async def get_klines(self, symbol, interval, limit):
            import random

            base_price = 50000.0 if 'BTC' in symbol else (3000.0 if 'ETH' in symbol else 150.0)
            klines = []

            # 间隔映射（秒）
            interval_map = {
                "1m": 60,
                "5m": 300,
                "15m": 900,
                "30m": 1800,
                "1h": 3600,
                "4h": 14400,
                "1d": 86400,
                "1w": 604800
            }

            interval_seconds = interval_map.get(interval, 3600)
            now = datetime.now().timestamp()

            for i in range(limit):
                timestamp = now - (limit - i) * interval_seconds
                price = base_price + random.uniform(-500, 500)
                klines.append({
                    "timestamp": int(timestamp),
                    "open": round(price + random.uniform(-10, 10), 2),
                    "high": round(price + random.uniform(0, 20), 2),
                    "low": round(price - random.uniform(0, 20), 2),
                    "close": round(price + random.uniform(-10, 10), 2),
                    "volume": round(random.uniform(10, 100), 2)
                })

            return klines

    # 创建 Bot 实例
    bot = MockBot()

    # 创建 Web 服务器
    web_server = WebServer(
        config={},
        bot_instance=bot,
        ws_log_handler=ws_log_handler
    )

    logger.info("Web 服务器已创建")
    logger.info("API 端点:")
    logger.info("  - GET  /api/status           - 获取系统状态")
    logger.info("  - GET  /api/equity           - 获取账户权益")
    logger.info("  - GET  /api/balance          - 获取账户余额")
    logger.info("  - GET  /api/positions        - 获取所有仓位")
    logger.info("  - GET  /api/orders/active    - 获取活跃订单")
    logger.info("  - GET  /api/trades/history   - 获取成交历史")
    logger.info("  - GET  /api/orderbook/{sym}  - 获取订单簿")
    logger.info("  - GET  /api/ticker/{sym}     - 获取 Ticker")
    logger.info("  - GET  /api/klines           - 获取 K 线数据")
    logger.info("  - GET  /api/pnl/history      - 获取 PnL 历史")
    logger.info("  - GET  /api/strategies       - 获取可用策略列表")
    logger.info("  - GET  /api/strategy-instances - 获取策略实例")
    logger.info("  - POST /api/strategy-instances - 创建策略实例")
    logger.info("  - POST /api/backtest/run     - 运行回测")
    logger.info("  - GET  /api/stats/realtime   - 获取实时统计数据")
    logger.info("  - POST /api/kill-switch      - 紧急停止")
    logger.info("")
    logger.info("WebSocket:")
    logger.info("  - WS   /ws/logs              - 实时日志推送")
    logger.info("")
    logger.info("服务器地址: http://localhost:5000")
    logger.info("API 文档:  http://localhost:5000/docs")

    # 启动服务器
    print("\n" + "="*60)
    print("服务器正在启动...")
    print("="*60 + "\n")

    await web_server.run_async(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
    except Exception as e:
        print(f"\n\n服务器启动失败: {e}")
        import traceback
        traceback.print_exc()
