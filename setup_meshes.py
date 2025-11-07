#!/usr/bin/env python3
"""
Tripo3D API를 사용해서 이미지 기반 메시 3개를 생성하는 1회용 스크립트
data/Mesh_Image의 3개 이미지로부터 메시를 생성하고, Task ID를 .env에 저장합니다.

사용법:
    python3 setup_meshes.py
"""

import os
import requests
import json
import time
import base64
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TRIPO_API_KEY = os.getenv("TRIPO_API_KEY")
TRIPO_API_URL = "https://api.tripo3d.ai/v2/openapi/task"
TRIPO_UPLOAD_URL = "https://api.tripo3d.ai/v2/openapi/upload/sts"

if not TRIPO_API_KEY:
    print("❌ TRIPO_API_KEY가 설정되어 있지 않습니다!")
    exit(1)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TRIPO_API_KEY}",
}

# 생성할 메시 정의 (이미지 기반)
MESH_CONFIGS = [
    {
        "name": "Spaceship",
        "env_var": "MESH_SPACESHIP_TASK_ID",
        "image_path": "data/Mesh_Image/Spaceship.png",
    },
    {
        "name": "Locket",
        "env_var": "MESH_LOCKET_TASK_ID",
        "image_path": "data/Mesh_Image/Locket.png",
    },
    {
        "name": "Single Character",
        "env_var": "MESH_CHARACTER_TASK_ID",
        "image_path": "data/Mesh_Image/SingleCharacter.png",
    }
]


def get_file_extension(image_path: str) -> str:
    """이미지 파일 확장자 가져오기"""
    ext = os.path.splitext(image_path)[1].lower()
    if ext == ".jpg":
        return "jpg"
    elif ext == ".jpeg":
        return "jpeg"
    elif ext == ".png":
        return "png"
    return "png"


def upload_image(image_path: str, mesh_name: str) -> str:
    """
    이미지를 Tripo3D에 업로드하고 image_token 획득

    Returns:
        image_token (str) 또는 None
    """
    if not os.path.exists(image_path):
        print(f"❌ 이미지 파일을 찾을 수 없습니다: {image_path}")
        return None

    print(f"📤 [{mesh_name}] 이미지 업로드 중...")

    try:
        # Multipart form-data로 파일 업로드
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f, "image/png")}
            upload_headers = {"Authorization": f"Bearer {TRIPO_API_KEY}"}

            response = requests.post(
                TRIPO_UPLOAD_URL,
                headers=upload_headers,
                files=files,
                timeout=30
            )

        print(f"   업로드 응답 상태: {response.status_code}")

        if response.status_code != 200:
            print(f"   ❌ 업로드 실패: {response.text}")
            return None

        result = response.json()
        print(f"   응답: {json.dumps(result, indent=2)}")

        if result.get("code") == 0:
            image_token = result.get("data", {}).get("image_token")
            if image_token:
                print(f"✅ [{mesh_name}] 업로드 완료! Token: {image_token}")
                return image_token
            else:
                print(f"❌ [{mesh_name}] image_token을 얻지 못했습니다")
                return None
        else:
            print(f"❌ [{mesh_name}] 업로드 API 오류: {result.get('message')}")
            return None

    except Exception as e:
        print(f"❌ 업로드 오류: {str(e)}")
        return None


