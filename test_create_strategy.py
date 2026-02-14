import sys
sys.path.insert(0, '/workspace/projects')

from src.core.event_bus import EventBus
from src.core.position import PositionManager
from src.core.risk_manager import RiskManager
from src.core.strategy_manager import StrategyManager

# 创建依赖对象
event_bus = EventBus()
position_manager = PositionManager()
risk_manager = RiskManager({"max_position_size": 1.0, "max_daily_loss": 1000})

# 创建策略管理器
strategy_manager = StrategyManager(event_bus, position_manager, risk_manager)

# 设置交易所回调（模拟）
async def mock_create_order(symbol, side, size, price, order_type):
    return f"order_{symbol}_{side}_{size}_{price}"

async def mock_cancel_order(order_id):
    return True

async def mock_get_balance():
    return {"USDT": 10000.0, "BTC": 0.5}

strategy_manager.set_exchange_callbacks({
    "create_order": mock_create_order,
    "cancel_order": mock_cancel_order,
    "get_balance": mock_get_balance
})

# 创建策略配置
config = {
    "trading_pair_1": "BTC-USDT",
    "trading_pair_2": "BTC-USDT",
    "order_amount": 0.001,
    "min_profitability": 0.001
}

try:
    # 尝试创建策略实例
    import asyncio
    instance = asyncio.run(strategy_manager.create_strategy_instance(
        strategy_name="amm_arbitrage",
        config=config,
        instance_name="test_instance"
    ))
    print("策略实例创建成功！")
    print(f"实例ID: {instance.instance_id}")
    print(f"策略名称: {instance.strategy_name}")
except Exception as e:
    print(f"策略实例创建失败: {e}")
    import traceback
    traceback.print_exc()
