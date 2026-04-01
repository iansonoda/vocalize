const { ipcRenderer } = require("electron");
const historyContainer = document.getElementById("history");
const emptyState = document.getElementById("empty-state");
const collapseBtn = document.getElementById("collapseBtn");
const appContainer = document.getElementById("mainWindow");
const quitBtn = document.getElementById("quitBtn");
const livePreviewPanel = document.getElementById("live-preview");
const livePreviewText = document.getElementById("live-preview-text");
const livePreviewStatus = document.getElementById("live-preview-status");
let activePreviewSessionId = null;

collapseBtn.addEventListener("click", () => {
  appContainer.classList.toggle("collapsed");
});

quitBtn.addEventListener("click", () => {
  ipcRenderer.send("quit-app");
});

function formatTime(date) {
  let hours = date.getHours();
  let minutes = date.getMinutes();
  const ampm = hours >= 12 ? "PM" : "AM";
  hours = hours % 12;
  hours = hours ? hours : 12;
  minutes = minutes < 10 ? "0" + minutes : minutes;
  return hours + ":" + minutes + " " + ampm;
}

function showLivePreview(sessionId, text, statusLabel) {
  activePreviewSessionId = sessionId || activePreviewSessionId;
  livePreviewPanel.classList.remove("hidden");
  livePreviewText.textContent = text || "Listening for speech...";
  livePreviewStatus.textContent = statusLabel;
}

function clearLivePreview(sessionId = null) {
  if (sessionId && activePreviewSessionId && sessionId !== activePreviewSessionId) {
    return;
  }

  activePreviewSessionId = null;
  livePreviewPanel.classList.add("hidden");
  livePreviewText.textContent = "";
  livePreviewStatus.textContent = "Idle";
}

ipcRenderer.on("recording-status", (event, isRecording) => {
  if (isRecording) {
    showLivePreview(activePreviewSessionId, "Listening for speech...", "Listening");
  }
});

ipcRenderer.on("transcript-event", (event, payload) => {
  if (payload.event === "partial") {
    showLivePreview(payload.session_id, payload.text, "Partial");
  } else if (payload.event === "final") {
    showLivePreview(payload.session_id, payload.text, "Finalizing");
  } else if (payload.event === "error") {
    showLivePreview(
      payload.session_id,
      payload.message || "Something went wrong while transcribing.",
      "Issue",
    );
  } else if (payload.event === "session-complete") {
    clearLivePreview(payload.session_id);
  }
});

ipcRenderer.on("new-transcription", (event, data) => {
  if (emptyState) {
    emptyState.style.display = "none";
  }

  clearLivePreview(data.session_id);

  const item = document.createElement("div");
  item.className =
    "flex items-baseline py-4 px-6 border-b border-[#f4f4f4] transition-colors duration-200 last:border-b-0 hover:bg-[#fafafa] animate-fade-in";

  // Format time for the current dictation
  const timeStr = formatTime(new Date());

  item.innerHTML = `
        <div class="w-[120px] shrink-0 text-[#888] text-[13px] font-medium">${timeStr}</div>
        <div class="text-[#333] text-sm leading-relaxed">${data.formatted}</div>
    `;

  // Add to top of list
  historyContainer.prepend(item);

  // Limit to 50 items
  if (historyContainer.children.length > 50) {
    historyContainer.removeChild(historyContainer.lastChild);
  }
});

// Update Analytics
ipcRenderer.on("stats-update", (event, stats) => {
  const streakEl = document.getElementById("streak-val");
  const wordsEl = document.getElementById("words-val");
  const wpmEl = document.getElementById("wpm-val");

  if (streakEl)
    streakEl.textContent = `${stats.streak} day${stats.streak !== 1 ? "s" : ""}`;
  if (wordsEl)
    wordsEl.textContent = `${stats.total_words.toLocaleString()} words overall`;
  if (wpmEl) wpmEl.textContent = `${stats.wpm} WPM`;
});
