import os
import base64
import uuid
import requests
import time
import asyncio
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.tripo_client import Tripo3DClient
from backend.vision_model import analyze_drawing_text
from Utils.image_cropper import crop_top_section

from dotenv import load_dotenv
load_dotenv()

print("[Main] crop_top_section 임포트 완료")

# --------------------------------------------------------
# 🆕 Task 상태 저장소 (메모리)
# --------------------------------------------------------
processing_tasks = {}  # {task_id: {"status": "...", "progress": 0, "result": {...}}}
model_queue = []  # Unity를 위한 완료된 모델 큐

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
DATA_DIR = os.path.join(BASE_DIR, "../data")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# 정적 파일 마운트
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
# 데이터 폴더도 마운트 (메시 생성용 이미지 접근)
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

@app.get("/")
async def serve_index():
    """index.html 기본 페이지"""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# --------------------------------------------------------
# 🔧 모듈 초기화
# --------------------------------------------------------
tripo_client = Tripo3DClient()

# --------------------------------------------------------
# 🆕 Task 상태 확인 엔드포인트
# --------------------------------------------------------
@app.get("/task_status/{task_id}")
async def task_status(task_id: str):
    """
    프론트엔드가 폴링할 엔드포인트

    응답:
    {
        "task_id": "xxx-xxx",
        "status": "processing",  // queued, processing, done, error
        "progress": 45,          // 0-100
        "result": {...},         // status="done"일 때만
        "error": "...",          // status="error"일 때만
    }
    """
    if task_id not in processing_tasks:
        return {
            "task_id": task_id,
            "status": "not_found",
            "progress": 0,
            "result": None,
            "error": "Task not found"
        }

    task = processing_tasks[task_id]
    return {
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "result": task["result"],
        "error": task["error"],
    }

# --------------------------------------------------------
# 🆕 모든 처리 중인 Task 확인 (디버깅용)
# --------------------------------------------------------
@app.get("/processing_tasks")
async def get_processing_tasks():
    """현재 처리 중인 모든 Task 확인"""
    tasks_summary = {}
    for task_id, task_info in processing_tasks.items():
        tasks_summary[task_id] = {
            "status": task_info["status"],
            "progress": task_info["progress"],
        }
    return {
        "total": len(processing_tasks),
        "tasks": tasks_summary,
    }

# --------------------------------------------------------
# 🆕 Unity 폴링 엔드포인트
# --------------------------------------------------------
@app.get("/get_latest_model")
async def get_latest_model():
    """
    Unity가 주기적으로 호출하는 엔드포인트.
    큐에 데이터가 있으면 반환하고, 없으면 빈 응답.
    """
    if len(model_queue) > 0:
        data = model_queue.pop(0)  # FIFO (First In First Out)
        print(f"[Unity Queue] ✅ 모델 데이터 전달: {data['label']} - {data['child_name']}")
        return {"has_data": True, "data": data}
    else:
        # 큐가 비어있음 (정상 상태)
        return {"has_data": False, "data": None}

# --------------------------------------------------------
# 📊 큐 상태 확인 엔드포인트 (디버깅용)
# --------------------------------------------------------
@app.get("/queue_status")
async def queue_status():
    """현재 큐에 대기 중인 모델 수 확인 (디버깅용)"""
    return {
        "queue_length": len(model_queue),
        "models": [
            {
                "label": m["label"],
                "child_name": m["child_name"],
                "task_id": m["task_id"]
            }
            for m in model_queue
        ]
    }

# --------------------------------------------------------
# 🆕 큐 초기화 엔드포인트 (개발용)
# --------------------------------------------------------
@app.post("/clear_queue")
async def clear_queue():
    """큐를 비웁니다 (개발/디버깅용)"""
    global model_queue
    cleared_count = len(model_queue)
    model_queue = []
    print(f"[Unity Queue] 🗑️ 큐 초기화: {cleared_count}개 항목 제거")
    return {"status": "ok", "cleared_count": cleared_count}

