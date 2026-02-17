"""
Hummingbot Lite - 量化交易机器人主程序（演示模式）
基于 Hummingbot 架构的简化版本

代理配置：
1. Clash 代理：config 中添加 "proxy": "clash" (HTTP) 或 "proxy": "clash-socks5"
2. HTTP 代理：config 中添加 "proxy": "http://127.0.0.1:7890"
3. SOCKS5 代理：config 中添加 "proxy": "socks5://127.0.0.1:7891" (需安装 aiohttp-socks)
4. 端口号：config 中添加 "proxy": "7890" (自动使用 HTTP 协议)

示例配置：
{
    "api_key": "xxx",
    "secret_key": "xxx",
    "passphrase": "xxx",
    "proxy": "clash"  # 或其他代理配置
}
"""
import asyncio
import yaml
import logging
import signal
import sys
from pathlib import Path
from colorlog import ColoredFormatter
from datetime import datetime, timedelta
import random

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.event_bus import EventBus
from src.core.position import PositionManager, PositionSide
from src.core.risk_manager import RiskManager
from src.strategies.market_maker import MarketMakerStrategy
from src.ui.web_server import WebServer

# 配置日志
def setup_logging(log_level: str = "INFO"):
    """设置日志"""
    handler = logging.StreamHandler()
    formatter = ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(handler)

    return logging.getLogger(__name__)


