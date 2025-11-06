import os
import base64
import uuid
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.tripo_client import Tripo3DClient
from backend.vision_model import analyze_drawing_text
from backend.unity_receiver import send_to_unity
from Utils.image_cropper import crop_top_section

# --------------------------------------------------------
# ⚙️ Ngrok URL 자동 감지
# --------------------------------------------------------
def get_ngrok_url() -> str:
    """
    로컬에서 실행 중인 ngrok의 public URL을 자동으로 가져옴.
    ngrok이 꺼져 있으면 localhost로 fallback.
    """
    try:
        resp = requests.get("http://127.0.0.1:4040/api/tunnels")
        data = resp.json()
        tunnels = data.get("tunnels", [])
        if tunnels:
            url = tunnels[0]["public_url"]
            print(f"[Ngrok] 자동 감지된 주소: {url}")
            return url
        else:
            print("[Ngrok] 터널 정보를 찾지 못했습니다. localhost로 대체합니다.")
    except Exception as e:
        print(f"[Ngrok] URL 자동 감지 실패: {e}")
    return "http://localhost:8000"

# --------------------------------------------------------
# 🌐 FastAPI 기본 설정
# --------------------------------------------------------
app = FastAPI(title="Digital Interactive Exhibition Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------
# 📁 폴더 경로 설정
# --------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")
UPLOAD_DIR = os.path.join(FRONTEND_DIR, "uploaded")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# 정적 파일 마운트
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
async def serve_index():
    """index.html 기본 페이지"""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# --------------------------------------------------------
# 🔧 모듈 초기화
# --------------------------------------------------------
tripo_client = Tripo3DClient()

# --------------------------------------------------------
# 📸 /analyze 엔드포인트
# --------------------------------------------------------
@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    프론트엔드에서 이미지를 받아서:
    1. GPT Vision으로 도안명 + 아이 이름 추출
    2. 이미지 상단 3cm 잘라서 저장
    3. Ngrok 공개 URL로 Tripo3D에 전달
    4. 결과를 Unity에 전송
    """

    # 1️⃣ 이미지 읽기
    image_bytes = await file.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    # 2️⃣ Vision 모델로 도안명 & 어린이 이름 추출
    vision_result = analyze_drawing_text(image_b64)
    design = vision_result.get("design", "Unknown")
    child_name = vision_result.get("child_name", "Unknown")
    print(f"[Vision] 도안: {design}, 이름: {child_name}")

    # 3️⃣ 상단 3cm 잘라내기
    cropped_image_bytes = crop_top_section(image_bytes)

    # 4️⃣ 잘린 이미지 로컬 저장
    filename = f"{uuid.uuid4().hex}.jpg"
    local_path = os.path.join(UPLOAD_DIR, filename)
    with open(local_path, "wb") as f:
        f.write(cropped_image_bytes)

    # 5️⃣ Ngrok 공개 URL 생성
    NGROK_BASE = get_ngrok_url()
    texture_image_url = f"{NGROK_BASE}/static/uploaded/{filename}"
    print(f"[Server] Tripo3D에 전달할 이미지 URL: {texture_image_url}")

    # 6️⃣ 도안별 Mesh 매핑
    mesh_map = {
    "spaceship": os.getenv("MESH_SPACESHIP_TASK_ID"),
    "locket": os.getenv("MESH_LOCKET_TASK_ID"),
    "single character": os.getenv("MESH_CHARACTER_TASK_ID"),
    }
    
    mesh_id = mesh_map.get(design.lower(), "mesh_spaceship_task_id")

    # 7️⃣ Tripo3D 호출 (이미지 URL 입력)
    try:
        tripo_result = tripo_client.texture_existing_model(
            original_model_task_id=mesh_id,
            texture_image_url=texture_image_url,
        )
        task_id = tripo_result.get("task_id", "unknown")
        result_url = tripo_result.get("result", {}).get("download_url", None)
        print(f"[Tripo3D] task_id={task_id}, result_url={result_url}")

        # ✅ 테스트용: 결과 zip 파일 로컬 저장
        if result_url:
            r = requests.get(result_url)
            output_zip = os.path.join(UPLOAD_DIR, f"{task_id}_result.zip")
            with open(output_zip, "wb") as f:
                f.write(r.content)
            print(f"[Local Save] 결과 메쉬 및 텍스처 저장 완료: {output_zip}")

    except Exception as e:
        print(f"[Tripo3D] API 오류: {e}")
        task_id, result_url = "error", None
        # 8️⃣ Unity로 전송

    payload = {
        "label": design,
        "child_name": child_name,
        "task_id": task_id,
        "mesh_id": mesh_id,
        "texture_url": result_url or texture_image_url,  # fallback
    }

    try:
        await send_to_unity(payload)
        print(f"[Unity] 전송 완료: {payload}")
    except Exception as e:
        print(f"[Unity] 전송 실패: {e}")

    # 9️⃣ 브라우저 응답
    return {
        "status": "ok",
        "label": design,
        "child_name": child_name,
        "task_id": task_id,
        "texture_url": result_url or texture_image_url,
    }
