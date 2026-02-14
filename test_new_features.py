import sys
sys.path.insert(0, '/workspace/projects')

import requests
import json

print("=== 测试 Hummingbot Lite 新功能 ===\n")

# 测试1: 获取策略列表
print("1. 获取策略列表:")
url = "http://localhost:5000/api/strategies"
response = requests.get(url)
result = response.json()
print(f"   找到 {len(result['strategies'])} 种策略\n")

# 测试2: 创建策略实例
print("2. 创建 AMM 套利策略实例:")
url = "http://localhost:5000/api/strategy-instances"
data = {
    "strategy_name": "amm_arbitrage",
    "config": {
        "trading_pair_1": "BTC-USDT",
        "trading_pair_2": "BTC-USDT",
        "order_amount": 0.001,
        "min_profitability": 0.001
    }
}
response = requests.post(url, json=data)
result = response.json()
instance_id = result.get("instance_id")
print(f"   创建成功: {instance_id}\n")

# 测试3: 启动策略
print("3. 启动策略:")
url = f"http://localhost:5000/api/strategy-instances/{instance_id}/start"
response = requests.post(url)
result = response.json()
print(f"   启动结果: {result}\n")

# 测试4: Kill Switch
print("4. 测试 Kill Switch (紧急撤单):")
url = "http://localhost:5000/api/kill-switch"
response = requests.post(url)
result = response.json()
print(f"   Kill Switch 结果: {result}\n")

# 测试5: 获取实例状态
print("5. 获取策略实例状态:")
url = f"http://localhost:5000/api/strategy-instances/{instance_id}"
response = requests.get(url)
result = response.json()
print(f"   策略状态: {'运行中' if result.get('is_running') else '已停止'}\n")

# 测试6: 删除实例
print("6. 删除策略实例:")
url = f"http://localhost:5000/api/strategy-instances/{instance_id}"
response = requests.delete(url)
result = response.json()
print(f"   删除结果: {result}\n")

print("=== 所有测试完成 ===")
