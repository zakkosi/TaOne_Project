# Unity Integration Guide

## 📋 개요

이 프로젝트는 아이들의 그림을 3D 모델로 변환하는 인터랙티브 전시 시스템입니다.

**핵심 구조**:
1. **프론트엔드**: 아이 그림 촬영
2. **백엔드**: GPT Vision으로 분석 → Tripo3D로 3D 모델 생성
3. **Unity**: 생성된 GLB 모델 로드 및 표시

---

## 🎮 Unity 폴링 큐 시스템

### 작동 원리

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 프론트엔드에서 그림 촬영                                   │
│    ↓                                                         │
│ 2. 백엔드 /analyze 엔드포인트 호출                             │
│    - Vision 분석                                            │
│    - Tripo3D로 텍스처 적용                                    │
│    ↓                                                         │
│ 3. 결과를 메모리 큐에 저장 (FIFO)                             │
│    ↓                                                         │
│ 4. Unity가 주기적으로 폴링 (/get_latest_model)                │
│    ↓                                                         │
│ 5. 큐에서 데이터 가져가기                                     │
│    ↓                                                         │
│ 6. GLB 파일 다운로드 및 표시                                 │
└─────────────────────────────────────────────────────────────┘
```

### 백엔드 엔드포인트

```python
# 1. 최신 모델 데이터 가져오기 (Unity가 주기적으로 호출)
GET /get_latest_model
응답:
{
  "has_data": true,
  "data": {
    "label": "spaceship",
    "child_name": "민준",
    "task_id": "abc123...",
    "mesh_id": "xyz789...",
    "texture_url": "http://localhost:8000/static/uploaded/{task_id}_texture.glb"
  }
}

# 2. 현재 큐 상태 확인 (디버깅용)
GET /queue_status
응답:
{
  "queue_length": 2,
  "models": [
    {"label": "locket", "child_name": "지은", "task_id": "..."},
    {"label": "spaceship", "child_name": "준호", "task_id": "..."}
  ]
}

# 3. 큐 초기화 (개발용)
POST /clear_queue
```

---

## 🎯 메시 관리

### 원본 메시 다운로드

Tripo3D에서 생성된 3개의 기본 메시가 있습니다:

```
frontend/meshes/
├── spaceship.glb    (14.14 MB)
├── locket.glb       (13.99 MB)
└── character.glb    (13.78 MB)
```

**다운로드 방법**:
```bash
python download_original_meshes.py
```

**원리**:
1. `.env`에서 Task ID 읽기
2. Tripo3D API로 Task 상태 확인
3. GLB URL 추출
4. 다운로드 후 `frontend/meshes/`에 저장

### 메시 타입별 응답 구조

**image_to_model** (기본 메시 생성):
```json
{
  "result": {
    "pbr_model": {
      "type": "glb",
      "url": "https://..."
    },
    "rendered_image": { "type": "webp", "url": "https://..." }
  },
  "output": {
    "pbr_model": "https://...",
    "rendered_image": "https://..."
  }
}
```

**texture_model** (텍스처 적용):
```json
{
  "result": {
    "model": {
      "type": "glb",
      "url": "https://..."
    },
    "rendered_image": { "type": "webp", "url": "https://..." }
  },
  "output": {
    "model": "https://...",
    "rendered_image": "https://..."
  }
}
```

---

## 🎨 Unity 구현

### 1️⃣ glTFast 설치

Package Manager에서:
```
com.unity.cloud.gltfast
```

> 선택사항: Draco 압축 필요시 `com.unity.cloud.gltfast.draco` 설치

### 2️⃣ 폴링 스크립트 (C#)

```csharp
using UnityEngine;
using UnityEngine.Networking;
using System.Collections;

public class ModelPoller : MonoBehaviour
{
    private string backendUrl = "http://localhost:8000";
    private float pollInterval = 1f;  // 1초마다 폴링

    void Start()
    {
        StartCoroutine(PollForModels());
    }

    IEnumerator PollForModels()
    {
        while (true)
        {
            using (UnityWebRequest request = UnityWebRequest.Get(
                $"{backendUrl}/get_latest_model"))
            {
                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    string json = request.downloadHandler.text;
                    ModelResponse response = JsonUtility.FromJson<ModelResponse>(json);

                    if (response.has_data)
                    {
                        Debug.Log($"✅ 모델 수신: {response.data.label} by {response.data.child_name}");
                        // 모델 로드
                        StartCoroutine(LoadModel(response.data));
                    }
                }
                else
                {
                    Debug.LogError($"❌ 폴링 실패: {request.error}");
                }
            }

            yield return new WaitForSeconds(pollInterval);
        }
    }

    IEnumerator LoadModel(ModelData data)
    {
        // glTFast로 GLB 로드
        var gltfImport = new GLTFast.GltfImport();
        bool success = await gltfImport.Load(data.texture_url);

        if (success)
        {
            GameObject instance = new GameObject($"Model_{data.task_id}");
            success = await gltfImport.InstantiateAsync(instance.transform);

            if (success)
            {
                Debug.Log($"✅ 모델 로드 완료: {data.label}");
            }
        }

        yield return null;
    }
}

