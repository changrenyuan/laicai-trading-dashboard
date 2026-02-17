#!/usr/bin/env python3
"""
测试 WebSocket 连接和事件推送
"""
import asyncio
import json
import websockets
from datetime import datetime


async def test_websocket():
    """测试 WebSocket 连接"""
    print("\n" + "="*60)
    print("🧪 测试 WebSocket 连接和事件推送")
    print("="*60 + "\n")

    uri = "ws://localhost:5000/ws"

    try:
        print("📡 连接到 WebSocket...")
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 连接成功\n")

            # 监听事件
            print("📡 监听事件（10 秒）...")
            end_time = asyncio.get_event_loop().time() + 10

            while asyncio.get_event_loop().time() < end_time:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)

                    print(f"📩 收到事件: {data.get('type')}")
                    print(f"   时间戳: {data.get('timestamp')}")
                    print(f"   内容: {json.dumps(data, indent=2, ensure_ascii=False)}\n")

                except asyncio.TimeoutError:
                    continue

            print("⏱️  监听结束\n")

    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket 连接失败: {e}\n")
    except Exception as e:
        print(f"❌ 测试失败: {e}\n")

    print("="*60)
    print("🎉 WebSocket 测试完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_websocket())
