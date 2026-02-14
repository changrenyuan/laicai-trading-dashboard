import sys
sys.path.insert(0, '/workspace/projects')

import requests
import json

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
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Response JSON: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
