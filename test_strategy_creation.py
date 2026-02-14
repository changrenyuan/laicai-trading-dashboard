import sys
sys.path.insert(0, '/workspace/projects')

from src.core.event_bus import EventBus
from src.core.position import PositionManager
from src.core.risk_manager import RiskManager
from src.strategies.amm_arbitrage import AMMArbitrageStrategy

# 创建依赖对象
event_bus = EventBus()
position_manager = PositionManager()
risk_manager = RiskManager({"max_position_size": 1.0, "max_daily_loss": 1000})

# 创建策略配置
config = {
    "trading_pair_1": "BTC-USDT",
    "trading_pair_2": "BTC-USDT",
    "order_amount": 0.001,
    "min_profitability": 0.001
}

try:
    # 尝试创建策略实例
    strategy = AMMArbitrageStrategy(
        event_bus=event_bus,
        position_manager=position_manager,
        risk_manager=risk_manager,
        config=config
    )
    print("策略创建成功！")
    print(f"策略类型: {type(strategy)}")
    print(f"策略名称: {strategy.__class__.__name__}")
    print(f"抽象方法: {AMMArbitrageStrategy.__abstractmethods__}")
except Exception as e:
    print(f"策略创建失败: {e}")
    import traceback
    traceback.print_exc()
