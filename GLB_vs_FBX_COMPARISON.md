# GLB vs FBX 비교

## 🔍 기본 비교

| 항목 | GLB | FBX |
|------|-----|-----|
| **확장자** | .glb | .fbx |
| **형식** | 이진(Binary) | 이진(Binary) |
| **표준** | glTF 2.0 (Khronos) | Autodesk 독점 |
| **파일 크기** | 작음 (압축 포함) | 중간~큼 |
| **메시 데이터** | ✅ 포함 | ✅ 포함 |
| **머티리얼** | PBR 지원 | 제한적 |
| **텍스처** | 임베드 가능 | 참조만 |
| **애니메이션** | ✅ 지원 | ✅ 지원 |
| **모션 캡처** | 제한적 | ✅ 우수 |
| **지원 엔진** | Unity, Unreal, 웹 | Unity, Unreal, Maya, Blender |

---

## 🎮 Unity에서의 사용

### GLB 사용
```csharp
// glTFast 필요
using GLTFast;

var gltfImport = new GltfImport();
await gltfImport.Load("model.glb");
await gltfImport.InstantiateAsync(parent);
// → 완성된 GameObject (메시, 머티리얼, 텍스처 모두 포함)
```

**장점**:
- ✅ 즉시 완성된 모델 사용 가능
- ✅ 패키지 하나로 모든 것 포함
- ✅ 런타임 로드 최적화됨

**단점**:
- ❌ 메시와 텍스처 분리 어려움
- ❌ 텍스처만 교체 불가능 (전체 다시 로드 필요)

---

### FBX 사용
```csharp
// Unity 에디터에서 미리 임포트
// Assets/Models/model.fbx → Inspector에서 설정
// → prefab 생성

// 런타임에는
var prefab = Resources.Load<GameObject>("Models/model");
var instance = Instantiate(prefab);
// → 미리 설정된 프리팹 사용
```

**장점**:
- ✅ 에디터에서 완전히 제어 가능
- ✅ 메시와 머티리얼 분리 가능
- ✅ 런타임에 머티리얼만 교체 가능

**단점**:
- ❌ 사전 임포트 필요 (에디터 작업)
- ❌ 프로젝트 빌드 크기 증가

---

## 🎯 우리의 상황에 맞는 것은?

### 현재 우리의 워크플로우

```
1️⃣ 기본 메시 3개:
   - Tripo3D에서 다운로드 → spaceship.glb, locket.glb, character.glb
   - 이걸 Unity 프리팹으로 만들기

2️⃣ 런타임에 텍스처 적용:
   - 아이 그림 업로드
   - Tripo3D texture_model API
   - 결과 GLB 다운로드
   - 프리팹에 텍스처만 입히기
```

### GLB로 남기는 경우

```
✅ 장점:
- 변환 작업 없음
- 그대로 프리팹으로 변환 가능
- 런타임에 glTFast로 로드

❌ 단점:
- 메시/텍스처 분리 어려움
- 매번 완전한 GLB 다운로드 (14MB)
- 메모리 사용량 많음
```

**코드 예**:
```csharp
// 매번 전체 GLB 다운로드
var gltfImport = new GltfImport();
await gltfImport.Load("http://backend/models/spaceship_with_texture.glb");
await gltfImport.InstantiateAsync(parent);
```

### FBX로 변환하는 경우

```
✅ 장점:
- 메시와 머티리얼 완전 분리
- 프리팹 재사용 (메시는 고정)
- 텍스처만 교체 (네트워크 효율)
- Unity 방식과 일치

❌ 단점:
- 변환 작업 필요 (GLB → FBX)
- 에디터에서 임포트 작업
- 프로젝트 파일 크기 증가
```

**코드 예**:
```csharp
// 메시 프리팹 (이미 에디터에서 만들어짐)
var meshPrefab = Resources.Load<GameObject>("Prefabs/Spaceship");
var instance = Instantiate(meshPrefab);

// 텍스처만 다운로드 & 적용 (경량)
var textureUrl = "http://backend/textures/child_drawing.png";
using (var req = UnityWebRequest.Get(textureUrl))
{
    yield return req.SendWebRequest();
    var texture = ((DownloadHandlerTexture)req.downloadHandler).texture;
    var renderer = instance.GetComponent<MeshRenderer>();
    renderer.material.SetTexture("_MainTex", texture);
}
```

---

## 📊 성능 비교

### 파일 크기
```
원본 메시 (spaceship):
- GLB: 14.14 MB
- FBX: 약 15-20 MB (변환 후)

텍스처 적용 결과:
- GLB (전체): 14.14 MB
- 텍스처만 (PNG): 2-5 MB
```

### 네트워크 사용량 (런타임)

