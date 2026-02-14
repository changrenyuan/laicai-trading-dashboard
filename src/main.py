"""
Hummingbot Lite - 量化交易机器人主程序
基于 Hummingbot 架构的简化版本
"""
import asyncio
import yaml
import logging
import signal
import sys
from pathlib import Path
from colorlog import ColoredFormatter

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.event_bus import EventBus
from src.core.position import PositionManager
from src.core.risk_manager import RiskManager
from src.connectors.okx import OKXConnector
from src.strategies.market_maker import MarketMakerStrategy
from src.ui.web import WebServer

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


class HummingbotLite:
    """Hummingbot Lite 主类"""

    def __init__(self, config_path: str = "config.yaml"):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)

        # 初始化核心组件
        self.event_bus = EventBus()
        self.position_manager = PositionManager()
        self.risk_manager = RiskManager(self.config.get('risk_management', {}))
        self.exchange = OKXConnector(self.config.get('exchange', {}))
        self.strategy = None
        self.web_server = None

        self.is_running = False
        self._setup_signal_handlers()

    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            raise

    def _setup_signal_handlers(self):
        """设置信号处理"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(self.stop())

    async def initialize(self):
        """初始化"""
        self.logger.info("=" * 50)
        self.logger.info("Hummingbot Lite 初始化中...")
        self.logger.info("=" * 50)

        # 测试交易所连接
        self.logger.info("测试交易所连接...")
        connected = await self.exchange.test_connection()
        if not connected:
            self.logger.error("交易所连接失败！请检查配置。")
            return False

        self.logger.info("交易所连接成功！")

        # 初始化策略
        self.logger.info("初始化策略...")
        self.strategy = MarketMakerStrategy(
            event_bus=self.event_bus,
            position_manager=self.position_manager,
            risk_manager=self.risk_manager,
            config=self.config.get('strategy', {})
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
        self.web_server = WebServer(self.config.get('server', {}), self)

        self.logger.info("=" * 50)
        self.logger.info("初始化完成！")
        self.logger.info("=" * 50)

        return True

    def _subscribe_events(self):
        """订阅事件"""
        # 将重要事件广播到 WebSocket 客户端
        self.event_bus.subscribe("order_filled", lambda data: asyncio.create_task(
            self.web_server.broadcast_event("order_filled", data)
        ))
        self.event_bus.subscribe("strategy_start", lambda data: asyncio.create_task(
            self.web_server.broadcast_event("strategy_start", data)
        ))
        self.event_bus.subscribe("strategy_stop", lambda data: asyncio.create_task(
            self.web_server.broadcast_event("strategy_stop", data)
        ))
        self.event_bus.subscribe("risk_limit_breach", lambda data: asyncio.create_task(
            self.web_server.broadcast_event("risk_limit_breach", data)
        ))

    async def _create_order_callback(self, symbol: str, side: str, size: float,
                                     price: float, order_type: str = "limit") -> str:
        """创建订单回调"""
        return await self.exchange.create_order(symbol, side, size, price, order_type)

    async def _cancel_order_callback(self, order_id: str) -> bool:
        """取消订单回调"""
        return await self.exchange.cancel_order(order_id)

    async def _get_balance_callback(self) -> dict:
        """获取余额回调"""
        return await self.exchange.get_balance()

    async def _market_data_loop(self):
        """市场数据循环"""
        self.logger.info("市场数据循环启动")
        trading_pair = self.config.get('strategy', {}).get('trading_pair', 'BTC-USDT')

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
                self.logger.error(f"Error in market data loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def run(self):
        """运行机器人"""
        if not await self.initialize():
            return

        self.is_running = True
        self.logger.info("Hummingbot Lite 启动成功！")

        # 启动市场数据循环
        market_data_task = asyncio.create_task(self._market_data_loop())

        # 启动 Web 服务器
        self.logger.info("Web 服务器启动中...")
        self.logger.info("访问 http://localhost:5000 查看控制面板")

        # 运行 Web 服务器（阻塞）
        self.web_server.run(
            host=self.config.get('server', {}).get('host', '0.0.0.0'),
            port=self.config.get('server', {}).get('port', 5000)
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
    ║     基于 Hummingbot 架构的简化版本                     ║
    ║     支持 OKX 交易所实盘交易                            ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    # 检查配置文件
    config_path = Path(__file__).parent.parent / "config.yaml"
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_path}")
        logger.info("请复制 config.yaml 并填写您的 OKX API 密钥")
        sys.exit(1)

    # 创建并运行机器人
    bot = HummingbotLite(str(config_path))

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
