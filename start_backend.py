#!/usr/bin/env python3
"""
启动后端服务器 - 使用真实交易所（从 .env 读取配置）
"""
import asyncio
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.event_bus import EventBus
from src.core.position import PositionManager
from src.core.risk_manager import RiskManager
from src.core.strategy_manager import StrategyManager
from src.core.websocket_log_handler import setup_websocket_logging
from src.ui.web_multi_strategy import WebServer
from src.connectors.okx_lite import OKXConnector


# 加载 .env 文件
load_dotenv()


async def main():
    """主函数"""
    print("="*60)
    print("启动 Hummingbot Web API 服务器（真实交易所模式）")
    print("="*60)

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # 从环境变量读取配置
    api_key = os.getenv('OKX_API_KEY')
    secret_key = os.getenv('OKX_SECRET_KEY')
    passphrase = os.getenv('OKX_PASSPHRASE')

    # 验证 API 密钥
    if not api_key or not secret_key or not passphrase:
        print("❌ 错误: 请在 .env 文件中配置 OKX API 密钥")
        print("配置步骤:")
        print("  1. 复制 .env.example 为 .env")
        print("  2. 填入你的 OKX API 密钥")
        print("  3. 重新启动服务")
        sys.exit(1)

    # 创建核心组件
    event_bus = EventBus()
    position_manager = PositionManager()
    risk_config = {
        'max_daily_loss': float(os.getenv('MAX_DAILY_LOSS', 0.05)),
        'max_position_size': float(os.getenv('MAX_POSITION_SIZE', 0.1)),
        'max_order_size': float(os.getenv('MAX_ORDER_SIZE', 0.01))
    }
    risk_manager = RiskManager(risk_config)
    strategy_manager = StrategyManager(event_bus, position_manager, risk_manager)

    # 设置日志处理器
    ws_log_handler = setup_websocket_logging("INFO")

    # 创建真实交易所连接
    exchange_config = {
        'api_key': api_key,
        'secret_key': secret_key,
        'passphrase': passphrase,
        'registration_sub_domain': os.getenv('OKX_SUB_DOMAIN', 'www'),
        'sandbox': os.getenv('OKX_SANDBOX', 'false').lower() == 'true',
    }

    # 添加代理配置
    proxy_url = None
    if os.getenv('PROXY_ENABLED', 'false').lower() == 'true':
        # 优先使用标准环境变量
        proxy_url = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')
        if proxy_url:
            print(f"✅ 使用代理（从环境变量）: {proxy_url}")
            exchange_config['proxy'] = proxy_url
        else:
            # 回退到自定义配置
            proxy_type = os.getenv('PROXY_TYPE', 'http')
            proxy_host = os.getenv('PROXY_HOST', '127.0.0.1')
            proxy_port = os.getenv('PROXY_PORT', '7890')

            if proxy_type == 'socks5':
                exchange_config['proxy'] = f'socks5://{proxy_host}:{proxy_port}'
            elif proxy_type == 'http':
                exchange_config['proxy'] = f'http://{proxy_host}:{proxy_port}'
            else:
                print(f"⚠️  警告: 不支持的代理类型 {proxy_type}，将不使用代理")
            print(f"✅ 使用代理（自定义配置）: {exchange_config.get('proxy', '无')}")
    else:
        print(f"⚠️  代理未启用 (PROXY_ENABLED=false)")

    # 创建真实交易所实例
    print(f"🔗 正在连接 OKX 交易所...")
    print(f"   模式: {'沙盒' if exchange_config['sandbox'] else '实盘'}")
    print(f"   子域名: {exchange_config['registration_sub_domain']}")
    if 'proxy' in exchange_config:
        print(f"   代理: {exchange_config['proxy']}")

    try:
        okx_connector = OKXConnector(exchange_config)
        await okx_connector.__aenter__()

        # 测试连接
        balance = await okx_connector.get_balance()
        print(f"✅ 成功连接到 OKX 交易所")
        print(f"💰 账户余额: {balance}")
    except Exception as e:
        print(f"⚠️  连接 OKX 交易所失败，服务将以离线模式启动")
        print(f"错误信息: {e}")
        print(f"请检查:")
        print(f"  1. .env 文件中的 API 密钥是否正确")
        print(f"  2. 网络连接是否正常")
        print(f"  3. 代理配置是否正确（如果使用代理）")
        import traceback
        print(traceback.format_exc())
        print(f"\n💡 提示: 配置正确的 API 密钥后，重启服务即可连接")

    # 创建 Bot 实例（使用真实交易所）
    class RealBot:
        def __init__(self, exchange):
            self.is_running = True
            self.event_bus = event_bus
            self.position_manager = position_manager
            self.risk_manager = risk_manager
            self.strategy_manager = strategy_manager
            self.exchange = exchange
            self.strategy = None

    bot = RealBot(okx_connector)

    # 创建 Web 服务器
    print(f"🌐 正在启动 Web 服务器...")
    web_server = WebServer(
        config=risk_config,
        bot_instance=bot,
        ws_log_handler=ws_log_handler
    )

    # 启动服务器
    import uvicorn
    host = "0.0.0.0"
    port = 5000

    print(f"🚀 服务器启动成功!")
    print(f"📍 API 地址: http://localhost:{port}")
    print(f"📍 API 文档: http://localhost:{port}/docs")
    print(f"📍 前端地址: http://localhost:5173")
    print()
    print("="*60)
    print("服务器正在运行，按 Ctrl+C 停止")
    print("="*60)
    print()

    try:
        config = uvicorn.Config(
            app=web_server.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务器...")
    finally:
        # 清理资源
        await okx_connector.__aexit__(None, None, None)
        print("✅ 服务器已停止")


if __name__ == "__main__":
    asyncio.run(main())
