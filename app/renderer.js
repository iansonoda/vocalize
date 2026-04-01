const { ipcRenderer } = require("electron");
const historyContainer = document.getElementById("history");
const emptyState = document.getElementById("empty-state");
const collapseBtn = document.getElementById("collapseBtn");
const appContainer = document.getElementById("mainWindow");
const quitBtn = document.getElementById("quitBtn");
const livePreviewPanel = document.getElementById("live-preview");
const livePreviewText = document.getElementById("live-preview-text");
const livePreviewStatus = document.getElementById("live-preview-status");
const modePicker = document.getElementById("mode-picker");
const modeDescription = document.getElementById("mode-description");
let activePreviewSessionId = null;
let selectedMode = "plain";

const MODE_DETAILS = {
  plain: {
    label: "Plain",
    description:
      "Plain mode keeps cleanup minimal and close to your original wording.",
  },
  notes: {
    label: "Notes",
    description:
      "Notes mode shapes the transcript into concise bullets or structured notes without inventing extra content.",
  },
  email: {
    label: "Email",
    description:
      "Email mode turns dictation into an email-ready message body while keeping your meaning and any dictated greeting or sign-off.",
  },
  code: {
    label: "Code",
    description:
      "Code mode stays literal, preserves developer vocabulary, and favors structure over polished prose.",
  },
};

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

function renderModeSelection() {
  const chips = modePicker.querySelectorAll("[data-mode]");
  chips.forEach((chip) => {
    const isActive = chip.dataset.mode === selectedMode;
    chip.classList.toggle("mode-chip-active", isActive);
    chip.setAttribute("aria-pressed", isActive ? "true" : "false");
  });

  const detail = MODE_DETAILS[selectedMode] || MODE_DETAILS.plain;
  modeDescription.textContent = detail.description;
}

function sendSettingsUpdate() {
  ipcRenderer.send("update-settings", {
    mode: selectedMode,
  });
}

function setMode(nextMode) {
  if (!MODE_DETAILS[nextMode]) {
    return;
  }

  selectedMode = nextMode;
  localStorage.setItem("vocalize-mode", selectedMode);
  renderModeSelection();
  sendSettingsUpdate();
}

modePicker.addEventListener("click", (event) => {
  const button = event.target.closest("[data-mode]");
  if (!button) {
    return;
  }

  setMode(button.dataset.mode);
});

const savedMode = localStorage.getItem("vocalize-mode");
if (savedMode && MODE_DETAILS[savedMode]) {
  selectedMode = savedMode;
}
renderModeSelection();
sendSettingsUpdate();

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

  const modeLabel = (MODE_DETAILS[data.mode] || MODE_DETAILS.plain).label;
  const cleanupMeta =
    data.cleanup_source === "raw_fallback"
      ? `Raw fallback${data.cleanup_fallback_reason ? ` • ${data.cleanup_fallback_reason}` : ""}`
      : "Mode cleanup";

  const item = document.createElement("div");
  item.className =
    "flex items-baseline py-4 px-6 border-b border-[#f4f4f4] transition-colors duration-200 last:border-b-0 hover:bg-[#fafafa] animate-fade-in";

  // Format time for the current dictation
  const timeStr = formatTime(new Date());

  item.innerHTML = `
        <div class="w-[120px] shrink-0 text-[#888] text-[13px] font-medium">${timeStr}</div>
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-1">
            <span class="inline-flex items-center rounded-full bg-[#fff7ed] px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.08em] text-[#c2410c]">${modeLabel}</span>
            <span class="text-[11px] text-stone-400">${cleanupMeta}</span>
          </div>
          <div class="text-[#333] text-sm leading-relaxed">${data.formatted}</div>
        </div>
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
