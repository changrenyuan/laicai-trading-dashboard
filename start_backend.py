#!/usr/bin/env python3
"""
启动后端服务器 - 使用真实交易所
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.event_bus import EventBus
from src.core.position import PositionManager
from src.core.risk_manager import RiskManager
from src.core.strategy_manager import StrategyManager
from src.core.websocket_log_handler import setup_websocket_logging
from src.ui.web_multi_strategy import WebServer
from src.connectors.okx_lite import OKXConnector


async def load_config(config_path: str = "config.json") -> dict:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"❌ 错误: 配置文件 {config_path} 不存在")
        print("请先配置 config.json 文件，填入你的交易所 API 密钥")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ 错误: 配置文件格式错误: {e}")
        sys.exit(1)


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

    # 加载配置
    config = await load_config()

    # 验证 API 密钥
    api_creds = config.get('api_credentials', {})
    if any([
        api_creds.get('api_key') == 'YOUR_OKX_API_KEY',
        api_creds.get('secret_key') == 'YOUR_OKX_SECRET_KEY',
        api_creds.get('passphrase') == 'YOUR_OKX_PASSPHRASE'
    ]):
        print("❌ 错误: 请在 config.json 中配置真实的 OKX API 密钥")
        print("配置位置: config.json -> api_credentials")
        print("你需要:")
        print("  1. 登录 OKX 官网: https://www.okx.com")
        print("  2. 进入 API 管理，创建 API Key")
        print("  3. 填入 api_key, secret_key, passphrase")
        sys.exit(1)

    # 创建核心组件
    event_bus = EventBus()
    position_manager = PositionManager()
    risk_config = config.get('risk_management', {})
    risk_manager = RiskManager(risk_config)
    strategy_manager = StrategyManager(event_bus, position_manager, risk_manager)

    # 设置日志处理器
    ws_log_handler = setup_websocket_logging("INFO")

    # 创建真实交易所连接
    exchange_config = {
        'api_key': api_creds.get('api_key'),
        'secret_key': api_creds.get('secret_key'),
        'passphrase': api_creds.get('passphrase'),
        'registration_sub_domain': config['exchange'].get('registration_sub_domain', 'www'),
        'sandbox': config['exchange'].get('sandbox', False),
    }

    # 添加代理配置
    proxy_config = config.get('proxy', {})
    if proxy_config.get('enabled', False):
        proxy_type = proxy_config.get('type', 'http')
        proxy_host = proxy_config.get('host', '127.0.0.1')
        proxy_port = proxy_config.get('port', 7890)

        if proxy_type == 'socks5':
            exchange_config['proxy'] = f'socks5://{proxy_host}:{proxy_port}'
        elif proxy_type == 'http':
            exchange_config['proxy'] = f'http://{proxy_host}:{proxy_port}'
        else:
            print(f"⚠️  警告: 不支持的代理类型 {proxy_type}，将不使用代理")

    # 创建真实交易所实例
    print(f"🔗 正在连接 OKX 交易所...")
    print(f"   模式: {'沙盒' if config['exchange'].get('sandbox') else '实盘'}")
    print(f"   子域名: {config['exchange'].get('registration_sub_domain', 'www')}")
    if proxy_config.get('enabled', False):
        print(f"   代理: {exchange_config.get('proxy', '无')}")

    try:
        okx_connector = OKXConnector(exchange_config)
        await okx_connector.__aenter__()

        # 测试连接
        balance = await okx_connector.get_balance()
        print(f"✅ 成功连接到 OKX 交易所")
        print(f"💰 账户余额: {balance}")
    except Exception as e:
        print(f"❌ 连接 OKX 交易所失败: {e}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)

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
        config=config,
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
