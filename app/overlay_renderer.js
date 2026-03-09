const { ipcRenderer } = require("electron");
const waveContainer = document.getElementById("wave-container");
const pill = document.getElementById("pill");
const tooltip = document.getElementById("tooltip");

const numBars = 15;
const bars = [];

for (let i = 0; i < numBars; i++) {
  const bar = document.createElement("div");
  bar.className = "bar";
  waveContainer.appendChild(bar);
  bars.push(bar);
}

// Robust hover detection for macOS Electron forward:true behavior
const hoverArea = document.getElementById("hover-area");
ipcRenderer.on("cursor-point", (event, pt) => {
  // Strictly detect if the mouse is directly over the pill element itself
  const rect = pill.getBoundingClientRect();
  if (
    pt.x >= rect.left &&
    pt.x <= rect.right &&
    pt.y >= rect.top &&
    pt.y <= rect.bottom
  ) {
    hoverArea.classList.add("hovered");
  } else {
    hoverArea.classList.remove("hovered");
  }
});
// Fallback standard event listeners too
hoverArea.addEventListener("mouseenter", () =>
  hoverArea.classList.add("hovered"),
);
hoverArea.addEventListener("mouseleave", () =>
  hoverArea.classList.remove("hovered"),
);

ipcRenderer.on("status", (event, status) => {
  if (status === "loading") {
    pill.classList.add("loading");
    pill.classList.remove("recording");
    tooltip.classList.add("visible");
    tooltip.innerHTML = "Loading response...";
  } else if (status === "recording") {
    pill.classList.remove("loading");
    pill.classList.add("recording");
    tooltip.classList.add("visible");
    tooltip.innerHTML = "Listening...";
  } else if (status === "stopped" || status === "idle") {
    pill.classList.remove("loading");
    pill.classList.remove("recording");
    tooltip.classList.remove("visible");

    // Delay changing the text so it doesn't flash while fading out
    setTimeout(() => {
      if (
        !pill.classList.contains("loading") &&
        !pill.classList.contains("recording")
      ) {
        tooltip.innerHTML =
          'Click or hold <span class="text-[#ec4899] font-semibold">⌥ Opt ➔</span> to start dictating';
      }
    }, 200);

    // Reset bars to empty so CSS controls idle hidden state
    bars.forEach((bar) => {
      bar.style.height = "";
    });
  }
});

ipcRenderer.on("bands", (event, bandData) => {
  if (!pill.classList.contains("recording")) return;

  bars.forEach((bar, i) => {
    const vol = bandData[i] || 0;
    // Scale from 4px to 16px based on band sensitivity
    const h = 4 + vol * 12 * (0.8 + Math.random() * 0.4);
    bar.style.height = `${Math.min(h, 16)}px`;
  });
});
