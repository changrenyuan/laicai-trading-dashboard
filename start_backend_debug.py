#!/usr/bin/env python3
"""
启动后端服务 - WebServer v2
带详细日志输出，用于调试
"""
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('backend_debug.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """启动 WebServer v2"""
    from src.ui.web_v2 import WebServerV2
    from src.core.position import PositionManager
    from src.core.risk_manager import RiskManager

    logger.info("="*60)
    logger.info("🚀 启动后端服务 - WebServer v2")
    logger.info("="*60)

    # 创建模拟机器人实例
    class MockBot:
        def __init__(self):
            self.is_running = False
            self.strategy = None
            self.position_manager = PositionManager()
            self.risk_manager = RiskManager({})

    bot = MockBot()

    # 创建配置
    config = {
        "api_key": "test",
        "secret_key": "test",
        "passphrase": "test",
        "sandbox": True
    }

    # 创建 WebServer
    web_server = WebServerV2(config=config, bot_instance=bot)

    # 订阅 EventBus 事件，用于调试
    def event_debug_handler(event):
        logger.info(f"📤 Event Published: type={event.get('type')}, timestamp={event.get('timestamp')}")
        logger.info(f"   Data: {event}")

    web_server.event_bus.subscribe("price", event_debug_handler)
    web_server.event_bus.subscribe("order_update", event_debug_handler)
    web_server.event_bus.subscribe("position", event_debug_handler)
    web_server.event_bus.subscribe("strategy", event_debug_handler)
    web_server.event_bus.subscribe("log", event_debug_handler)
    web_server.event_bus.subscribe("error", event_debug_handler)
    web_server.event_bus.subscribe("snapshot", event_debug_handler)

    logger.info("="*60)
    logger.info("✅ WebServer v2 初始化完成")
    logger.info("📍 API 地址: http://localhost:5000")
    logger.info("🔌 WebSocket 地址: ws://localhost:5000/ws")
    logger.info("="*60)
    logger.info("")

    # 启动服务
    await web_server.run_async(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 服务已停止")
    except Exception as e:
        logger.error(f"❌ 服务启动失败: {e}", exc_info=True)
        sys.exit(1)