**GLB 방식**:
```
매 아이마다 14MB 다운로드
10명 = 140MB
```

**FBX + 텍스처 분리 방식**:
```
메시: 1회만 (에디터에서)
텍스처: 3-5MB × 아이 수
10명 = 30-50MB
```

### 로딩 시간

**GLB 방식**:
- 네트워크: ~2초
- glTFast 파싱: ~1초
- 렌더링 준비: ~1초
- **총**: ~4초

**FBX + 텍스처 방식**:
- 프리팹 인스턴스: ~0.1초
- 텍스처 다운로드: ~1초
- 머티리얼 적용: ~0.5초
- **총**: ~1.6초

---

## 🔄 Tripo3D에서 FBX 받기

### 방법 1: 현재 대로 GLB 받고 변환

```bash
# 온라인 도구 사용
# https://products.aspose.app/3d/conversion/glb-to-fbx

# 또는 Blender 사용
# 1. spaceship.glb 열기
# 2. File > Export as > spaceship.fbx
# 3. 설정 확인 후 내보내기
```

### 방법 2: Tripo3D API에 FBX 요청 파라미터 추가?

우리가 찾아본 API 응답에는 형식 지정 옵션이 없습니다:
```python
# 현재 API
response = requests.post(TRIPO_API_URL, json={
    "type": "texture_model",
    "original_model_task_id": mesh_id,
    "texture_prompt": {...},
    # ❌ "output_format": "fbx" 같은 파라미터 없음
})
```

**대안**: Tripo3D 웹 대시보드에서 FBX 다운로드 옵션이 있는지 확인
- 웹에서는 다양한 형식 선택 가능할 수 있음
- API에서는 제한적일 수 있음

---

## 💡 최종 권장안

### 상황별 선택

#### 상황 1: 개발 빨리 끝내고 싶음
**→ GLB 그대로 사용**
```
✅ 변환 작업 없음
✅ 지금 바로 프리팹 생성 가능
✅ glTFast로 완성된 모델 로드
❌ 네트워크 효율 낮음 (14MB × 아이 수)
```

#### 상황 2: 최적화된 시스템 원함
**→ GLB → FBX 변환 → 프리팹**
```
✅ 메시/텍스처 분리 (네트워크 효율)
✅ 텍스처만 교체 가능
✅ Unity 방식과 일치
❌ 변환 작업 필요 (1-2시간)
```

#### 상황 3: 최고의 네트워크 효율
**→ Tripo3D에서 렌더링된 이미지만 받기**
```
✅ 가장 경량 (이미지 파일만)
✅ 네트워크 최소 (1-2MB)
❌ 3D 상호작용 불가능 (정적 이미지)
```

---

## 🎯 우리 프로젝트에 최적인 선택

### Phase 1 (지금): GLB 사용
```
1. 원본 메시 3개 (GLB) → Unity 프리팹으로 변환
2. 텍스처 결과도 GLB → glTFast로 로드
3. 시스템 완성

장점: 빠른 개발
```

### Phase 2 (나중): FBX로 최적화 (선택)
```
1. GLB → FBX 변환
2. 메시와 머티리얼 분리
3. 네트워크 효율 개선

장점: 성능 최적화
```

---

## 🚀 구체적인 액션 아이템

### 지금 해야 할 것 (GLB 방식)

```python
# 1. 원본 메시 3개 다운로드 ✅ (이미 완료)
# frontend/meshes/spaceship.glb 등

# 2. Unity에 임포트
#    Assets/Meshes/spaceship.glb 복사
#    → 프리팹 생성

# 3. 런타임에 텍스처 적용
var gltfImport = new GltfImport();
await gltfImport.Load(
    "http://localhost:8000/static/uploaded/{task_id}_texture.glb"
);
await gltfImport.InstantiateAsync(parent);
```

### 만약 FBX가 필요하면 (선택)

```bash
# 1. Blender 설치 (무료)
# 2. spaceship.glb 열기
# 3. spaceship.fbx로 내보내기
# 4. Unity에 임포트
```

---

## 결론

| 방식 | 개발 난이도 | 성능 | 네트워크 | 추천 |
|------|-----------|------|---------|------|
| **GLB 그대로** | ⭐ | ⭐⭐ | ⭐ | ✅ 지금 |
| **GLB → FBX 변환** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⏳ 나중 |
| **이미지만** | ⭐ | ⭐ | ⭐⭐⭐ | ❌ 3D 불가 |

**현재 상황에서는 GLB 그대로 사용하는 것을 권장합니다.**
- 이미 다운로드 완료
- 변환 작업 불필요
- 시스템 완성 속도 빠름
- 나중에 필요하면 FBX로 최적화 가능

