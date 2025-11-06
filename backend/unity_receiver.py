# backend/unity_bridge.py
import json
import aiohttp

# Unity 쪽에서 열어둔 HTTP 수신 엔드포인트 주소
UNITY_ENDPOINT = "http://localhost:8080/unity_receive"

async def send_to_unity(payload: dict):
    """
    Unity로 JSON 데이터를 전송.

    Args:
        payload (dict): Unity로 보낼 데이터 (예: 도안 정보, task_id 등)
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(UNITY_ENDPOINT, json=payload) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise RuntimeError(f"Unity 전송 실패 ({resp.status}): {text}")
                print(f"[UnityBridge] Unity 응답: {text}")
                return text
        except Exception as e:
            print(f"[UnityBridge] 전송 오류: {e}")
