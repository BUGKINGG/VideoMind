const userId = document.querySelector("#userId");
const sessionId = document.querySelector("#sessionId");
const videoSelect = document.querySelector("#videoSelect");
const videoTitle = document.querySelector("#videoTitle");
const messages = document.querySelector("#messages");
const chatForm = document.querySelector("#chatForm");
const questionInput = document.querySelector("#questionInput");
const sendButton = document.querySelector("#sendButton");
const summaryButton = document.querySelector("#summaryButton");
const clearButton = document.querySelector("#clearButton");
const statusDot = document.querySelector("#statusDot");
const statusText = document.querySelector("#statusText");

let videos = [];

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "请求失败");
  return data;
}

function setBusy(busy) {
  sendButton.disabled = busy;
  summaryButton.disabled = busy;
  statusText.textContent = busy ? "Agent 正在处理" : "Agent 已连接";
}

function addMessage(role, text, sources = []) {
  const row = document.createElement("article");
  row.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  if (sources.length) {
    const sourceList = document.createElement("div");
    sourceList.className = "sources";
    sources.forEach((source) => {
      const item = document.createElement("div");
      item.className = "source";
      item.textContent = `${source.chunk_id}: ${source.text.slice(0, 180)}${source.text.length > 180 ? "..." : ""}`;
      sourceList.appendChild(item);
    });
    bubble.appendChild(sourceList);
  }

  row.appendChild(bubble);
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
}

function selectedVideo() {
  return videos.find((video) => video.video_id === videoSelect.value);
}

async function loadVideos() {
  const data = await api("/api/videos");
  videos = data.videos;
  videoSelect.innerHTML = "";
  videos.forEach((video) => {
    const option = document.createElement("option");
    option.value = video.video_id;
    option.textContent = video.title;
    videoSelect.appendChild(option);
  });
  updateVideoTitle();
}

function updateVideoTitle() {
  videoTitle.textContent = selectedVideo()?.title || "暂无已索引视频";
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question || !videoSelect.value) return;
  addMessage("user", question);
  questionInput.value = "";
  setBusy(true);
  try {
    const result = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId.value.trim(),
        session_id: sessionId.value.trim(),
        video_id: videoSelect.value,
        question,
      }),
    });
    addMessage("agent", result.answer, result.sources);
  } catch (error) {
    addMessage("agent error", error.message);
  } finally {
    setBusy(false);
  }
});

summaryButton.addEventListener("click", async () => {
  if (!videoSelect.value) return;
  setBusy(true);
  try {
    const result = await api("/api/summary", {
      method: "POST",
      body: JSON.stringify({ user_id: userId.value.trim(), video_id: videoSelect.value }),
    });
    addMessage("agent", result.summary);
  } catch (error) {
    addMessage("agent error", error.message);
  } finally {
    setBusy(false);
  }
});

videoSelect.addEventListener("change", updateVideoTitle);
clearButton.addEventListener("click", () => {
  messages.querySelectorAll(".message").forEach((item) => item.remove());
});

async function initialize() {
  try {
    await api("/api/health");
    statusDot.classList.add("online");
    statusText.textContent = "Agent 已连接";
    await loadVideos();
  } catch (error) {
    statusText.textContent = "无法连接 Agent";
    addMessage("agent error", error.message);
  }
}

initialize();
