const video = document.getElementById("video");
const captureBtn = document.getElementById("capture-btn");
const statusDiv = document.getElementById("status");
const loadingDiv = document.getElementById("loading");
const resultDiv = document.getElementById("result");
const resultText = document.getElementById("result-text");
const retryBtn = document.getElementById("retry-btn");

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

// 🖼️ 캡처 → 백엔드로 전송
captureBtn.addEventListener("click", async () => {
  captureBtn.disabled = true;
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
    captureBtn.disabled = false;
    loadingDiv.classList.add("hidden");
    return;
  }

  const formData = new FormData();
  formData.append("file", blob, "drawing.jpg");

  try {
    // ✅ Ngrok에서도 호환되게 상대 경로로 호출
    const response = await fetch("/analyze", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`서버 응답 오류: ${response.status}`);
    }

    const data = await response.json();
    console.log("✅ 백엔드 응답:", data);

    loadingDiv.classList.add("hidden");
    resultDiv.classList.remove("hidden");
    resultText.innerText = `✅ 분석 완료! 도안: ${data.label}, 어린이: ${data.child_name}`;
  } catch (err) {
    console.error("❌ 업로드 오류:", err);
    loadingDiv.classList.add("hidden");
    resultDiv.classList.remove("hidden");
    resultText.innerText = "❌ 오류가 발생했습니다. 다시 시도해주세요.";
  }
});

// 🔁 다시 찍기
retryBtn.addEventListener("click", () => {
  resultDiv.classList.add("hidden");
  statusDiv.classList.add("hidden");
  captureBtn.disabled = false;
});

initCamera();
