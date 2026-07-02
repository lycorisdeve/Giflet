const tabs = document.querySelectorAll(".tab");
const fileForm = document.querySelector("#fileForm");
const urlForm = document.querySelector("#urlForm");
const fileInput = document.querySelector("#imageInput");
const fileName = document.querySelector("#fileName");
const urlInput = document.querySelector("#urlInput");
const statusNode = document.querySelector("#status");
const logNode = document.querySelector("#log");
const previewStage = document.querySelector(".preview-stage");
const preview = document.querySelector("#preview");
const downloadLink = document.querySelector("#downloadLink");
const sizeStat = document.querySelector("#sizeStat");
const frameStat = document.querySelector("#frameStat");
const fileStat = document.querySelector("#fileStat");

function log(message) {
  const time = new Date().toLocaleTimeString();
  logNode.textContent += `${time}  ${message}\n`;
  logNode.scrollTop = logNode.scrollHeight;
}

function setBusy(isBusy) {
  statusNode.textContent = isBusy ? "Working" : "Ready";
  document.querySelectorAll("button").forEach((button) => {
    button.disabled = isBusy;
  });
}

function showResult(result) {
  preview.src = `${result.previewUrl}?t=${Date.now()}`;
  previewStage.classList.add("has-image");
  downloadLink.href = result.downloadUrl;
  downloadLink.download = result.gif;
  downloadLink.classList.remove("is-disabled");
  sizeStat.textContent = `${result.width}x${result.height}`;
  frameStat.textContent = `${result.frames}`;
  fileStat.textContent = result.gif;
}

async function convertUrl(event) {
  event.preventDefault();
  const url = urlInput.value.trim();
  if (!url) {
    log("Paste an image URL first.");
    return;
  }
  setBusy(true);
  log(`Downloading ${url}`);
  try {
    const response = await fetch("/api/convert-url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "Conversion failed");
    showResult(payload.result);
    log(`Created ${payload.result.gif}`);
  } catch (error) {
    log(`ERROR ${error.message}`);
  } finally {
    setBusy(false);
  }
}

async function convertFile(event) {
  event.preventDefault();
  if (!fileInput.files.length) {
    log("Choose an image file first.");
    return;
  }
  setBusy(true);
  log(`Uploading ${fileInput.files[0].name}`);
  try {
    const formData = new FormData(fileForm);
    const response = await fetch("/api/convert-file", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "Conversion failed");
    showResult(payload.result);
    log(`Created ${payload.result.gif}`);
  } catch (error) {
    log(`ERROR ${error.message}`);
  } finally {
    setBusy(false);
  }
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((item) => item.classList.remove("is-active"));
    tab.classList.add("is-active");
    const mode = tab.dataset.tab;
    fileForm.classList.toggle("is-hidden", mode !== "file");
    urlForm.classList.toggle("is-hidden", mode !== "url");
  });
});

fileInput.addEventListener("change", () => {
  fileName.textContent = fileInput.files.length ? fileInput.files[0].name : "支持 animated WebP / AWebP / GIF，也可转单帧图片";
});

fileForm.addEventListener("submit", convertFile);
urlForm.addEventListener("submit", convertUrl);
log("Ready. Upload an image or paste a link.");
