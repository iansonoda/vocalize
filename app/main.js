const {
  app,
  BrowserWindow,
  screen,
  ipcMain,
  Menu,
  nativeImage,
} = require("electron");
const path = require("path");
const { spawn } = require("child_process");

let mainWindow;
let pythonProcess;
let overlayWindow;

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  // Main Dashboard Window
  mainWindow = new BrowserWindow({
    width: Math.floor(width * (2 / 3)),
    height: Math.floor(height * (2 / 3)),
    icon: path.join(__dirname, "openflow_icon.png"),
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
    titleBarStyle: "hiddenInset",
    show: false, // Start hidden to prevent flicker
    backgroundColor: "#0f172a",
  });

  mainWindow.on("close", (event) => {
    if (!app.isQuiting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on("show", () => {
    if (process.platform === "darwin") {
      app.dock.show();
    }
  });

  mainWindow.on("hide", () => {
    // We keep it visible even when hidden to allow reactivating from Dock
    if (process.platform === "darwin") {
      app.dock.show();
    }
  });

  mainWindow.loadFile("index.html");

  // Unified Small Overlay Window
  overlayWindow = new BrowserWindow({
    width: 300,
    height: 120,
    x: Math.floor((width - 300) / 2),
    y: height - 120,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    focusable: false,
    resizable: false,
    movable: false,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
    show: true,
  });
  overlayWindow.setIgnoreMouseEvents(true, { forward: true });
  overlayWindow.loadFile("overlay.html");

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
    mainWindow.focus();
    if (process.platform === "darwin") {
      app.dock.show();
    }
    console.log("Dashboard ready and shown");
  });
}

app.setName("Vocalize AI");

app.whenReady().then(() => {
  if (process.platform === "darwin") {
    const iconPath = path.join(__dirname, "openflow_icon.png");
    const appIcon = nativeImage.createFromPath(iconPath);
    app.dock.setIcon(appIcon);
    app.dock.show();

    // Setup dock menu for right-click on taskbar icon
    const dockMenu = Menu.buildFromTemplate([
      {
        label: "Quit",
        click: () => {
          app.isQuiting = true;
          app.quit();
        },
      },
    ]);
    app.dock.setMenu(dockMenu);
  }

  createWindow();

  // Poll mouse position to implement robust hover across transparent window ignoring mouse events
  setInterval(() => {
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      const point = screen.getCursorScreenPoint();
      const bounds = overlayWindow.getBounds();
      overlayWindow.webContents.send("cursor-point", {
        x: point.x - bounds.x,
        y: point.y - bounds.y,
      });
    }
  }, 50);

  // When clicking the dock icon, show the dashboard
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else if (mainWindow && !mainWindow.isVisible()) {
      mainWindow.show();
      mainWindow.focus();
    }
  });

  startPython();
});

app.on("before-quit", () => {
  app.isQuiting = true;
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
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send("recording-status", true);
        }
        if (overlayWindow && !overlayWindow.isDestroyed()) {
          overlayWindow.webContents.send("status", "recording");
        }
      } else if (line.includes("--- 🔴 Recording Stopped ---")) {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send("recording-status", false);
        }
      } else if (line.startsWith("STATUS: loading")) {
        if (overlayWindow && !overlayWindow.isDestroyed()) {
          overlayWindow.webContents.send("status", "loading");
        }
      } else if (line.startsWith("BANDS:")) {
        const bandsData = JSON.parse(line.substring(6));
        if (overlayWindow && !overlayWindow.isDestroyed()) {
          overlayWindow.webContents.send("bands", bandsData);
        }
      } else if (line.startsWith("VOL:")) {
        const vol = parseFloat(line.split(":")[1]);
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send("volume", vol);
        }
      } else if (line.startsWith("FINAL:")) {
        const payload = JSON.parse(line.substring(6));
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send("new-transcription", payload);
        }
        if (overlayWindow && !overlayWindow.isDestroyed()) {
          overlayWindow.webContents.send("status", "idle");
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

ipcMain.on("quit-app", () => {
  app.isQuiting = true;
  app.quit();
});

app.on("window-all-closed", function () {
  if (process.platform !== "darwin") app.quit();
});

app.on("quit", () => {
  if (pythonProcess) pythonProcess.kill();
});
