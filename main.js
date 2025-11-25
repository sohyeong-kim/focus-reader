const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let serverProcess;

// Check if running in development
const isDev = !app.isPackaged;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    icon: path.join(__dirname, 'assets', 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#1e1e2e'
  });

  // Load the HTML file
  mainWindow.loadFile('focusread-v5.html');

  // Open DevTools in development
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function startPythonServer() {
  const serverPath = isDev
    ? path.join(__dirname, 'server_grobid_v2.py')
    : path.join(process.resourcesPath, 'server_grobid_v2.py');

  console.log('Starting Python server from:', serverPath);

  serverProcess = spawn('python3', [serverPath], {
    stdio: ['pipe', 'pipe', 'pipe']
  });

  serverProcess.stdout.on('data', (data) => {
    console.log(`Server: ${data}`);
  });

  serverProcess.stderr.on('data', (data) => {
    console.error(`Server Error: ${data}`);
  });

  serverProcess.on('close', (code) => {
    console.log(`Server process exited with code ${code}`);
  });

  serverProcess.on('error', (err) => {
    console.error('Failed to start server:', err);
    dialog.showErrorBox(
      'Server Error',
      'Failed to start Python server. Make sure Python 3 and required packages are installed.\n\n' +
      'Required: pip install fastapi uvicorn httpx spacy\n' +
      'And: python -m spacy download en_core_web_sm'
    );
  });
}

function stopPythonServer() {
  if (serverProcess) {
    console.log('Stopping Python server...');
    serverProcess.kill('SIGTERM');
    serverProcess = null;
  }
}

// Check Docker/Grobid status
async function checkGrobid() {
  try {
    const http = require('http');
    return new Promise((resolve) => {
      const req = http.get('http://localhost:8070/api/isalive', (res) => {
        resolve(res.statusCode === 200);
      });
      req.on('error', () => resolve(false));
      req.setTimeout(2000, () => {
        req.destroy();
        resolve(false);
      });
    });
  } catch {
    return false;
  }
}

app.whenReady().then(async () => {
  // Check if Grobid is running
  const grobidRunning = await checkGrobid();
  if (!grobidRunning) {
    const result = await dialog.showMessageBox({
      type: 'warning',
      title: 'Grobid Not Running',
      message: 'Grobid server is not running on port 8070.',
      detail: 'To use PDF parsing features, please start Grobid with Docker:\n\n' +
              'docker run -d --name grobid -p 8070:8070 lfoppiano/grobid:0.8.0\n\n' +
              'Click "Continue" to open the app anyway (PDF parsing won\'t work).',
      buttons: ['Continue', 'Quit'],
      defaultId: 0
    });

    if (result.response === 1) {
      app.quit();
      return;
    }
  }

  // Start Python server
  startPythonServer();

  // Wait a bit for server to start
  await new Promise(resolve => setTimeout(resolve, 2000));

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  stopPythonServer();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopPythonServer();
});

app.on('will-quit', () => {
  stopPythonServer();
});
