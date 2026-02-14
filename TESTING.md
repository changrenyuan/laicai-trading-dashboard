# Hummingbot Lite 测试指南

## 环境检查

### 1. Python 版本检查
```bash
python --version
# 需要 Python 3.12+
```

### 2. 依赖安装
```bash
pip install -r requirements.txt
```

### 3. 配置文件检查
```bash
# 复制模板
cp config.example.yaml config.yaml

# 编辑配置
vim config.yaml  # 或使用其他编辑器
```

## 功能测试

### 测试 1: 模块导入测试
```bash
python -c "
import sys
sys.path.insert(0, '/workspace/projects')

# 测试核心模块
from src.core.event_bus import EventBus
from src.core.position import PositionManager, PositionSide
from src.core.risk_manager import RiskManager
print('✓ Core modules OK')

# 测试策略模块
from src.strategies.market_maker import MarketMakerStrategy
print('✓ Strategy modules OK')

# 测试连接器
from src.connectors.okx import OKXConnector
print('✓ Connector modules OK')

print('\\n✓ All modules imported successfully')
"
```

### 测试 2: 事件总线测试
```bash
python -c "
import asyncio
from src.core.event_bus import EventBus

async def test_event_bus():
    bus = EventBus()

    # 测试发布订阅
    received = []
    def callback(data):
        received.append(data)

    bus.subscribe('test_event', callback)
    await bus.publish('test_event', {'test': 'data'})

    if len(received) == 1:
        print('✓ Event bus OK')
    else:
        print('✗ Event bus FAILED')

asyncio.run(test_event_bus())
"
```

### 测试 3: 仓位管理测试
```bash
python -c "
from src.core.position import PositionManager, PositionSide

pm = PositionManager()

# 开仓测试
pos = pm.open_position('BTC-USDT', PositionSide.LONG, 0.01, 50000)
print(f'✓ Position opened: {pos.symbol} {pos.side.value}')

# 平仓测试
closed = pm.close_position('BTC-USDT', PositionSide.LONG, 50500)
if closed:
    print(f'✓ Position closed: PnL = {closed.realized_pnl}')

# 盈亏计算
total_pnl = pm.get_total_realized_pnl()
print(f'✓ Total PnL: {total_pnl}')
"
```

### 测试 4: 风控测试
```bash
python -c "
from src.core.risk_manager import RiskManager

config = {
    'max_position_size': 0.1,
    'max_order_size': 0.01,
    'stop_loss_percentage': 0.02,
    'take_profit_percentage': 0.03,
    'max_daily_loss': 0.05
}

rm = RiskManager(config)

# 订单大小检查
allowed, msg = rm.check_order_size(0.005)
print(f'✓ Order size check: {allowed}')

# 仓位限制检查
allowed, msg = rm.check_position_limit('BTC-USDT', 0.0, 0.05)
print(f'✓ Position limit check: {allowed}')

# 止损设置
stop_price = rm.set_stop_loss('BTC-USDT', 'long', 50000)
print(f'✓ Stop loss set at: {stop_price}')

# 止损触发检查
triggered, order = rm.check_stop_loss('BTC-USDT', 'long', 49000)
print(f'✓ Stop loss triggered: {triggered}')
"
```

### 测试 5: OKX 连接测试（需要 API 密钥）

⚠️ **此测试需要有效的 OKX API 密钥**

```bash
python -c "
import asyncio
from src.connectors.okx import OKXConnector

async def test_okx():
    # 使用沙盒环境测试
    config = {
        'api_key': 'YOUR_API_KEY',
        'secret_key': 'YOUR_SECRET_KEY',
        'passphrase': 'YOUR_PASSPHRASE',
        'sandbox': True  # 测试网
    }

    connector = OKXConnector(config)

    # 测试连接
    connected = await connector.test_connection()
    if connected:
        print('✓ OKX connection OK')

        # 获取余额（需要 API 密钥）
        try:
            balance = await connector.get_balance()
            print(f'✓ Balance retrieved: {len(balance)} assets')
        except Exception as e:
            print(f'⚠ Balance test skipped (needs valid API): {e}')

        await connector.close()
    else:
        print('✗ OKX connection FAILED')

asyncio.run(test_okx())
"
```

### 测试 6: Web 服务器测试

```bash
# 启动服务器（在后台）
python src/main.py &
SERVER_PID=$!

# 等待服务器启动
sleep 3

# 测试 API
echo "Testing API endpoints..."

# 测试状态 API
curl -s http://localhost:5000/api/status | python -m json.tool > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ API status endpoint OK"
else
    echo "✗ API status endpoint FAILED"
fi

# 测试事件 API
curl -s http://localhost:5000/api/events | python -m json.tool > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ API events endpoint OK"
else
    echo "✗ API events endpoint FAILED"
fi

# 停止服务器
kill $SERVER_PID
echo "✓ Web server tests completed"
```

