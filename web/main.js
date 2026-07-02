const tabs = document.querySelectorAll(".tab");
const fileForm = document.querySelector("#fileForm");
const urlForm = document.querySelector("#urlForm");
const fileInput = document.querySelector("#imageInput");
const fileName = document.querySelector("#fileName");
const urlInput = document.querySelector("#urlInput");
const statusNode = document.querySelector("#status");
const langToggle = document.querySelector("#langToggle");
const logNode = document.querySelector("#log");
const previewStage = document.querySelector(".preview-stage");
const preview = document.querySelector("#preview");
const downloadLink = document.querySelector("#downloadLink");
const sizeStat = document.querySelector("#sizeStat");
const frameStat = document.querySelector("#frameStat");
const fileStat = document.querySelector("#fileStat");
let language = "zh";
let busy = false;
let selectedFileLabel = "";

const copy = {
  zh: {
    langButton: "English",
    ready: "就绪",
    working: "处理中",
    title: "表情动图提取台",
    tabFile: "上传图片",
    tabUrl: "粘贴链接",
    chooseLocal: "选择本地图片",
    fileHelp: "支持 animated WebP / AWebP / GIF，也可转单帧图片",
    extract: "提取 GIF",
    imageUrl: "图片链接",
    downloadExtract: "下载并提取",
    runLog: "运行记录",
    previewTitle: "输出预览",
    downloadGif: "下载 GIF",
    empty: "完成转换后，GIF 会显示在这里。",
    size: "尺寸",
    frames: "帧数",
    file: "文件",
    pasteUrl: "请先粘贴图片链接。",
    downloading: "正在下载",
    failed: "转换失败",
    chooseFile: "请先选择图片文件。",
    uploading: "正在上传",
    created: "已生成",
    boot: "就绪。上传图片或粘贴链接。",
  },
  en: {
    langButton: "中文",
    ready: "Ready",
    working: "Working",
    title: "Emote GIF extractor",
    tabFile: "Upload image",
    tabUrl: "Paste link",
    chooseLocal: "Choose local image",
    fileHelp: "Supports animated WebP / AWebP / GIF and single-frame images",
    extract: "Extract GIF",
    imageUrl: "Image URL",
    downloadExtract: "Download and extract",
    runLog: "Run log",
    previewTitle: "Output preview",
    downloadGif: "Download GIF",
    empty: "The converted GIF appears here.",
    size: "Size",
    frames: "Frames",
    file: "File",
    pasteUrl: "Paste an image URL first.",
    downloading: "Downloading",
    failed: "Conversion failed",
    chooseFile: "Choose an image file first.",
    uploading: "Uploading",
    created: "Created",
    boot: "Ready. Upload an image or paste a link.",
  },
};

function t(key) {
  return copy[language][key];
}

function applyLanguage() {
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  langToggle.textContent = t("langButton");
  statusNode.textContent = busy ? t("working") : t("ready");
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  if (!selectedFileLabel) fileName.textContent = t("fileHelp");
}

function log(message) {
  const time = new Date().toLocaleTimeString();
  logNode.textContent += `${time}  ${message}\n`;
  logNode.scrollTop = logNode.scrollHeight;
}

function setBusy(isBusy) {
  busy = isBusy;
  statusNode.textContent = isBusy ? t("working") : t("ready");
  document.querySelectorAll("button").forEach((button) => {
    button.disabled = isBusy;
  });
  langToggle.disabled = false;
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
    log(t("pasteUrl"));
    return;
  }
  setBusy(true);
  log(`${t("downloading")} ${url}`);
  try {
    const response = await fetch("/api/convert-url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || t("failed"));
    showResult(payload.result);
    log(`${t("created")} ${payload.result.gif}`);
  } catch (error) {
    log(`ERROR ${error.message}`);
  } finally {
    setBusy(false);
  }
}

async function convertFile(event) {
  event.preventDefault();
  if (!fileInput.files.length) {
    log(t("chooseFile"));
    return;
  }
  setBusy(true);
  log(`${t("uploading")} ${fileInput.files[0].name}`);
  try {
    const formData = new FormData(fileForm);
    const response = await fetch("/api/convert-file", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || t("failed"));
    showResult(payload.result);
    log(`${t("created")} ${payload.result.gif}`);
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
  selectedFileLabel = fileInput.files.length ? fileInput.files[0].name : "";
  fileName.textContent = selectedFileLabel || t("fileHelp");
});

langToggle.addEventListener("click", () => {
  language = language === "zh" ? "en" : "zh";
  applyLanguage();
});

fileForm.addEventListener("submit", convertFile);
urlForm.addEventListener("submit", convertUrl);
applyLanguage();
log(t("boot"));
