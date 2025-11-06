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

  // 캔버스로 현재 프레임 캡처
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0);
  const blob = await new Promise((r) => canvas.toBlob(r, "image/jpeg"));

  // 백엔드로 전송
  const formData = new FormData();
  formData.append("file", blob, "drawing.jpg");

  try {
    const response = await fetch("http://localhost:8000/analyze", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    loadingDiv.classList.add("hidden");
    resultDiv.classList.remove("hidden");
    resultText.innerText = `✅ 분석 완료! 도안 종류: ${data.label}`;
  } catch (err) {
    loadingDiv.classList.add("hidden");
    resultDiv.classList.remove("hidden");
    resultText.innerText = "❌ 오류가 발생했습니다. 다시 시도해주세요.";
    console.error(err);
  }
});

// 🔁 다시 찍기
retryBtn.addEventListener("click", () => {
  resultDiv.classList.add("hidden");
  statusDiv.classList.add("hidden");
  captureBtn.disabled = false;
});

initCamera();
