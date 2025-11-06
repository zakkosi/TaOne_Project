import os
import requests
from dotenv import load_dotenv

load_dotenv()

TRIPO_API_KEY = os.getenv("TRIPO_API_KEY")
TRIPO_API_URL = "https://api.tripo3d.ai/v2/openapi/task"


class Tripo3DClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or TRIPO_API_KEY
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def texture_existing_model(
        self,
        original_model_task_id: str,
        texture_image_url: str = None,
        texture_prompt_text: str = None,
        model_version: str = "v2.5-20250123",
    ):
        """
        기존 모델에 새 텍스처를 입힘
        Args:
            original_model_task_id: 기존 3D 모델의 task_id
            texture_image_url: 참고용 텍스처 이미지 URL (예: 사진 기반 텍스처)
            texture_prompt_text: 텍스트 기반 텍스처 프롬프트 (선택)
            model_version: 텍스처 생성 모델 버전
        """
        if not (texture_image_url or texture_prompt_text):
            raise ValueError("texture_image_url 또는 texture_prompt_text 중 하나는 필요합니다.")

        texture_prompt = {}
        if texture_image_url:
            texture_prompt["image"] = {"url": texture_image_url}
        elif texture_prompt_text:
            texture_prompt["text"] = texture_prompt_text

        payload = {
            "type": "texture_model",
            "original_model_task_id": original_model_task_id,
            "texture_prompt": texture_prompt,
            "texture": True,
            "pbr": False,
            "bake": False,
            "texture_quality": "detailed",
            "model_version": model_version,
        }

        response = requests.post(TRIPO_API_URL, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def get_task_status(self, task_id: str):
        """Tripo3D에서 현재 태스크 상태 확인"""
        status_url = f"https://api.tripo3d.ai/v2/openapi/task/{task_id}"
        response = requests.get(status_url, headers=self.headers)
        response.raise_for_status()
        return response.json()
