import sys
sys.path.insert(0, '/workspace/projects')

import requests

strategies = [
    "market_maker",
    "pure_market_making",
    "perpetual_market_making",
    "spot_perpetual_arbitrage",
    "amm_arbitrage",
    "avellaneda_market_making",
    "cross_exchange_market_making",
    "liquidity_mining",
    "hedge",
    "cross_exchange_mining"
]

url = "http://localhost:5000/api/strategy-instances"
headers = {"Content-Type": "application/json"}

print("Testing all strategies:")
print("=" * 60)

for strategy_name in strategies:
    data = {
        "strategy_name": strategy_name,
        "config": {
            "trading_pair": "BTC-USDT",
            "order_amount": 0.001
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if "instance_id" in result:
                print(f"✓ {strategy_name}: Success (instance_id={result['instance_id']})")
            else:
                print(f"✗ {strategy_name}: Failed - {result.get('error', 'Unknown error')}")
        else:
            print(f"✗ {strategy_name}: HTTP {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ {strategy_name}: Exception - {e}")

print("=" * 60)
print("All tests completed!")
