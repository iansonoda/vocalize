const { app, BrowserWindow, screen, ipcMain, Tray, Menu } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

let mainWindow;
let bubbleWindow;
let pythonProcess;
let tray;

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  // Main Dashboard Window
  mainWindow = new BrowserWindow({
    width: 600,
    height: 700,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
    titleBarStyle: "hiddenInset",
    show: false,
    backgroundColor: "#0f172a",
  });

  mainWindow.on("close", (event) => {
    if (!app.isQuiting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('show', () => {
    if (process.platform === 'darwin') app.dock.show();
  });

  mainWindow.on('hide', () => {
    if (process.platform === 'darwin') app.dock.hide();
  });

  mainWindow.loadFile("index.html");

  // Bubble Overlay
  bubbleWindow = new BrowserWindow({
    width: 400,
    height: 100,
    x: Math.floor((width - 400) / 2),
    y: height - 120,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    movable: false,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
    show: false,
  });

  bubbleWindow.on("close", (event) => {
    if (!app.isQuiting) {
      event.preventDefault();
      bubbleWindow.hide();
    }
  });

  bubbleWindow.setIgnoreMouseEvents(true);
  bubbleWindow.loadFile("bubble.html");

  mainWindow.once("ready-to-show", () => {
    // We don't auto-show now, stay in tray
    console.log("Dashboard ready in background");
  });
}

app.whenReady().then(() => {
  createWindow();

  tray = new Tray(path.join(__dirname, "icon.png"));
  const contextMenu = Menu.buildFromTemplate([
    {
      label: "Open Dashboard",
      click: () => {
        if (!mainWindow.isVisible()) mainWindow.show();
        mainWindow.focus();
      },
    },
    { type: "separator" },
    {
      label: "Quit",
      click: () => {
        app.isQuiting = true;
        app.quit();
      },
    },
  ]);
  tray.setToolTip("AI Speech Tool");
  tray.setContextMenu(contextMenu);

  startPython();
});

function startPython() {
  const venvPath = path.join(__dirname, "..", "venv", "bin", "python3");
  const pythonPath = require("fs").existsSync(venvPath) ? venvPath : "python3";
  const scriptPath = path.join(__dirname, "..", "main.py");

  pythonProcess = spawn(pythonPath, ["-u", scriptPath], {
    cwd: path.join(__dirname, ".."),
  });

  pythonProcess.stdout.on("data", (data) => {
    const rawOutput = data.toString();
    const lines = rawOutput.split("\n");

    lines.forEach((line) => {
      if (line.includes("--- 🟢 Recording Started ---")) {
        if (bubbleWindow && !bubbleWindow.isDestroyed()) {
          bubbleWindow.show();
          bubbleWindow.webContents.send("recording-status", true);
        }
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send("recording-status", true);
        }
      } else if (line.includes("--- 🔴 Recording Stopped ---")) {
        if (bubbleWindow && !bubbleWindow.isDestroyed()) {
          bubbleWindow.webContents.send("recording-status", false);
          setTimeout(() => {
            if (bubbleWindow && !bubbleWindow.isDestroyed())
              bubbleWindow.hide();
          }, 1500);
        }
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send("recording-status", false);
        }
      } else if (line.startsWith("VOL:")) {
        const vol = parseFloat(line.split(":")[1]);
        if (bubbleWindow && !bubbleWindow.isDestroyed()) {
          bubbleWindow.webContents.send("volume", vol);
        }
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send("volume", vol);
        }
      } else if (line.startsWith("FINAL:")) {
        const payload = JSON.parse(line.substring(6));
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send("new-transcription", payload);
        }
      } else if (line.startsWith("DEBUG:")) {
        console.log("Python Debug:", line);
      }
    });
  });

  pythonProcess.stderr.on("data", (data) => {
    console.error("Python Error:", data.toString());
  });

  pythonProcess.on("close", (code) => {
    console.log(`Python process exited with code ${code}`);
    app.quit();
  });
}

// IPC for settings
ipcMain.on("update-settings", (event, settings) => {
  if (pythonProcess) {
    pythonProcess.stdin.write(`SETTINGS:${JSON.stringify(settings)}\n`);
  }
});

app.on("window-all-closed", function () {
  if (process.platform !== "darwin") app.quit();
});

app.on("quit", () => {
  if (pythonProcess) pythonProcess.kill();
});