def create_mesh_from_image(image_path: str, mesh_name: str, image_token: str) -> dict:
    """
    이미지로부터 3D 메시 생성

    Args:
        image_path: 로컬 이미지 경로 (파일 검증용)
        mesh_name: 메시 이름 (로그용)
        image_token: Tripo3D에서 업로드 후 받은 image_token
    """
    if not os.path.exists(image_path):
        print(f"❌ 이미지 파일을 찾을 수 없습니다: {image_path}")
        return None

    if not image_token:
        print(f"❌ image_token이 필요합니다.")
        return None

    print(f"🎨 [{mesh_name}] 메시 생성 요청 중...")

    file_ext = get_file_extension(image_path)

    # Tripo3D API: image_to_model with file_token
    payload = {
        "type": "image_to_model",
        "file": {
            "type": file_ext,
            "file_token": image_token
        },
        "model_version": "v2.5-20250123",
    }

    print(f"   Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(TRIPO_API_URL, headers=headers, json=payload, timeout=30)
        print(f"   응답 상태: {response.status_code}")

        if response.status_code != 200:
            print(f"   ❌ 오류: {response.text}")
            return None

        result = response.json()
        print(f"   응답: {json.dumps(result, indent=2)}")

        return result

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        return None


def check_task_status(task_id: str) -> dict:
    """
    생성 중인 작업의 상태 확인
    """
    status_url = f"{TRIPO_API_URL}/{task_id}"

    try:
        response = requests.get(status_url, headers=headers, timeout=30)
        return response.json()
    except Exception as e:
        print(f"❌ 상태 확인 오류: {str(e)}")
        return None


def get_task_error(task_id: str) -> dict:
    """
    실패한 작업의 상세 에러 정보 가져오기
    """
    status = check_task_status(task_id)
    if status and status.get("code") == 0:
        data = status.get("data", {})
        return {
            "status": data.get("status"),
            "error": data.get("error"),
            "output": data.get("output"),
        }
    return status


def wait_for_completion(task_id: str, mesh_name: str, max_wait: int = 600) -> bool:
    """
    메시 생성이 완료될 때까지 대기 (최대 10분)
    """
    print(f"⏳ [{mesh_name}] Task {task_id} 완료 대기 중...")

    start_time = time.time()
    elapsed = 0

    while elapsed < max_wait:
        status = check_task_status(task_id)

        if status is None:
            return False

        state = status.get("data", {}).get("status", "unknown")
        progress = status.get("data", {}).get("progress", 0)

        # 진행률 표시
        print(f"   상태: {state} | 진행률: {progress}%", end="\r")

        if state == "success":
            print(f"\n✅ [{mesh_name}] Task {task_id} 완료!")
            return True
        elif state in ["failed", "error"]:
            print(f"\n❌ [{mesh_name}] Task {task_id} 실패!")
            # 에러 정보 출력
            error_info = get_task_error(task_id)
            print(f"   에러 정보: {json.dumps(error_info, indent=2, ensure_ascii=False)}")
            return False

        elapsed = time.time() - start_time
        time.sleep(3)  # 3초마다 확인

    print(f"\n⏱️ [{mesh_name}] Task {task_id} 시간 초과 (10분)")
    return False


def update_env_file(task_ids: dict):
    """
    .env 파일 업데이트
    """
    env_path = os.path.join(os.path.dirname(__file__), ".env")

    if not os.path.exists(env_path):
        print(f"❌ .env 파일을 찾을 수 없습니다: {env_path}")
        return False

    # 기존 .env 읽기
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 업데이트할 변수들
    updated_vars = set(task_ids.keys())
    new_lines = []

    # 기존 라인 필터링 (업데이트할 변수 제외)
    for line in lines:
        skip = False
        for var_name in updated_vars:
            if line.startswith(f"{var_name}="):
                skip = True
                break
        if not skip:
            new_lines.append(line)

    # 새로운 라인 추가
    for var_name, task_id in task_ids.items():
        new_lines.append(f"{var_name}={task_id}\n")

    # .env 파일에 쓰기
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    return True


def get_ngrok_url() -> str:
    """
    Ngrok의 공개 URL을 가져오기
    """
    try:
        resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=5)
        data = resp.json()
        tunnels = data.get("tunnels", [])
        if tunnels:
            url = tunnels[0]["public_url"]
            print(f"[Ngrok] 공개 URL: {url}")
            return url
    except Exception as e:
        print(f"[Ngrok] URL 감지 실패: {e}")
    return None


def create_all_meshes():
    """
    모든 메시 생성 및 .env 업데이트
    """
    print("=" * 80)
    print("🚀 Tripo3D 메시 생성 시작 (1회용 셋업)")
    print("=" * 80)

    task_ids = {}
    mesh_tasks = []  # (task_id, mesh_name, env_var) 튜플 저장

    # 1단계: 이미지 업로드 및 메시 생성 요청
    for config in MESH_CONFIGS:
        print(f"\n{'='*70}")
        print(f"[{config['name']}]")
        print(f"{'='*70}")

        # 1-1: 이미지 업로드
        image_token = upload_image(
            image_path=config["image_path"],
            mesh_name=config["name"]
        )

        if not image_token:
            print(f"❌ [{config['name']}] 업로드 실패!")
            continue

        # 1-2: 메시 생성 요청
        result = create_mesh_from_image(
            image_path=config["image_path"],
            mesh_name=config["name"],
            image_token=image_token
        )

        if not result or result.get("code") != 0:
            print(f"❌ [{config['name']}] 메시 생성 요청 실패!")
            continue

        task_id = result.get("data", {}).get("task_id")
        if not task_id:
            print(f"❌ [{config['name']}] Task ID를 얻지 못했습니다")
            continue

        print(f"✅ [{config['name']}] Task ID 발급됨: {task_id}")
        mesh_tasks.append((task_id, config["name"], config["env_var"]))
        task_ids[config["env_var"]] = task_id

    if not mesh_tasks:
        print("\n❌ 생성된 메시가 없습니다. 셋업 중단.")
        return

    # 2단계: 모든 메시의 완료 대기
    print("\n" + "=" * 80)
    print("⏳ 모든 메시 생성 완료 대기 중...")
    print("=" * 80)

    for task_id, mesh_name, env_var in mesh_tasks:
        if not wait_for_completion(task_id, mesh_name):
            print(f"⚠️ [{mesh_name}] 생성 중단됨 (타임아웃 또는 오류)")
            del task_ids[env_var]

    # 3단계: .env 파일 업데이트
    if task_ids:
        print("\n" + "=" * 80)
        print("📝 .env 파일 업데이트 중...")
        print("=" * 80)

        if update_env_file(task_ids):
            print("✅ .env 파일 업데이트 완료!")
            print(f"\n📋 업데이트된 내용:")
            for env_var, task_id in task_ids.items():
                print(f"   {env_var}={task_id}")
        else:
            print("❌ .env 파일 업데이트 실패!")
    else:
        print("❌ 완료된 메시가 없으므로 .env를 업데이트하지 않습니다.")

    print("\n" + "=" * 80)
    print("✅ 셋업 완료!")
    print("=" * 80)
    print("\n이제 다음 명령어로 서버를 다시 시작하세요:")
    print("   uvicorn backend.main:app --reload")


if __name__ == "__main__":
    create_all_meshes()