[System.Serializable]
public class ModelResponse
{
    public bool has_data;
    public ModelData data;
}

[System.Serializable]
public class ModelData
{
    public string label;
    public string child_name;
    public string task_id;
    public string mesh_id;
    public string texture_url;
}
```

### 3️⃣ 원본 메시 로드 (선택)

```csharp
public class MeshLoader : MonoBehaviour
{
    private GLTFast.GltfImport gltfImport;

    public async void LoadOriginalMesh(string meshPath)
    {
        // 예: "Assets/Meshes/spaceship.glb"
        gltfImport = new GLTFast.GltfImport();
        bool success = await gltfImport.Load(meshPath);

        if (success)
        {
            GameObject instance = new GameObject("OriginalMesh");
            await gltfImport.InstantiateAsync(instance.transform);
        }
    }
}
```

---

## 🔄 워크플로우

### 프론트엔드 사용자 관점

```
1. 아이가 화면에 그림을 그림
2. 캡처 버튼 클릭
3. 이미지 업로드 → /analyze 호출
4. 처리 중... (약 94초)
5. Unity에서 3D 모델 표시
```

### 백엔드 처리 흐름

```
/analyze 엔드포인트
├─ 1. 이미지 로드
├─ 2. Vision 분석 (도안명, 아이 이름)
├─ 3. 이미지 크롭 (상단 5cm 제거)
├─ 4. Tripo3D 업로드 (multipart/form-data)
├─ 5. Tripo3D texture_model API 호출
├─ 6. Task 완료 대기 (polling, 최대 10분)
├─ 7. GLB 다운로드 및 로컬 저장
├─ 8. 결과를 큐에 추가
└─ 9. 브라우저 응답
```

---

## 🧪 테스트

### 1️⃣ 백엔드 테스트

```bash
# 큐 상태 확인
curl http://localhost:8000/queue_status

# 큐 초기화
curl -X POST http://localhost:8000/clear_queue

# 폴링 테스트 (데이터 없음)
curl http://localhost:8000/get_latest_model
# 응답: {"has_data": false, "data": null}
```

### 2️⃣ 통합 테스트

```bash
# 1. 이미지 업로드 (test.jpg 필요)
curl -X POST \
  -F "file=@test.jpg" \
  http://localhost:8000/analyze

# 2. 큐 상태 확인
curl http://localhost:8000/queue_status

# 3. Unity에서 /get_latest_model 호출하여 데이터 가져가기
curl http://localhost:8000/get_latest_model

# 4. 큐가 비워짐
curl http://localhost:8000/queue_status
# 응답: {"queue_length": 0, "models": []}
```

---

## 📊 시스템 성능

| 단계 | 소요 시간 |
|------|----------|
| Vision 분석 | ~2초 |
| 이미지 크롭 | ~1초 |
| Tripo3D 업로드 | ~3초 |
| Tripo3D 텍스처 생성 | ~60초 |
| GLB 다운로드 | ~3초 |
| **전체** | **~69-94초** |

---

## 🐛 트러블슈팅

### 문제: Vision 분석이 "Unknown" 반환

**원인**: GPT-4o-mini의 응답이 JSON 형식이 아님

**해결**:
- `vision_model.py`에서 `temperature=0` 설정
- JSON 파싱 후 정규식 폴백 추가
- 프롬프트에서 JSON 형식 명시

### 문제: Tripo3D API 400 오류

**원인**: 잘못된 payload 구조

**해결**:
- Upload API로 먼저 이미지 업로드
- 획득한 image_token을 texture_prompt에 사용
- Payload 구조 정확히 따르기

### 문제: GLB 파일을 찾을 수 없음

**원인**: Task 응답 구조가 다름 (image_to_model vs texture_model)

**해결**: `tripo_client.py`에서 여러 경로 확인
```python
model_url = (
    result.get("model", {}).get("url")        # texture_model
    or result.get("pbr_model", {}).get("url") # image_to_model
    or output.get("model")                    # fallback
    or output.get("pbr_model")                # fallback
)
```

---

## 📝 환경 변수 (.env)

```
TRIPO_API_KEY=tsk_...
OPENAI_API_KEY=sk-proj-...

MESH_SPACESHIP_TASK_ID=e83df609-...
MESH_LOCKET_TASK_ID=b8d007c4-...
MESH_CHARACTER_TASK_ID=9a0677e8-...
```

---

## 🚀 배포

### 프로덕션 체크리스트

- [ ] CORS 설정 검토 (현재: allow_origins=["*"])
- [ ] 파일 저장 경로 확인
- [ ] Ngrok URL 자동 감지 테스트
- [ ] GLB 파일 용량 관리 (cleanup 스크립트 필요)
- [ ] Error logging 강화
- [ ] Rate limiting 추가

---

## 📚 참고

- [Tripo3D API 문서](https://www.tripo3d.ai/docs)
- [glTFast 문서](https://github.com/atteneder/glTFast)
- [Unity WebRequest 가이드](https://docs.unity3d.com/ScriptReference/Networking.UnityWebRequest.html)

---

**마지막 업데이트**: 2025-11-08
