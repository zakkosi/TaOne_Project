import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()

TRIPO_API_KEY = os.getenv("TRIPO_API_KEY")
TRIPO_API_URL = "https://api.tripo3d.ai/v2/openapi/task"
TRIPO_UPLOAD_URL = "https://api.tripo3d.ai/v2/openapi/upload/sts"


class Tripo3DClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or TRIPO_API_KEY
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def upload_image(self, image_bytes: bytes, file_type: str = "png") -> str:
        """
        이미지를 Tripo3D 서버에 업로드하고 image_token 획득

        Args:
            image_bytes: 이미지 바이너리 데이터
            file_type: 파일 타입 (png, jpg, jpeg, webp)

        Returns:
            image_token (str) 또는 None
        """
        try:
            files = {"file": (f"image.{file_type}", image_bytes, f"image/{file_type}")}
            upload_headers = {"Authorization": f"Bearer {self.api_key}"}

            response = requests.post(
                TRIPO_UPLOAD_URL,
                headers=upload_headers,
                files=files,
                timeout=30
            )

            print(f"[TripoClient] 이미지 업로드 응답: {response.status_code}")

            if response.status_code != 200:
                print(f"[TripoClient] 업로드 실패: {response.text}")
                return None

            result = response.json()
            if result.get("code") == 0:
                image_token = result.get("data", {}).get("image_token")
                if image_token:
                    print(f"[TripoClient] ✅ 이미지 업로드 완료! Token: {image_token}")
                    return image_token

        except Exception as e:
            print(f"[TripoClient] 업로드 오류: {str(e)}")

        return None

    def texture_existing_model(
        self,
        original_model_task_id: str,
        texture_image_bytes: bytes = None,
        texture_image_url: str = None,
        texture_prompt_text: str = None,
        model_version: str = "v2.5-20250123",
    ):
        """
        기존 모델에 새 텍스처를 입힘
        Args:
            original_model_task_id: 기존 3D 모델의 task_id
            texture_image_bytes: 텍스처 이미지 바이너리 (권장)
            texture_image_url: 텍스처 이미지 URL (폴백)
            texture_prompt_text: 텍스트 기반 텍스처 프롬프트 (선택)
            model_version: 텍스처 생성 모델 버전
        """
        # 이미지 바이트가 있으면 먼저 업로드
        image_token = None
        if texture_image_bytes:
            image_token = self.upload_image(texture_image_bytes, file_type="jpg")

        # texture_prompt 구성
        texture_prompt = {}

        if image_token:
            # 업로드된 이미지 토큰 사용
            texture_prompt["image"] = {
                "type": "jpg",
                "file_token": image_token
            }
            print(f"[TripoClient] texture_prompt: file_token 사용")
        elif texture_image_url:
            # URL 사용 (폴백)
            texture_prompt["image"] = {
                "type": "jpg",
                "url": texture_image_url
            }
            print(f"[TripoClient] texture_prompt: URL 사용")
        elif texture_prompt_text:
            # 텍스트 프롬프트
            texture_prompt["text"] = texture_prompt_text
            print(f"[TripoClient] texture_prompt: 텍스트 사용")
        else:
            raise ValueError("texture_image_bytes/url 또는 texture_prompt_text 중 하나는 필요합니다.")

        # Payload 구성 (문서 기준)
        payload = {
            "type": "texture_model",
            "original_model_task_id": original_model_task_id,
            "texture_prompt": texture_prompt,
            "texture_quality": "detailed",
            "model_version": model_version,
        }

        print(f"[TripoClient] 요청 payload: {payload}")

        try:
            response = requests.post(
                TRIPO_API_URL,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            print(f"[TripoClient] 응답 상태: {response.status_code}")
            print(f"[TripoClient] 응답 내용: {response.text}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"[TripoClient] HTTP 오류: {e.response.status_code}")
            print(f"[TripoClient] 오류 상세: {e.response.text}")
            raise
        except Exception as e:
            print(f"[TripoClient] 예상치 못한 오류: {str(e)}")
            raise

    def get_task_status(self, task_id: str):
        """Tripo3D에서 현재 태스크 상태 확인"""
        status_url = f"https://api.tripo3d.ai/v2/openapi/task/{task_id}"
        try:
            response = requests.get(status_url, headers=self.headers, timeout=30)
            print(f"[TripoClient] Task Status ({task_id}): {response.status_code}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"[TripoClient] Task Status HTTP 오류: {e.response.status_code}")
            print(f"[TripoClient] 오류 상세: {e.response.text}")
            raise
        except Exception as e:
            print(f"[TripoClient] Task Status 조회 오류: {str(e)}")
            raise

    async def wait_for_task_completion(self, task_id: str, max_wait: int = 600) -> str:
        """
        Task 완료까지 대기하고 다운로드 URL 반환

        Args:
            task_id: 모니터링할 task ID
            max_wait: 최대 대기 시간 (초)

        Returns:
            download_url (str) 또는 None
        """
        import time
        import asyncio

        print(f"[TripoClient] ⏳ Task {task_id} 완료 대기 중...")

        start_time = time.time()
        elapsed = 0

        while elapsed < max_wait:
            try:
                status_response = self.get_task_status(task_id)

                if status_response.get("code") != 0:
                    print(f"[TripoClient] ❌ Task 조회 실패: {status_response}")
                    return None

                data = status_response.get("data", {})
                task_status = data.get("status")
                progress = data.get("progress", 0)

                print(f"[TripoClient]   상태: {task_status} | 진행률: {progress}%", end="\r")

                if task_status == "success":
                    print(f"\n[TripoClient] ✅ Task {task_id} 완료!")

                    # texture_model은 result.model.url 또는 output.model에서 URL을 가져옴
                    result = data.get("result", {})
                    model_url = result.get("model", {}).get("url") or data.get("output", {}).get("model")

                    if model_url:
                        print(f"[TripoClient] ✅ GLB 모델 URL: {model_url[:100]}...")
                        return model_url
                    else:
                        print(f"[TripoClient] ⚠️ 모델 URL을 찾을 수 없습니다")
                        return None

                elif task_status in ["failed", "error"]:
                    print(f"\n[TripoClient] ❌ Task {task_id} 실패!")
                    return None

                # 비동기 sleep
                await asyncio.sleep(3)

            except Exception as e:
                print(f"\n[TripoClient] ⚠️ 대기 중 오류: {str(e)}")
                await asyncio.sleep(3)

            elapsed = time.time() - start_time

        print(f"\n[TripoClient] ⏱️ Task {task_id} 타임아웃 (최대 {max_wait}초)")
        return None