## 完整流程测试

### 测试 7: 完整启动流程（模拟）

```bash
# 1. 创建测试配置
cat > test_config.yaml << 'EOF'
exchange:
  name: "okx"
  api_key: "TEST_KEY"
  secret_key: "TEST_SECRET"
  passphrase: "TEST_PASS"
  sandbox: true

strategy:
  name: "market_maker"
  trading_pair: "BTC-USDT"
  order_amount: 0.001
  bid_spread: 0.001
  ask_spread: 0.001
  order_refresh_time: 30

risk_management:
  max_position_size: 0.1
  max_order_size: 0.01
  stop_loss_percentage: 0.02
  take_profit_percentage: 0.03
  max_daily_loss: 0.05

server:
  host: "127.0.0.1"
  port: 5001

position_management:
  auto_rebalance: true
  min_order_size: 0.001
  inventory_target_base_pct: 0.5
EOF

# 2. 模拟启动（不连接真实交易所）
python << 'PYEOF'
import asyncio
from src.core.event_bus import EventBus
from src.core.position import PositionManager
from src.core.risk_manager import RiskManager
from src.strategies.market_maker import MarketMakerStrategy

async def main():
    print("初始化组件...")

    # 初始化核心组件
    event_bus = EventBus()
    position_manager = PositionManager()
    risk_manager = RiskManager({
        'max_position_size': 0.1,
        'max_order_size': 0.01,
        'stop_loss_percentage': 0.02,
        'take_profit_percentage': 0.03,
        'max_daily_loss': 0.05
    })

    print("✓ 核心组件初始化完成")

    # 创建策略
    strategy_config = {
        'trading_pair': 'BTC-USDT',
        'order_amount': 0.001,
        'bid_spread': 0.001,
        'ask_spread': 0.001,
        'order_refresh_time': 30
    }

    strategy = MarketMakerStrategy(
        event_bus=event_bus,
        position_manager=position_manager,
        risk_manager=risk_manager,
        config=strategy_config
    )

    print("✓ 策略创建完成")

    # 模拟市场数据
    ticker = {
        'symbol': 'BTC-USDT',
        'last': 50000,
        'bid': 49990,
        'ask': 50010
    }

    await strategy.on_tick(ticker)
    print("✓ 策略处理市场数据")

    # 检查策略状态
    status = strategy.get_status()
    print(f"✓ 策略状态: {status}")

    print("\n✓ 完整流程测试通过")

asyncio.run(main())
PYEOF

# 清理
rm test_config.yaml
```

## 性能测试

### 测试 8: 事件处理性能
```bash
python << 'PYEOF'
import asyncio
import time
from src.core.event_bus import EventBus

async def test_performance():
    bus = EventBus()
    count = 0

    def callback(data):
        nonlocal count
        count += 1

    bus.subscribe('test', callback)

    # 测试 1000 次事件发布
    start = time.time()
    for i in range(1000):
        await bus.publish('test', {'data': i})

    elapsed = time.time() - start
    print(f"✓ 处理 1000 个事件，耗时: {elapsed:.3f}秒")
    print(f"✓ 平均每个事件: {elapsed/1000*1000:.2f}毫秒")

asyncio.run(test_performance())
PYEOF
```

## 常见问题排查

### 问题 1: ModuleNotFoundError
```bash
# 解决方案
pip install -r requirements.txt
```

### 问题 2: OKX 连接失败
```bash
# 检查配置
python -c "
import yaml
with open('config.yaml') as f:
    config = yaml.safe_load(f)
    print('API Key:', 'SET' if config['exchange'].get('api_key') != 'YOUR_API_KEY' else 'NOT SET')
    print('Secret:', 'SET' if config['exchange'].get('secret_key') != 'YOUR_SECRET_KEY' else 'NOT SET')
    print('Passphrase:', 'SET' if config['exchange'].get('passphrase') != 'YOUR_PASSPHRASE' else 'NOT SET')
"
```

### 问题 3: 端口被占用
```bash
# 检查端口
lsof -i:5000

# 修改配置文件中的端口
# server:
#   port: 5001  # 改为其他端口
```

## 测试总结

所有测试完成后，您应该看到：

```
✓ Core modules OK
✓ Strategy modules OK
✓ Connector modules OK
✓ Event bus OK
✓ Position management OK
✓ Risk management OK
✓ Web server OK
✓ Complete flow OK
✓ Performance OK
```

如果所有测试通过，系统已准备就绪，可以进行实盘测试。