class MockExchange:
    """模拟交易所（演示模式）"""

    def __init__(self):
        self.orders = {}
        self.order_id_counter = 0
        self.current_price = 50000.0
        self.balances = {
            "USDT": 10000.0,
            "BTC": 0.5
        }

    def test_connection(self):
        return True

    async def get_balance(self):
        return {"USDT": {"total": self.balances["USDT"]},
                "BTC": {"total": self.balances["BTC"]}}

    async def get_ticker(self, symbol):
        # 模拟价格波动
        self.current_price += random.uniform(-50, 50)
        return {
            "symbol": symbol,
            "last": self.current_price,
            "bid": self.current_price * 0.9999,
            "ask": self.current_price * 1.0001,
            "high": self.current_price * 1.01,
            "low": self.current_price * 0.99,
            "volume": random.uniform(100, 1000),
            "timestamp": datetime.utcnow().timestamp() * 1000
        }

    async def get_order_book(self, symbol, limit=20):
        mid_price = self.current_price
        bids = [[mid_price * (1 - 0.0001 * i), random.uniform(0.001, 0.01)]
                for i in range(1, limit//2 + 1)]
        asks = [[mid_price * (1 + 0.0001 * i), random.uniform(0.001, 0.01)]
                for i in range(1, limit//2 + 1)]
        return {
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
            "timestamp": datetime.utcnow().timestamp() * 1000
        }

    async def create_order(self, symbol, side, size, price, order_type="limit"):
        self.order_id_counter += 1
        order_id = f"demo_{self.order_id_counter}"
        self.orders[order_id] = {
            "id": order_id,
            "symbol": symbol,
            "side": side,
            "size": size,
            "price": price,
            "status": "open",
            "filled": 0.0
        }

        # 模拟订单成交（30%概率）
        if random.random() < 0.3:
            await asyncio.sleep(random.uniform(0.5, 2.0))
            self.orders[order_id]["status"] = "filled"
            self.orders[order_id]["filled"] = size

            # 更新余额
            if side == "buy":
                self.balances["USDT"] -= size * price
                self.balances["BTC"] += size
            else:
                self.balances["BTC"] -= size
                self.balances["USDT"] += size * price

        return order_id

    async def cancel_order(self, order_id, symbol=None):
        if order_id in self.orders:
            self.orders[order_id]["status"] = "canceled"
            return True
        return False

    async def get_open_orders(self, symbol=None):
        return [order for order in self.orders.values()
                if order["status"] == "open"]

    async def get_order(self, order_id, symbol=None):
        return self.orders.get(order_id)

    async def cancel_all_orders(self, symbol=None):
        cancelled = 0
        for order in list(self.orders.values()):
            if order["status"] == "open":
                order["status"] = "canceled"
                cancelled += 1
        return cancelled

    async def close(self):
        pass

    def to_dict(self):
        return {
            "exchange": "demo_exchange",
            "sandbox": True,
            "orders_count": len(self.orders)
        }


class HummingbotLite:
    """Hummingbot Lite 主类"""

    def __init__(self, demo_mode=True):
        self.logger = logging.getLogger(__name__)
        self.demo_mode = demo_mode
        self.is_running = False

        # 初始化核心组件
        self.event_bus = EventBus()
        self.position_manager = PositionManager()
        self.risk_manager = RiskManager({
            'max_position_size': 0.1,
            'max_order_size': 0.01,
            'stop_loss_percentage': 0.02,
            'take_profit_percentage': 0.03,
            'max_daily_loss': 0.05
        })
        self.exchange = MockExchange() if demo_mode else None
        self.strategy = None
        self.web_server = None

        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """设置信号处理"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"收到信号 {signum}，正在关闭...")
        asyncio.create_task(self.stop())

    async def initialize(self):
        """初始化"""
        self.logger.info("=" * 50)
        self.logger.info("Hummingbot Lite 初始化中...")
        self.logger.info(f"模式: {'演示模式' if self.demo_mode else '实盘模式'}")
        self.logger.info("=" * 50)

        # 初始化策略
        self.logger.info("初始化策略...")
        self.strategy = MarketMakerStrategy(
            event_bus=self.event_bus,
            position_manager=self.position_manager,
            risk_manager=self.risk_manager,
            config={
                'trading_pair': 'BTC-USDT',
                'order_amount': 0.01,
                'bid_spread': 0.001,
                'ask_spread': 0.001,
                'order_refresh_time': 30
            }
        )

        # 设置策略回调
        self.strategy.set_callbacks(
            create_order=self._create_order_callback,
            cancel_order=self._cancel_order_callback,
            get_balance=self._get_balance_callback
        )

        # 订阅事件
        self._subscribe_events()

        # 初始化 Web 服务器
        self.logger.info("初始化 Web 服务器...")
        self.web_server = WebServer({
            'host': '0.0.0.0',
            'port': 5000,
            'log_level': 'INFO'
        }, self)

        self.logger.info("=" * 50)
        self.logger.info("初始化完成！")
        self.logger.info("=" * 50)

        return True

    def _subscribe_events(self):
        """订阅事件"""
        self.event_bus.subscribe("order_filled", lambda data: asyncio.create_task(
            self.web_server.broadcast_event("order_filled", data)
        ))
        self.event_bus.subscribe("strategy_start", lambda data: asyncio.create_task(
            self.web_server.broadcast_event("strategy_start", data)
        ))
        self.event_bus.subscribe("strategy_stop", lambda data: asyncio.create_task(
            self.web_server.broadcast_event("strategy_stop", data)
        ))

    async def _create_order_callback(self, symbol, side, size, price, order_type="limit"):
        """创建订单回调"""
        return await self.exchange.create_order(symbol, side, size, price, order_type)

    async def _cancel_order_callback(self, order_id):
        """取消订单回调"""
        return await self.exchange.cancel_order(order_id)

    async def _get_balance_callback(self):
        """获取余额回调"""
        return await self.exchange.get_balance()

    async def _market_data_loop(self):
        """市场数据循环"""
        self.logger.info("市场数据循环启动")
        trading_pair = "BTC-USDT"

        while self.is_running:
            try:
                # 获取行情
                ticker = await self.exchange.get_ticker(trading_pair)
                if ticker:
                    await self.strategy.on_tick(ticker)
                    await self.event_bus.publish("market_tick", ticker)

                # 获取订单簿
                orderbook = await self.exchange.get_order_book(trading_pair, limit=20)
                if orderbook:
                    await self.strategy.on_order_book(orderbook)
                    await self.event_bus.publish("market_order_book", orderbook)

                await asyncio.sleep(1)  # 每秒更新一次

            except Exception as e:
                self.logger.error(f"市场数据循环错误: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def run(self):
        """运行机器人"""
        if not await self.initialize():
            return

        self.is_running = True
        self.logger.info("Hummingbot Lite 启动成功！")
        self.logger.info("访问 http://localhost:5000 查看控制面板")

        # 启动市场数据循环
        market_data_task = asyncio.create_task(self._market_data_loop())

        # 运行 Web 服务器（异步版本）
        await self.web_server.run_async(
            host='0.0.0.0',
            port=5000
        )

        # 等待所有任务完成
        await market_data_task

    async def stop(self):
        """停止机器人"""
        if not self.is_running:
            return

        self.logger.info("正在停止 Hummingbot Lite...")

        self.is_running = False

        # 停止策略
        if self.strategy and self.strategy.is_running:
            await self.strategy.stop()

        # 关闭交易所连接
        await self.exchange.close()

        self.logger.info("Hummingbot Lite 已停止")


def main():
    """主函数"""
    # 设置日志
    logger = setup_logging(log_level="INFO")

    logger.info("""
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║     🚀 Hummingbot Lite - 量化交易机器人               ║
    ║                                                       ║
    ║     演示模式（无需 API 密钥）                         ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    # 创建并运行机器人
    bot = HummingbotLite(demo_mode=True)

    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    except Exception as e:
        logger.error(f"发生错误: {e}", exc_info=True)
    finally:
        logger.info("程序退出")


if __name__ == "__main__":
    main()
