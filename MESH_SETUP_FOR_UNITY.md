# Unity에 메시 세팅하기

## 상황 정리

### 기존 계획
```
Unity 에디터
├─ Spaceship 프리팹 (메시O, 머티리얼 없음)
├─ Locket 프리팹
└─ Character 프리팹
        ↓
런타임에 텍스처만 다운로드해서 입히기
```

### 현재 상황
```
우리가 Tripo3D에서 다운로드한 메시:
├─ spaceship.glb (14.14 MB) ← 이미 텍스처 적용된 완성 모델
├─ locket.glb (13.99 MB)
└─ character.glb (13.78 MB)

이 메시는:
✅ GLB 형식 (FBX 아님)
✅ PBR 재질 포함 (metallic, roughness 등)
✅ 텍스처 이미 포함됨
```

---

## 🤔 선택지

### 옵션 1: GLB 그대로 사용 (권장 - 간단함)

**장점**:
- 가장 간단
- Tripo3D의 완성 모델을 그대로 사용
- glTFast로 바로 로드 가능

**단점**:
- 텍스처를 교체할 때마다 새로운 GLB 전체 다운로드 필요
- 메시는 고정, 텍스처만 변경할 수 없음

**구현**:
```csharp
var gltfImport = new GLTFast.GltfImport();
await gltfImport.Load("http://localhost:8000/static/uploaded/{task_id}_texture.glb");
await gltfImport.InstantiateAsync(parent);
```

---

### 옵션 2: GLB → FBX 변환 후 프리팹 만들기

**장점**:
- Unity 에디터에서 완전히 제어 가능
- 메시와 텍스처를 분리할 수 있음

**단점**:
- 변환 과정 필요
- 파일 크기 증가 (GLB 14MB → FBX는 더 클 수 있음)

**방법**:
1. GLB를 FBX로 변환 (온라인 도구 또는 Blender 사용)
2. Unity에 FBX 임포트
3. 메시만 사용하는 프리팹 만들기
4. 머티리얼은 기본값 또는 빈 상태로

---

### 옵션 3: GLB 메시 추출 후 프리팹 만들기 (가장 깔끔)

**장점**:
- 메시와 텍스처 완전 분리
- 런타임에 텍스처만 교체 가능
- Unity 방식에 맞음

**단점**:
- 약간의 처리 필요

**방법**:
1. GLB 파일을 Unity 프로젝트에 임포트
2. Mesh 자체만 추출
3. 텍스처 없는 프리팹 만들기
4. 런타임에 텍스처 입히기

---

## 🎯 추천: 옵션 3 (메시 분리)

### 단계별 설정

#### 1단계: GLB를 Unity 프로젝트에 임포트

```
Assets/Meshes/
├── spaceship.glb          ← Unity가 자동으로 처리
├── spaceship.prefab       ← 우리가 생성
└── ...
```

**Unity에서**:
1. `frontend/meshes/spaceship.glb` → `Assets/Meshes/` 복사
2. Inspector에서 임포트 설정:
   - Model: ✅ Meshes
   - Materials: ❌ (비활성화)
   - Animations: ❌ (필요 없으면)

#### 2단계: 메시만 사용하는 프리팹 만들기

```csharp
// Assets/Scripts/MeshSetup.cs
using UnityEngine;
using GLTFast;

public class MeshSetup : MonoBehaviour
{
    // Unity 에디터에서 설정:
    public Mesh spaceshipMesh;  // spaceship.glb의 메시
    public Mesh locketMesh;
    public Mesh characterMesh;

    // 또는 Resources 폴더에서 로드
    void LoadMeshes()
    {
        spaceshipMesh = Resources.Load<Mesh>("Meshes/spaceship");
        // ...
    }

    // 런타임에 메시 적용
    void ApplyMesh(string designType)
    {
        var meshFilter = gameObject.GetComponent<MeshFilter>();

        switch(designType.ToLower())
        {
            case "spaceship":
                meshFilter.mesh = spaceshipMesh;
                break;
            case "locket":
                meshFilter.mesh = locketMesh;
                break;
            case "character":
                meshFilter.mesh = characterMesh;
                break;
        }
    }

    // 런타임에 텍스처 입히기
    void ApplyTexture(Texture2D diffuseTexture)
    {
        var renderer = gameObject.GetComponent<MeshRenderer>();
        var material = new Material(Shader.Find("Standard"));
        material.SetTexture("_MainTex", diffuseTexture);
        renderer.material = material;
    }
}
```

#### 3단계: 프리팹 생성

```
1. Hierarchy에 빈 GameObject 생성 ("Spaceship")
2. MeshFilter 추가
3. MeshRenderer 추가 (Material 없음)
4. Prefab으로 드래그 → Assets/Prefabs/
```

---

## 🔄 런타임 워크플로우

```csharp
public class ModelDisplay : MonoBehaviour
{
    private GameObject currentModel;
    private GLTFast.GltfImport textureImport;

    // 백엔드에서 받은 데이터
    public async void DisplayModel(ModelData data)
    {
        // 1. 메시 타입에 따라 프리팹 인스턴스 생성
        var prefabPath = $"Prefabs/{data.label}";
        var meshPrefab = Resources.Load<GameObject>(prefabPath);
        currentModel = Instantiate(meshPrefab);

        // 2. 텍스처 다운로드 및 적용
        if (!string.IsNullOrEmpty(data.texture_url))
        {
            textureImport = new GLTFast.GltfImport();
            bool success = await textureImport.Load(data.texture_url);

            if (success)
            {
                // 현재 모델의 렌더러에 텍스처 적용
                ApplyDownloadedTexture(currentModel, textureImport);
            }
        }
    }

    void ApplyDownloadedTexture(GameObject model, GLTFast.GltfImport import)
    {
        var renderer = model.GetComponent<MeshRenderer>();
        // glTFast에서 추출한 머티리얼을 적용
        if (import.GetMaterial(0) is Material material)
        {
            renderer.material = material;
        }
    }
}
```

