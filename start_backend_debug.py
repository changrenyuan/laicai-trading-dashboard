#!/usr/bin/env python3
"""
启动后端服务 - WebServer v2
带详细日志输出，用于调试
"""
import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

# 创建带时间戳的日志文件名
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f'backend_debug_{timestamp}.log'

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filename, encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

logger.info("="*80)
logger.info(f"🚀 启动后端服务 - WebServer v2")
logger.info(f"📝 日志文件: {log_filename}")
logger.info("="*80)


async def main():
    """启动 WebServer"""
    from src.ui.web_server import WebServer
    from src.core.position import PositionManager
    from src.core.risk_manager import RiskManager

    logger.info("="*60)
    logger.info("🚀 启动后端服务 - WebServer")
    logger.info("="*60)

    # 创建模拟机器人实例
    class MockBot:
        def __init__(self):
            self.is_running = False
            self.strategy = None
            self.position_manager = PositionManager()
            self.risk_manager = RiskManager({})
            # 创建事件总线
            from src.core.event_bus import EventBus
            self.event_bus = EventBus()
            # 创建策略管理器
            from src.core.strategy_manager import StrategyManager
            self.strategy_manager = None  # 可选，暂时为 None

    bot = MockBot()

    # 创建配置
    config = {
        "api_key": "test",
        "secret_key": "test",
        "passphrase": "test",
        "sandbox": True
    }

    # 创建 WebServer
    web_server = WebServer(config=config, bot_instance=bot)

    # 从环境变量读取配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))

    # WebServer 已经在初始化时订阅了事件总线
    # 这里不需要再订阅

    logger.info("="*60)
    logger.info("✅ WebServer 初始化完成")
    logger.info(f"📍 API 地址: http://localhost:{port}")
    logger.info(f"🔌 WebSocket 地址: ws://localhost:{port}/api/stream")
    logger.info("="*60)
    logger.info("")

    # 启动服务
    await web_server.run_async(host=host, port=port)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 服务已停止")
    except Exception as e:
        logger.error(f"❌ 服务启动失败: {e}", exc_info=True)
        sys.exit(1)
