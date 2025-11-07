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
            "content": (
                "너는 이미지 안의 텍스트를 정확히 읽는 OCR 분석가야. "
                "이미지의 상단에 글씨가 거꾸로 되어 있거나 작게 써있을 수 있으니, "
                "필요하면 이미지를 회전시켜서 모든 글씨를 읽어야 해. "
                "반드시 다음 JSON 형식으로만 응답해: "
                '{"design": "Spaceship", "child_name": "Minjun"} '
                "도안명은 spaceship, locket, single character 중 하나만 가능해."
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "이 그림의 텍스트에서 도안명과 어린이 이름을 추출해. "
                        "다음 형식의 JSON만 반환해. 다른 글은 절대 쓰지마. "
                        '{"design": "...", "child_name": "..."}'
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                },
            ],
        },
    ],
    max_tokens=200,
    temperature=0,  # 더 결정적인 응답
    )

    text = response.choices[0].message.content.strip()
    print(f"[VisionModel] GPT 원본 응답: {text}")

    design, name = None, None

    # 1️⃣ 먼저 JSON 파싱 시도 (GPT가 정확한 JSON을 반환할 가능성)
    try:
        import json
        json_match = re.search(r'\{[^}]+\}', text)
        if json_match:
            json_str = json_match.group(0)
            parsed = json.loads(json_str)
            design = parsed.get("design")
            name = parsed.get("child_name")
            print(f"[VisionModel] JSON 파싱 성공: design={design}, name={name}")
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"[VisionModel] JSON 파싱 실패: {e}")

    # 2️⃣ JSON 파싱 실패 시 정규식으로 폴백
    if not design:
        m1 = re.search(r"(spaceship|locket|single\s+character)", text, re.I)
        if m1:
            design = m1.group(1).strip().lower()
            if design == "single character":
                design = "Single Character"
            else:
                design = design.title()
            print(f"[VisionModel] 정규식으로 도안명 추출: {design}")

    if not name:
        # 다양한 이름 패턴 시도
        patterns = [
            r"name[:：\s]+([A-Za-z가-힣\s]+?)(?:\n|$)",  # name: 다음
            r"child_name[:：\s]+([A-Za-z가-힣\s]+?)(?:\n|$)",  # child_name: 다음
            r"([A-Za-z가-힣]+)\s*(?:as\s+)?(?:name|child)",  # 이름이 앞에 오는 경우
            r"어린이\s*:\s*([A-Za-z가-힣\s]+?)(?:\n|$)",  # 어린이: 패턴
            r"(?:^|\n)([A-Za-z가-힣]{2,})\s*(?:\n|$)",  # 2글자 이상의 단어 (이름일 가능성)
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if m:
                name = m.group(1).strip().title()
                print(f"[VisionModel] 정규식으로 이름 추출: {name}")
                break

    result = {
        "design": design or "Unknown",
        "child_name": name or "Unknown",
    }

    print(f"[VisionModel] 최종 결과 - 도안: {result['design']}, 아이 이름: {result['child_name']}")
    return result