---

## ⚠️ 주의사항

### 현재 우리의 텍스처 파일 형식

Tripo3D texture_model API가 반환하는 GLB는:
- ✅ 메시 포함
- ✅ 텍스처 포함 (이미 메시에 입혀있음)
- ❌ 메시만 분리 불가능 (메시와 텍스처가 하나의 GLB)

### 따라서 현실적인 선택지:

**옵션 A: 원본 메시만 사용 (권장)**
```
1. 원본 메시 (spaceship.glb 등) → Unity 프리팹
2. Tripo3D texture_model 결과 → 텍스처 파일로 따로 뽑아서 적용
```

**옵션 B: 전체 GLB 사용 (더 간단)**
```
1. 계획 변경
2. 매번 완성된 GLB 전체를 다운로드해서 표시
3. 메시 분리 안 함
```

---

## 🎯 현재 상황에서 최선의 방법

### 문제점
Tripo3D texture_model API가 반환하는 GLB는:
- 메시와 텍스처가 이미 합쳐져 있음
- 따로 분리 불가능
- 매번 새 GLB 다운로드 필요

### 해결책: Tripo3D API 변경

**texture_model** 대신 **render** API 사용:
```python
# 현재 (메시+텍스처 포함):
tripo_client.texture_existing_model(...)  # 전체 GLB 반환

# 개선안 (텍스처만):
# render API → PNG 이미지 반환 (optional)
# 기존 메시 (원본) + 텍스처 이미지 분리
```

---

## 💡 최종 권장안

### Phase 1: 지금 당장
원본 메시 3개를 Unity 프리팹으로 만들기:
```
Assets/Prefabs/
├── Spaceship.prefab (원본 메시만, 텍스처 없음)
├── Locket.prefab
└── Character.prefab
```

### Phase 2: 런타임
```
1. 백엔드에서 메시 ID 받기
2. 해당 프리팹 인스턴스 생성
3. Tripo3D에서 텍스처 이미지만 다운로드
4. 프리팹 머티리얼에 텍스처 입히기
```

### Phase 3: Tripo3D API 개선 (선택)
Render API를 사용해서 이미지만 반환받기

---

## 🔧 실제 구현 (Phase 1)

### Unity 에디터에서

```
1. Assets/Meshes/ 폴더 생성
2. spaceship.glb, locket.glb, character.glb 복사
3. 각 GLB 선택 → Inspector:
   - Model > Meshes: ✅
   - Model > Materials: ❌
   - Save → Apply
4. Mesh 추출:
   - glb 선택 → Inspector에서 Mesh 항목 우클릭 → "Extract Mesh"
   - Assets/Meshes/spaceship_mesh.asset 생성
5. 프리팹 생성:
   - 빈 GameObject 생성 (이름: "Spaceship")
   - MeshFilter 추가 → Mesh에 "spaceship_mesh" 할당
   - MeshRenderer 추가 (Material 비워두기)
   - Prefabs 폴더로 드래그 → 프리팹 생성
```

### C# 스크립트로 자동화 (Optional)

```csharp
#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using System.IO;

public class MeshSetupTool
{
    [MenuItem("Tools/Setup Meshes")]
    public static void SetupMeshes()
    {
        var meshTypes = new[] { "spaceship", "locket", "character" };

        foreach (var type in meshTypes)
        {
            var glbPath = $"Assets/Meshes/{type}.glb";

            // GLB에서 메시 추출
            var prefab = ExtractMeshAndCreatePrefab(glbPath, type);

            Debug.Log($"✅ {type} 프리팹 생성 완료: {prefab}");
        }
    }

    static GameObject ExtractMeshAndCreatePrefab(string glbPath, string name)
    {
        // 1. GLB 임포트
        var importer = AssetImporter.GetAtPath(glbPath) as ModelImporter;
        importer.importMaterials = false;
        importer.SaveAndReimport();

        // 2. 메시 추출
        var meshAsset = $"Assets/Meshes/{name}_mesh.asset";
        var meshes = AssetDatabase.LoadAllAssetsAtPath(glbPath);
        foreach (var obj in meshes)
        {
            if (obj is Mesh mesh)
            {
                AssetDatabase.CreateAsset(mesh, meshAsset);
                break;
            }
        }

        // 3. 프리팹 생성
        var prefab = new GameObject(name);
        var filter = prefab.AddComponent<MeshFilter>();
        prefab.AddComponent<MeshRenderer>();

        filter.mesh = AssetDatabase.LoadAssetAtPath<Mesh>(meshAsset);

        var prefabPath = $"Assets/Prefabs/{name}.prefab";
        PrefabUtility.SaveAsPrefabAsset(prefab, prefabPath);

        Object.DestroyImmediate(prefab);

        return AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
    }
}
#endif
```

---

## 결론

**단계**:
1. ✅ **지금**: 원본 메시 3개 다운로드 완료
2. ⏳ **다음**: Unity에 메시 임포트 → 프리팹 생성
3. 🎯 **런타임**: 프리팹 인스턴스 + 텍스처 적용

**GLB는 프리팹으로 변환 가능한가?**
- ✅ 네, 가능합니다
- ✅ 메시 추출 후 프리팹으로 만들 수 있습니다
- ✅ Unity 에디터에서 또는 코드로 자동화 가능합니다

**현재 우리의 경우**:
- 원본 메시 (spaceship.glb 등) → 프리팹
- Tripo3D 결과 (GLB) → 텍스처만 적용
