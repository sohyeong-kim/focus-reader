const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, execSync } = require('child_process');

let mainWindow;
let serverProcess;

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
      preload: path.join(__dirname, 'preload.js'),
    },
    backgroundColor: '#1e1e2e',
  });

  mainWindow.loadFile('focusread-v5.html');

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ---------------- host-python helpers ----------------

// Need 3.10+ for current Docling. macOS ships /usr/bin/python3 at 3.9.x, so
// version-suffixed binaries and Homebrew paths come first.
function findSystemPython() {
  const candidates = [
    '/opt/homebrew/bin/python3.13',
    '/opt/homebrew/bin/python3.12',
    '/opt/homebrew/bin/python3.11',
    '/opt/homebrew/bin/python3.10',
    '/usr/local/bin/python3.13',
    '/usr/local/bin/python3.12',
    '/usr/local/bin/python3.11',
    '/usr/local/bin/python3.10',
    'python3.13',
    'python3.12',
    'python3.11',
    'python3.10',
    '/opt/miniconda3/bin/python3',
    '/opt/homebrew/bin/python3',
    '/usr/local/bin/python3',
    '/usr/bin/python3',
    'python3',
  ];
  for (const p of candidates) {
    try {
      const out = execSync(
        `${p} -c "import sys; print(sys.version_info >= (3,10))"`,
        { encoding: 'utf8' }
      );
      if (out.trim() === 'True') return p;
    } catch (e) {
      // skip and try the next candidate
    }
  }
  return null;
}

function venvPython(venvDir) {
  return process.platform === 'win32'
    ? path.join(venvDir, 'Scripts', 'python.exe')
    : path.join(venvDir, 'bin', 'python');
}

function resourcePath(name) {
  return isDev
    ? path.join(__dirname, name)
    : path.join(process.resourcesPath, name);
}

function spawnAsync(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { stdio: 'inherit', ...opts });
    p.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${cmd} ${args.join(' ')} exited ${code}`));
    });
    p.on('error', reject);
  });
}

async function ensurePythonEnv() {
  const venvDir = path.join(app.getPath('userData'), 'venv');
  const pythonBin = venvPython(venvDir);

  if (fs.existsSync(pythonBin)) {
    return pythonBin;
  }

  const systemPython = findSystemPython();
  if (!systemPython) {
    throw new Error(
      'Python 3.10+ was not found on this system. Install it (e.g. `brew install python@3.11`) and relaunch.'
    );
  }

  console.log('[setup] creating venv at', venvDir, 'using', systemPython);
  await spawnAsync(systemPython, ['-m', 'venv', venvDir]);

  const requirementsPath = resourcePath('requirements.txt');
  console.log('[setup] installing requirements from', requirementsPath);
  await spawnAsync(pythonBin, ['-m', 'pip', 'install', '--upgrade', 'pip']);
  await spawnAsync(pythonBin, ['-m', 'pip', 'install', '-r', requirementsPath]);
  await spawnAsync(pythonBin, ['-m', 'spacy', 'download', 'en_core_web_sm']);

  // Pre-warm Docling so the first server boot doesn't pay the
  // Hugging Face model download cost on the critical path.
  console.log('[setup] pre-warming Docling models...');
  await spawnAsync(pythonBin, [
    '-c',
    'from docling.document_converter import DocumentConverter; DocumentConverter()',
  ]);

  return pythonBin;
}

function startPythonServer(pythonBin) {
  const serverPath = resourcePath('server_docling.py');
  console.log('[server] starting Docling server:', serverPath);

  const serverDir = path.dirname(serverPath);
  serverProcess = spawn(
    pythonBin,
    ['-u', '-m', 'uvicorn', 'server_docling:app', '--host', '127.0.0.1', '--port', '8000'],
    {
      cwd: serverDir,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: {
        ...process.env,
        PYTHONPATH: serverDir + (process.env.PYTHONPATH ? `:${process.env.PYTHONPATH}` : ''),
      },
    }
  );

  serverProcess.stdout.on('data', (d) => console.log(`[server] ${d}`));
  serverProcess.stderr.on('data', (d) => console.error(`[server] ${d}`));
  serverProcess.on('close', (code) =>
    console.log(`[server] process exited with code ${code}`)
  );
  serverProcess.on('error', (err) =>
    console.error('[server] failed to start:', err)
  );
}

function stopPythonServer() {
  if (serverProcess) {
    serverProcess.kill('SIGTERM');
    serverProcess = null;
  }
}

async function checkDocling() {
  try {
    const http = require('http');
    return await new Promise((resolve) => {
      const req = http.get('http://localhost:8000/health', (res) => {
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

async function waitForDocling(timeoutMs = 120000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await checkDocling()) return true;
    await new Promise((r) => setTimeout(r, 1000));
  }
  return false;
}

// ---------------- app lifecycle ----------------

app.whenReady().then(async () => {
  // If Docling is already reachable (e.g. user is running docker compose), just use it.
  if (await checkDocling()) {
    console.log('[startup] Docling already reachable on :8000, skipping host setup');
    createWindow();
    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
    return;
  }

  const venvDir = path.join(app.getPath('userData'), 'venv');
  const venvExists = fs.existsSync(venvPython(venvDir));

  if (!venvExists) {
    const choice = await dialog.showMessageBox({
      type: 'info',
      title: 'First-time setup',
      message: 'Focus Reader needs to install its Python dependencies.',
      detail:
        'This one-time setup downloads ~1 GB of model files and can take 5–10 minutes.\n\nThe main window will open once setup completes.',
      buttons: ['Install', 'Quit'],
      defaultId: 0,
      cancelId: 1,
    });
    if (choice.response === 1) {
      app.quit();
      return;
    }
  }

  let pythonBin;
  try {
    pythonBin = await ensurePythonEnv();
  } catch (err) {
    await dialog.showMessageBox({
      type: 'error',
      title: 'Setup failed',
      message: String(err.message || err),
      detail:
        'You can also run the backend in Docker as a fallback:\n  docker compose up -d docling kokoro',
    });
    app.quit();
    return;
  }

  startPythonServer(pythonBin);

  // First boot can take a few minutes if Docling still has to download
  // its Hugging Face weights — give it 10 min before warning the user.
  const ready = await waitForDocling(600000);
  if (!ready) {
    await dialog.showMessageBox({
      type: 'warning',
      title: 'Docling did not start',
      message: 'The local Docling server failed to come up on port 8000.',
      detail:
        'It may still be loading models in the background. Wait a minute and try opening a PDF; if it still fails, check the Electron console log or run `docker compose up -d docling kokoro` as a fallback.',
    });
  }

  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
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