# --------------------------------------------------------
# 📸 /analyze 엔드포인트
# --------------------------------------------------------
@app.post("/analyze")
async def analyze(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    ⚡ 비동기 이미지 분석 (즉시 반환, 백그라운드에서 처리)

    응답:
    {
        "status": "queued",
        "task_id": "xxx-xxx-xxx",
        "status_url": "/task_status/xxx-xxx-xxx",
        "message": "작업이 큐에 추가되었습니다. 상태를 확인해주세요."
    }
    """

    # 고유한 task_id 생성
    task_id = str(uuid.uuid4())

    # 이미지 읽기
    image_bytes = await file.read()

    # Task 상태 초기화
    processing_tasks[task_id] = {
        "status": "queued",
        "progress": 0,
        "result": None,
        "error": None,
        "start_time": time.time(),
    }

    print(f"\n{'='*80}")
    print(f"📥 [QUEUE] Task {task_id} 큐에 추가됨")
    print(f"{'='*80}")

    # 🔥 백그라운드 작업 추가 (즉시 반환!)
    background_tasks.add_task(
        process_image_in_background,
        task_id=task_id,
        image_bytes=image_bytes
    )

    # ✅ 즉시 반환 (0.5초)
    return {
        "status": "queued",
        "task_id": task_id,
        "status_url": f"/task_status/{task_id}",
        "message": "작업이 큐에 추가되었습니다. 상태를 확인해주세요."
    }


async def process_image_in_background(task_id: str, image_bytes: bytes):
    """
    🔄 백그라운드에서 이미지 처리 (병렬로 여러 개 동시 실행)
    """
    try:
        start_time = time.time()
        print(f"\n{'='*80}")
        print(f"🔄 [PROCESS] Task {task_id} 처리 시작")
        print(f"{'='*80}")

        # 상태 업데이트: 처리 중
        processing_tasks[task_id]["status"] = "processing"
        processing_tasks[task_id]["progress"] = 5

        # 1️⃣ 이미지 회전 (90도 시계방향, 크로핑 없음)
        print(f"[Rotate] Task {task_id} 이미지 회전 중 (시계방향 90도)...")
        rotated_bytes = crop_top_section(image_bytes, ratio=0, rotate_cw=90)  # 회전만!
        print(f"[Rotate] ✅ 회전 완료")

        processing_tasks[task_id]["progress"] = 10

        # 2️⃣ Vision 모델로 도안명 & 어린이 이름 추출 (회전된 이미지로!)
        print(f"[Vision] Task {task_id} Vision 분석 중 (회전된 이미지)...")
        image_b64 = base64.b64encode(rotated_bytes).decode("utf-8")  # ← 회전된 이미지!
        vision_result = analyze_drawing_text(image_b64)
        design = vision_result.get("design", "Unknown")
        child_name = vision_result.get("child_name", "Unknown")
        print(f"[Vision] ✅ 도안: {design}, 이름: {child_name}")

        # 🆕 Vision 결과를 즉시 저장 (프론트에서 폴링할 때 보여주기 위함)
        processing_tasks[task_id]["progress"] = 15
        processing_tasks[task_id]["result"] = {
            "label": design,
            "child_name": child_name,
            "model_url": None,
            "processing_time": None,
        }
        print(f"[Task] Task {task_id} 임시 결과 저장: {design}, {child_name}")

        # 3️⃣ 이미지 크로핑 (회전된 이미지에서 텍스트 부분 제거)
        print(f"[Crop] Task {task_id} 이미지 크로핑 중 (상단 15% 제거)...")
        cropped_bytes = crop_top_section(rotated_bytes, ratio=0.15, rotate_cw=0)  # 이미 회전됨, 크로핑만!
        print(f"[Crop] ✅ 크로핑 완료")

        processing_tasks[task_id]["progress"] = 18

        # 크로핑된 이미지 저장 (디버깅용)
        debug_crop_path = os.path.join(UPLOAD_DIR, f"{task_id}_cropped.jpg")
        with open(debug_crop_path, "wb") as f:
            f.write(cropped_bytes)
        print(f"[Crop] 💾 크로핑된 이미지 저장: {debug_crop_path}")

        # 4️⃣ 크로핑된 이미지 업로드
        print(f"[Upload] Task {task_id} 크로핑된 이미지 업로드 중...")
        image_token = tripo_client.upload_image(cropped_bytes, file_type="png")
        if not image_token:
            raise Exception("Image upload failed")
        print(f"[Upload] ✅ 업로드 완료")

        processing_tasks[task_id]["progress"] = 20

        # 5️⃣ image_to_model API 호출
        print(f"[Tripo3D] Task {task_id} image_to_model 요청 중...")
        tripo_result = tripo_client.image_to_model(
            image_token=image_token,
            model_version="v2.5-20250123"
        )
        task_tripo_id = tripo_result.get("data", {}).get("task_id", "unknown")
        print(f"[Tripo3D] ✅ Task 생성: {task_tripo_id}")

        processing_tasks[task_id]["progress"] = 25

        # 6️⃣ Task 완료 대기 (이 부분이 오래 걸림)
        print(f"[Tripo3D] Task {task_id} 3D 생성 대기 중... (1-2분 소요)")
        urls = await tripo_client.wait_for_task_completion(task_tripo_id, max_wait=600)

        if not urls:
            raise Exception("Task completion timeout")

        model_url = urls.get("model_url")
        if not model_url:
            raise Exception("Model URL not found in response")

        print(f"[Tripo3D] ✅ Task 완료!")

        processing_tasks[task_id]["progress"] = 85

        # 7️⃣ GLB 다운로드
        print(f"[Download] Task {task_id} GLB 다운로드 중...")
        r = requests.get(model_url, timeout=30)
        glb_file_size_mb = len(r.content) / 1024 / 1024
        print(f"[Download] ✅ 다운로드 완료 ({glb_file_size_mb:.2f} MB)")

        processing_tasks[task_id]["progress"] = 95

        # 8️⃣ 결과를 Unity 큐에 추가
        payload = {
            "label": design,
            "child_name": child_name,
            "task_id": task_tripo_id,
            "model_url": model_url,
        }
        model_queue.append(payload)
        print(f"[Unity Queue] ✅ Task {task_id} 완료 후 Unity 큐에 추가")

        # 상태 업데이트: 완료
        total_time = time.time() - start_time
        processing_tasks[task_id]["status"] = "done"
        processing_tasks[task_id]["progress"] = 100
        processing_tasks[task_id]["result"] = {
            "label": design,
            "child_name": child_name,
            "model_url": model_url,
            "processing_time": total_time,
        }

        print(f"\n{'='*80}")
        print(f"✅ [COMPLETE] Task {task_id} 처리 완료")
        print(f"⏱️  총 소요 시간: {total_time:.2f}초")
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"\n{'='*80}")
        print(f"❌ [ERROR] Task {task_id} 처리 실패")
        print(f"오류: {str(e)}")
        print(f"{'='*80}\n")

        processing_tasks[task_id]["status"] = "error"
        processing_tasks[task_id]["progress"] = 0
        processing_tasks[task_id]["error"] = str(e)
