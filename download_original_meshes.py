#!/usr/bin/env python3
"""
원본 메시 3개를 Tripo3D에서 다운로드하여 로컬에 저장하는 스크립트

사용 방법:
  python download_original_meshes.py

결과:
  - frontend/meshes/spaceship.glb
  - frontend/meshes/locket.glb
  - frontend/meshes/character.glb
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

TRIPO_API_KEY = os.getenv("TRIPO_API_KEY")
TRIPO_BASE_URL = "https://api.tripo3d.ai/v2/openapi"

# Task ID 매핑
MESH_CONFIGS = {
    "spaceship": {
        "task_id": os.getenv("MESH_SPACESHIP_TASK_ID"),
        "filename": "spaceship.glb",
        "name": "🚀 Spaceship"
    },
    "locket": {
        "task_id": os.getenv("MESH_LOCKET_TASK_ID"),
        "filename": "locket.glb",
        "name": "💎 Locket"
    },
    "character": {
        "task_id": os.getenv("MESH_CHARACTER_TASK_ID"),
        "filename": "character.glb",
        "name": "👤 Single Character"
    }
}

# 저장 디렉토리
MESHES_DIR = os.path.join(os.path.dirname(__file__), "frontend", "meshes")
os.makedirs(MESHES_DIR, exist_ok=True)

def get_task_status(task_id: str) -> dict:
    """Tripo3D Task 상태 조회"""
    url = f"{TRIPO_BASE_URL}/task/{task_id}"
    headers = {"Authorization": f"Bearer {TRIPO_API_KEY}"}

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()

def download_mesh(task_id: str, filename: str, mesh_name: str) -> bool:
    """
    Task ID로부터 GLB 파일을 다운로드하여 저장

    Args:
        task_id: Tripo3D Task ID
        filename: 저장할 파일명
        mesh_name: 표시용 메시 이름

    Returns:
        성공 여부
    """
    print(f"\n📥 {mesh_name} 다운로드 중... (Task ID: {task_id})")

    try:
        # Task 상태 조회
        status_response = get_task_status(task_id)

        if status_response.get("code") != 0:
            print(f"  ❌ Task 조회 실패: {status_response}")
            return False

        data = status_response.get("data", {})
        task_status = data.get("status")

        print(f"  상태: {task_status}")

        if task_status != "success":
            print(f"  ⚠️ Task가 완료되지 않음 (현재 상태: {task_status})")
            return False

        # GLB URL 추출 (response 구조에 따라 다름)
        # image_to_model: result.pbr_model.url 또는 output.pbr_model
        # texture_model: result.model.url 또는 output.model
        result = data.get("result", {})
        output = data.get("output", {})

        # 먼저 result 구조 확인
        model_url = (
            result.get("pbr_model", {}).get("url")  # image_to_model
            or result.get("model", {}).get("url")    # texture_model
            or output.get("pbr_model")               # image_to_model fallback
            or output.get("model")                   # texture_model fallback
        )

        if not model_url:
            print(f"  ❌ GLB URL을 찾을 수 없음")
            print(f"     result: {list(result.keys())}")
            print(f"     output: {list(output.keys())}")
            return False

        print(f"  🔗 GLB URL: {model_url[:80]}...")

        # GLB 다운로드
        print(f"  ⏳ 파일 다운로드 중...")
        response = requests.get(model_url, timeout=60)
        response.raise_for_status()

        # 파일 저장
        file_path = os.path.join(MESHES_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(response.content)

        file_size_mb = len(response.content) / 1024 / 1024
        print(f"  ✅ 저장 완료: {file_path}")
        print(f"     파일 크기: {file_size_mb:.2f} MB")

        return True

    except requests.exceptions.RequestException as e:
        print(f"  ❌ 네트워크 오류: {e}")
        return False
    except Exception as e:
        print(f"  ❌ 오류: {type(e).__name__}: {e}")
        return False

def main():
    print("=" * 80)
    print("🎯 Tripo3D 원본 메시 다운로드")
    print("=" * 80)
    print(f"\n📁 저장 위치: {MESHES_DIR}")

    if not TRIPO_API_KEY:
        print("\n❌ 오류: TRIPO_API_KEY를 .env에서 찾을 수 없습니다")
        return False

    results = {}
    for key, config in MESH_CONFIGS.items():
        task_id = config.get("task_id")

        if not task_id:
            print(f"\n⚠️ {config['name']}: Task ID가 설정되지 않음")
            results[key] = False
            continue

        success = download_mesh(
            task_id=task_id,
            filename=config["filename"],
            mesh_name=config["name"]
        )
        results[key] = success

    # 결과 요약
    print(f"\n{'=' * 80}")
    print("📊 결과 요약")
    print(f"{'=' * 80}")

    for key, success in results.items():
        status = "✅ 성공" if success else "❌ 실패"
        print(f"  {MESH_CONFIGS[key]['name']}: {status}")

    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    print(f"\n✨ 전체: {success_count}/{total_count} 완료")

    if success_count == total_count:
        print("\n🎉 모든 메시를 성공적으로 다운로드했습니다!")
        print("\n💡 다음 단계:")
        print("   1. Unity 프로젝트에 frontend/meshes/ 폴더 복사")
        print("   2. glTFast로 GLB 파일 로드")
        print("   3. 텍스처 적용된 모델과 교체")
        return True
    else:
        print("\n⚠️ 일부 메시 다운로드에 실패했습니다")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
