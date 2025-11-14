const video = document.getElementById("video");
const captureBtn = document.getElementById("capture-btn");
const statusDiv = document.getElementById("status");
const loadingDiv = document.getElementById("loading");
const resultDiv = document.getElementById("result");
const resultText = document.getElementById("result-text");
const retryBtn = document.getElementById("retry-btn");

// 🆕 진행 중인 Task 추적
const activeTasks = new Map(); // {task_id: {status, progress, childName}}

// 🎥 카메라 시작
async function initCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
  } catch (err) {
    alert("카메라를 켤 수 없습니다. 권한을 허용해주세요.");
    console.error(err);
  }
}

// 🖼️ 캡처 → 백엔드로 전송 (비동기, 즉시 반환!)
captureBtn.addEventListener("click", async () => {
  statusDiv.classList.remove("hidden");
  loadingDiv.classList.remove("hidden");

  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0);

  // ✅ Blob 생성
  const blob = await new Promise((r) => canvas.toBlob(r, "image/jpeg"));
  if (!blob) {
    console.error("⚠️ Blob 생성 실패! 캔버스 캡처 문제 발생");
    alert("이미지를 캡처하지 못했습니다. 다시 시도해주세요.");
    loadingDiv.classList.add("hidden");
    return;
  }

  const formData = new FormData();
  formData.append("file", blob, "drawing.jpg");

  try {
    // ✅ 즉시 반환 (0.5초 안에!)
    console.log("📤 이미지 업로드 중...");
    const response = await fetch("/analyze", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`서버 응답 오류: ${response.status}`);
    }

    const data = await response.json();
    console.log("✅ 백엔드 응답 (즉시 반환):", data);

    if (data.status === "queued") {
      // ✅ Task가 큐에 추가됨
      const taskId = data.task_id;
      const statusUrl = data.status_url;

      resultText.innerText = `⏳ 작업이 큐에 추가되었습니다. 처리 중입니다...`;
      loadingDiv.classList.add("hidden");
      resultDiv.classList.remove("hidden");

      // 🆕 Task 추적 시작
      activeTasks.set(taskId, {
        status: "queued",
        progress: 0,
        label: "Unknown",
        childName: "Unknown",
      });

      // 🔄 폴링 시작 (상태 확인)
      startPollingTask(taskId, statusUrl);

      // ✨ 즉시 "다시 찍기" 활성화
      setTimeout(() => {
        retryBtn.disabled = false;
        resultText.innerText = `✅ 작업 중입니다! 계속 그림을 찍을 수 있습니다.`;
      }, 500);
    } else {
      throw new Error("예상치 못한 응답 형식");
    }
  } catch (err) {
    console.error("❌ 업로드 오류:", err);
    loadingDiv.classList.add("hidden");
    resultDiv.classList.remove("hidden");
    resultText.innerText = "❌ 오류가 발생했습니다. 다시 시도해주세요.";
  }
});

// 🔄 Task 상태 폴링
async function startPollingTask(taskId, statusUrl) {
  console.log(`⏳ Task ${taskId} 폴링 시작...`);

  const pollInterval = setInterval(async () => {
    try {
      const response = await fetch(statusUrl);
      const data = await response.json();

      // 상태 업데이트
      const label = data.result?.label || activeTasks.get(taskId)?.label || "Unknown";
      const childName = data.result?.child_name || activeTasks.get(taskId)?.childName || "Unknown";

      activeTasks.set(taskId, {
        status: data.status,
        progress: data.progress,
        label: label,
        childName: childName,
      });

      console.log(`[${taskId}] 상태: ${data.status}, 진행률: ${data.progress}%, 도안: ${label}, 아이: ${childName}`);

      // 진행률 업데이트
      if (data.status === "processing") {
        resultText.innerText = `⏳ 작업 중... ${data.progress}% (${childName}님의 ${label})`;
      }

      if (data.status === "done") {
        // ✅ 완료!
        console.log(`✅ Task ${taskId} 완료!`);
        const taskInfo = activeTasks.get(taskId);
        resultText.innerText = `✅ 작업 완료! ${taskInfo.childName}님의 ${taskInfo.label} 준비됨 🎉`;
        clearInterval(pollInterval);
        activeTasks.delete(taskId);
      } else if (data.status === "error") {
        // ❌ 오류
        console.error(`❌ Task ${taskId} 오류: ${data.error}`);
        resultText.innerText = `❌ 오류 발생: ${data.error}`;
        clearInterval(pollInterval);
        activeTasks.delete(taskId);
      }
    } catch (err) {
      console.error(`⚠️ 폴링 오류: ${err}`);
    }
  }, 2000); // 2초마다 폴링
}

// 🔁 다시 찍기
retryBtn.addEventListener("click", () => {
  resultDiv.classList.add("hidden");
  statusDiv.classList.add("hidden");
  resultText.innerText = "";
  loadingDiv.classList.remove("hidden");

  // ✨ 여전히 활성 Task가 있으면 계속 폴링됨 (백그라운드에서)
  console.log(`📊 현재 처리 중인 Task: ${activeTasks.size}개`);
});

initCamera();
