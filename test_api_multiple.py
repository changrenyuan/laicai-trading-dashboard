import sys
sys.path.insert(0, '/workspace/projects')

import requests

# 测试1: 检查服务是否运行
url = "http://localhost:5000/api/strategies"
try:
    response = requests.get(url)
    print(f"Test 1 - GET /api/strategies:")
    print(f"  Status code: {response.status_code}")
    print(f"  Response: {response.text[:200]}")
except Exception as e:
    print(f"Test 1 failed: {e}")

# 测试2: 创建策略实例
url = "http://localhost:5000/api/strategy-instances"
headers = {"Content-Type": "application/json"}
data = {
    "strategy_name": "amm_arbitrage",
    "config": {
        "trading_pair_1": "BTC-USDT",
        "trading_pair_2": "BTC-USDT",
        "order_amount": 0.001,
        "min_profitability": 0.001
    }
}

try:
    response = requests.post(url, headers=headers, json=data)
    print(f"\nTest 2 - POST /api/strategy-instances:")
    print(f"  Status code: {response.status_code}")
    print(f"  Response: {response.text}")
except Exception as e:
    print(f"Test 2 failed: {e}")

# 测试3: 使用空配置
data3 = {
    "strategy_name": "amm_arbitrage",
    "config": {}
}

try:
    response = requests.post(url, headers=headers, json=data3)
    print(f"\nTest 3 - POST /api/strategy-instances (empty config):")
    print(f"  Status code: {response.status_code}")
    print(f"  Response: {response.text}")
except Exception as e:
    print(f"Test 3 failed: {e}")
