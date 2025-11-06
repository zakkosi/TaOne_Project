# backend/vision_model.py
import os
from openai import OpenAI
import base64
import re

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def analyze_drawing_text(image_b64: str) -> dict:
    """
    그림의 상단 텍스트를 읽어 도안명과 아이 이름을 추출.
    Returns:
        dict: {"design": "Spaceship", "child_name": "Minjun"}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an OCR and understanding model that reads the top of a child's drawing. Extract exactly two pieces of information: the design type (e.g., Spaceship, Locket, Single Character) and the child's name written at the top.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "이 그림 상단에 적힌 도안명과 아이 이름을 각각 알려줘."},
                    {"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_b64}"}
                ],
            },
        ],
        max_tokens=50,
    )

    text = response.choices[0].message.content.strip()

    # 간단한 정규식으로 두 값 추출 시도
    design, name = None, None
    m1 = re.search(r"(spaceship|locket|single character)", text, re.I)
    if m1:
        design = m1.group(1).title()

    m2 = re.search(r"name[:：]?\s*([A-Za-z가-힣]+)", text)
    if m2:
        name = m2.group(1).strip().title()

    result = {
        "design": design or "Unknown",
        "child_name": name or "Unknown",
    }

    print(f"[VisionModel] 도안: {result['design']}, 아이 이름: {result['child_name']}")
    return result
