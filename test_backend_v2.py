#!/usr/bin/env python3
"""
测试后端改造后的 API
"""
import asyncio
import json
from src.ui.web_v2 import WebServerV2
from src.core.position import PositionManager
from src.core.risk_manager import RiskManager


class MockBot:
    """模拟机器人实例"""
    def __init__(self):
        self.is_running = False
        self.strategy = None
        self.position_manager = PositionManager()
        self.risk_manager = RiskManager({})


async def test_web_server_v2():
    """测试 WebServer v2"""
    print("\n" + "="*60)
    print("🧪 测试后端改造后的 API")
    print("="*60 + "\n")

    # 创建模拟机器人
    bot = MockBot()

    # 创建 WebServer v2
    config = {
        "api_key": "test",
        "secret_key": "test",
        "passphrase": "test",
        "sandbox": True
    }

    web_server = WebServerV2(config=config, bot_instance=bot)

    print("✅ WebServer v2 初始化完成\n")

    # 测试健康检查
    print("📋 测试健康检查...")
    try:
        from fastapi.testclient import TestClient
        client = TestClient(web_server.app)

        response = client.get("/api/health")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
    except Exception as e:
        print(f"   ❌ 健康检查失败: {e}\n")

    # 测试 API 根路径
    print("📋 测试 API 根路径...")
    try:
        response = client.get("/")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
    except Exception as e:
        print(f"   ❌ API 根路径测试失败: {e}\n")

    # 测试命令接口 - start_strategy
    print("📋 测试命令接口 - start_strategy...")
    try:
        response = client.post(
            "/api/command",
            json={
                "cmd": "start_strategy",
                "params": {
                    "strategy_id": "test_strategy"
                }
            }
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
    except Exception as e:
        print(f"   ❌ start_strategy 测试失败: {e}\n")

    # 测试命令接口 - place_order
    print("📋 测试命令接口 - place_order...")
    try:
        response = client.post(
            "/api/command",
            json={
                "cmd": "place_order",
                "params": {
                    "symbol": "ETH-USDT",
                    "side": "buy",
                    "size": 0.01,
                    "type": "market"
                }
            }
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
    except Exception as e:
        print(f"   ❌ place_order 测试失败: {e}\n")

    # 测试状态接口
    print("📋 测试状态接口...")
    try:
        response = client.get("/api/state")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
    except Exception as e:
        print(f"   ❌ 状态接口测试失败: {e}\n")

    # 测试无效命令
    print("📋 测试无效命令...")
    try:
        response = client.post(
            "/api/command",
            json={
                "cmd": "invalid_command",
                "params": {}
            }
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}\n")
    except Exception as e:
        print(f"   ❌ 无效命令测试失败: {e}\n")

    print("="*60)
    print("🎉 测试完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_web_server_v2())
