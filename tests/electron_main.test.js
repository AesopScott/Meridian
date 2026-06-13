'use strict';

const assert = require('node:assert/strict');
const EventEmitter = require('node:events');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const mainPath = path.resolve(__dirname, '..', 'electron', 'main.js');
const originalLoad = Module._load;

function loadMainWithElectronMock() {
  const electronMock = {
    app: {
      getPath(name) {
        assert.equal(name, 'userData');
        return fs.mkdtempSync(path.join(os.tmpdir(), 'meridian-electron-test-'));
      },
      on() {},
      quit() {},
      whenReady() {
        return Promise.resolve();
      },
    },
    BrowserWindow: class BrowserWindow {
      constructor(options) {
        this.options = options;
        this.webContents = {
          on() {},
          setWindowOpenHandler() {},
        };
      }

      loadFile(file) {
        this.loadedFile = file;
      }

      static getAllWindows() {
        return [];
      }
    },
  };

  delete require.cache[mainPath];
  Module._load = function loadWithElectronMock(request, parent, isMain) {
    if (request === 'electron') return electronMock;
    return originalLoad.call(this, request, parent, isMain);
  };
  try {
    return require(mainPath);
  } finally {
    Module._load = originalLoad;
  }
}

function mockBridgeRequest(responses) {
  return (url, handler) => {
    const request = new EventEmitter();
    request.setTimeout = () => {};
    request.destroy = () => {};

    const route = String(url).match(/\/bridge\/[^/?#]+/i)?.[0] || String(url);
    const payload = responses[route] || {};
    const response = new EventEmitter();
    response.statusCode = typeof payload.statusCode === 'number' ? payload.statusCode : 200;
    response.setEncoding = () => {};

    process.nextTick(() => {
      handler(response);
      const body = typeof payload.body === 'string' ? payload.body : JSON.stringify(payload.body || {});
      response.emit('data', body);
      response.emit('end');
    });

    return request;
  };
}

function fakeChildProcess() {
  const child = new EventEmitter();
  child.killed = false;
  child.kill = () => {
    child.killed = true;
    child.emit('exit', 0);
    return true;
  };
  return child;
}

test('runtime exports stable local UI and bridge paths', () => {
  const main = loadMainWithElectronMock();

  assert.equal(main.BRIDGE_HEALTH_URL, 'http://127.0.0.1:8767/bridge/health');
  assert.equal(path.basename(main.UI_FILE), 'index.html');
  assert.equal(path.basename(main.BRIDGE_SCRIPT), 'meridian-model-bridge.js');
  assert.match(main.UI_URL, /^file:\/\//);
});

test('ensureModelBridge reuses an already running bridge', async () => {
  const main = loadMainWithElectronMock();
  let spawnCount = 0;

  const result = await main.ensureModelBridge({
    healthCheck: async () => true,
    spawnProcess: () => {
      spawnCount += 1;
      return fakeChildProcess();
    },
  });

  assert.equal(result.started, false);
  assert.equal(result.alreadyRunning, true);
  assert.equal(result.process, null);
  assert.equal(result.startupDiagnostics.path.ok, true);
  assert.equal(result.startupDiagnostics.storage.ok, true);
  assert.equal(result.startupDiagnostics.auth.status, 'skipped');
  assert.equal(result.startupDiagnostics.skillRegistry.status, 'skipped');
  assert.equal(spawnCount, 0);
});

test('ensureModelBridge starts the bridge with Electron-as-Node and log files', async () => {
  const main = loadMainWithElectronMock();
  const tempUserData = fs.mkdtempSync(path.join(os.tmpdir(), 'meridian-runtime-'));
  const electronApp = {
    getPath(name) {
      assert.equal(name, 'userData');
      return tempUserData;
    },
  };
  const child = fakeChildProcess();
  const calls = [];
  let healthChecks = 0;

  const result = await main.ensureModelBridge({
    electronApp,
    bridgeScript: 'C:\\Meridian\\scripts\\meridian-model-bridge.js',
    nodeRuntime: 'C:\\Meridian\\Meridian.exe',
    healthCheck: async () => {
      healthChecks += 1;
      return healthChecks > 1;
    },
    spawnProcess: (bin, args, options) => {
      calls.push({ bin, args, options });
      return child;
    },
  });

  assert.equal(result.started, true);
  assert.equal(result.alreadyRunning, false);
  assert.equal(result.ready, true);
  assert.equal(result.startupDiagnostics.path.ok, true);
  assert.equal(result.startupDiagnostics.storage.ok, true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].bin, 'C:\\Meridian\\Meridian.exe');
  assert.deepEqual(calls[0].args, ['C:\\Meridian\\scripts\\meridian-model-bridge.js']);
  const pathKey = Object.keys(calls[0].options.env).find((key) => key.toLowerCase() === 'path');
  const childPath = calls[0].options.env[pathKey].toLowerCase();

  assert.equal(calls[0].options.env.ELECTRON_RUN_AS_NODE, '1');
  assert.equal(calls[0].options.env.MERIDIAN_APP_SUPERVISED, '0');
  assert.equal(calls[0].options.env.MERIDIAN_MODEL_HOST, '127.0.0.1');
  assert.equal(calls[0].options.env.MERIDIAN_MODEL_PORT, '8767');
  assert.equal(path.basename(calls[0].options.env.MERIDIAN_MODEL_CWD), 'Meridian');
  assert.match(childPath, /appdata\\roaming\\npm/);
  assert.match(childPath, /microsoft\\windowsapps/);
  assert.equal(calls[0].options.windowsHide, true);
  assert.equal(fs.existsSync(path.join(tempUserData, 'logs')), true);

  assert.equal(main.stopOwnedBridge(), true);
  assert.equal(child.killed, true);
  assert.equal(main.stopOwnedBridge(), false);
});

test('ensureModelBridge can supervise bridge exits and respawn under app ownership', async () => {
  const main = loadMainWithElectronMock();
  const tempUserData = fs.mkdtempSync(path.join(os.tmpdir(), 'meridian-runtime-supervised-'));
  const children = [];
  let healthChecks = 0;

  await main.ensureModelBridge({
    electronApp: {
      getPath(name) {
        assert.equal(name, 'userData');
        return tempUserData;
      },
    },
    bridgeScript: 'C:\\Meridian\\scripts\\meridian-model-bridge.js',
    nodeRuntime: 'C:\\Meridian\\Meridian.exe',
    supervise: true,
    respawnDelayMs: 1,
    healthCheck: async () => {
      healthChecks += 1;
      return healthChecks % 2 === 0;
    },
    spawnProcess: (bin, args, options) => {
      const child = fakeChildProcess();
      child.spawn = { bin, args, options };
      children.push(child);
      return child;
    },
  });

  children[0].emit('exit', 0);
  await new Promise((resolve) => setTimeout(resolve, 15));

  assert.equal(children.length, 2);
  assert.equal(children[0].spawn.options.env.MERIDIAN_APP_SUPERVISED, '1');
  assert.equal(children[1].spawn.options.env.MERIDIAN_APP_SUPERVISED, '1');
  assert.equal(main.stopOwnedBridge(), true);
});

test('ensureModelBridge waits for an already-starting bridge to become healthy', async () => {
  const main = loadMainWithElectronMock();
  const tempUserData = fs.mkdtempSync(path.join(os.tmpdir(), 'meridian-runtime-startup-'));
  let healthChecks = 0;

  const result = await main.ensureModelBridge({
    electronApp: {
      getPath(name) {
        assert.equal(name, 'userData');
        return tempUserData;
      },
    },
    bridgeScript: 'C:\\Meridian\\scripts\\meridian-model-bridge.js',
    nodeRuntime: 'C:\\Meridian\\Meridian.exe',
    healthCheck: async () => {
      healthChecks += 1;
      if (healthChecks === 1) return { ok: false, state: 'starting', version: 'local-bridge-routes-v4' };
      return { ok: true, state: 'healthy', version: 'local-bridge-routes-v4' };
    },
  });

  assert.equal(result.started, false);
  assert.equal(result.alreadyRunning, true);
  assert.equal(result.process, null);
  assert.equal(result.startupDiagnostics.path.ok, true);
  assert.equal(healthChecks, 2);
});

test('bridgeHealthCheck preserves startup state details from non-200 responses', async () => {
  const main = loadMainWithElectronMock();
  const responseBody = {
    ok: false,
    state: 'starting',
    version: 'local-bridge-routes-v4',
    service: 'meridian-model-bridge',
    error: 'booting',
  };

  const result = await main.bridgeHealthCheck({
    timeoutMs: 5,
    request: (url, handler) => {
      const request = new EventEmitter();
      request.setTimeout = () => {};
      request.destroy = () => {};
      process.nextTick(() => {
        const response = new EventEmitter();
        response.statusCode = 503;
        response.setEncoding = () => {};
        handler(response);
        response.emit('data', JSON.stringify(responseBody));
        response.emit('end');
      });
      return request;
    },
  });

  assert.equal(result.ok, false);
  assert.equal(result.state, 'starting');
  assert.equal(result.version, 'local-bridge-routes-v4');
  assert.equal(result.statusCode, 503);
  assert.equal(result.error, 'booting');
});

test('ensureModelBridge retries when health version mismatches and treats bridge as not ready', async () => {
  const main = loadMainWithElectronMock();
  const tempUserData = fs.mkdtempSync(path.join(os.tmpdir(), 'meridian-runtime-startup-mismatch-'));
  const child = fakeChildProcess();
  let healthChecks = 0;

  const result = await main.ensureModelBridge({
    electronApp: {
      getPath(name) {
        assert.equal(name, 'userData');
        return tempUserData;
      },
    },
    bridgeScript: 'C:\\Meridian\\scripts\\meridian-model-bridge.js',
    nodeRuntime: 'C:\\Meridian\\Meridian.exe',
    healthCheck: async () => {
      healthChecks += 1;
      if (healthChecks === 1) return { ok: true, state: 'healthy', version: 'legacy-bridge-version' };
      return { ok: true, state: 'healthy', version: 'local-bridge-routes-v4' };
    },
    spawnProcess: () => child,
  });

  assert.equal(result.started, true);
  assert.equal(result.ready, true);
  assert.equal(result.startup.ready, true);
  assert.equal(result.startup.attempts, 2);
  assert.equal(healthChecks, 2);
  assert.equal(result.startup.last.version, 'local-bridge-routes-v4');
  assert.equal(result.startupDiagnostics.path.ok, true);
  assert.equal(result.startupDiagnostics.auth.status, 'skipped');
});

test('collectStartupDiagnostics reports PATH/auth/storage/skill registry checks', async () => {
  const main = loadMainWithElectronMock();
  const tempUserData = fs.mkdtempSync(path.join(os.tmpdir(), 'meridian-runtime-diagnostics-'));
  const electronApp = {
    getPath(name) {
      assert.equal(name, 'userData');
      return tempUserData;
    },
  };
  const request = mockBridgeRequest({
    '/bridge/models': {
      body: {
        ok: true,
        models: [
          {
            backend: 'codex',
            cli: 'codex',
            installed: true,
            setupHint: 'Install and sign in to the selected model CLI.',
          },
        ],
      },
    },
    '/bridge/filemap': {
      body: {
        ok: true,
        commandRegistry: [
          { name: '/status', provenance: 'backend:models' },
          { name: '/skills', provenance: 'backend:models' },
        ],
      },
    },
  });
  const diagnostics = await main.collectStartupDiagnostics({
    electronApp,
    request,
    includeBridgeSignals: true,
    bridgeReady: true,
    env: process.env,
  });

  assert.equal(diagnostics.path.ok, true);
  assert.equal(diagnostics.storage.ok, true);
  assert.equal(diagnostics.auth.ok, true);
  assert.equal(diagnostics.auth.status, 'pass');
  assert.equal(diagnostics.skillRegistry.ok, true);
  assert.equal(diagnostics.skillRegistry.status, 'pass');
  assert.equal(typeof diagnostics.auth.cli, 'string');
});

test('collectStartupDiagnostics infers runtime command registry when /bridge/filemap omits commandRegistry', async () => {
  const main = loadMainWithElectronMock();
  const tempUserData = fs.mkdtempSync(path.join(os.tmpdir(), 'meridian-runtime-diagnostics-inferred-'));
  const electronApp = {
    getPath(name) {
      assert.equal(name, 'userData');
      return tempUserData;
    },
  };
  const request = mockBridgeRequest({
    '/bridge/models': {
      body: {
        ok: true,
        models: [
          {
            backend: 'codex',
            cli: 'codex',
            installed: true,
            setupHint: 'Install and sign in to the selected model CLI.',
          },
        ],
      },
    },
    '/bridge/filemap': {
      body: {
        ok: true,
        focus_entries: [{ path: 'index.html', area: 'frontend' }],
      },
    },
  });
  const diagnostics = await main.collectStartupDiagnostics({
    electronApp,
    request,
    includeBridgeSignals: true,
    bridgeReady: true,
    env: process.env,
  });

  assert.equal(diagnostics.auth.ok, true);
  assert.equal(diagnostics.skillRegistry.ok, true);
  assert.equal(diagnostics.skillRegistry.status, 'pass');
});

test('collectStartupDiagnostics skips bridge probes until the bridge is marked ready', async () => {
  const main = loadMainWithElectronMock();
  const tempUserData = fs.mkdtempSync(path.join(os.tmpdir(), 'meridian-runtime-skip-'));
  let requestCalled = false;
  const request = () => {
    requestCalled = true;
    throw new Error('bridge probe should not run');
  };

  const diagnostics = await main.collectStartupDiagnostics({
    electronApp: {
      getPath(name) {
        assert.equal(name, 'userData');
        return tempUserData;
      },
    },
    request,
    includeBridgeSignals: false,
    bridgeReady: false,
    env: process.env,
  });

  assert.equal(diagnostics.path.ok, true);
  assert.equal(diagnostics.storage.ok, true);
  assert.equal(diagnostics.auth.status, 'skipped');
  assert.equal(diagnostics.skillRegistry.status, 'skipped');
  assert.equal(requestCalled, false);
});

test('collectStartupDiagnostics surfaces auth failures and skill registry warnings', async () => {
  const main = loadMainWithElectronMock();
  const tempUserData = fs.mkdtempSync(path.join(os.tmpdir(), 'meridian-runtime-fail-'));
  const electronApp = {
    getPath(name) {
      assert.equal(name, 'userData');
      return tempUserData;
    },
  };
  const request = mockBridgeRequest({
    '/bridge/models': {
      body: {
        ok: true,
        models: [
          { backend: 'max', installed: true },
        ],
      },
    },
    '/bridge/filemap': {
      body: {
        ok: true,
        commandRegistry: [
          { name: '/skills', provenance: 'backend:models' },
        ],
      },
    },
  });

  const diagnostics = await main.collectStartupDiagnostics({
    electronApp,
    request,
    includeBridgeSignals: true,
    bridgeReady: true,
    env: process.env,
  });

  assert.equal(diagnostics.auth.ok, false);
  assert.equal(diagnostics.auth.status, 'fail');
  assert.equal(diagnostics.auth.reason, 'models snapshot missing codex entry');
  assert.equal(diagnostics.skillRegistry.ok, true);
  assert.equal(diagnostics.skillRegistry.status, 'missing-status-row');
  assert.equal(diagnostics.skillRegistry.degraded, true);
});

test('collectStartupDiagnostics captures storage probe failure', async () => {
  const main = loadMainWithElectronMock();
  const tempUserData = fs.mkdtempSync(path.join(os.tmpdir(), 'meridian-runtime-storage-'));
  const blockedUserDataPath = path.join(tempUserData, 'blocked-location.json');
  fs.writeFileSync(blockedUserDataPath, 'blocked');

  const diagnostics = await main.collectStartupDiagnostics({
    electronApp: {
      getPath(name) {
        assert.equal(name, 'userData');
        return blockedUserDataPath;
      },
    },
    request: mockBridgeRequest({}),
    includeBridgeSignals: false,
    bridgeReady: false,
    env: process.env,
  });

  assert.equal(diagnostics.storage.ok, false);
  assert.equal(diagnostics.storage.status, 'fail');
  const reason = String(diagnostics.storage.reason || '');
  assert.equal(/not a directory|ENOTDIR|EEXIST/i.test(reason), true);
});

test('bridgeRuntimePath preserves existing PATH entries and appends Windows CLI locations', () => {
  const main = loadMainWithElectronMock();
  const result = main.bridgeRuntimePath({
    Path: 'C:\\Existing',
    APPDATA: 'C:\\Users\\scott\\AppData\\Roaming',
    LOCALAPPDATA: 'C:\\Users\\scott\\AppData\\Local',
  });

  assert.equal(result.pathKey, 'Path');
  assert.equal(result.value.split(path.delimiter)[0], 'C:\\Existing');
  assert.match(result.value, /AppData\\Roaming\\npm/);
  assert.match(result.value, /Microsoft\\WindowsApps/);
});

test('resolveModelCwd maps a portable dist launch back to the repo root', () => {
  const main = loadMainWithElectronMock();
  const repoRoot = path.resolve(__dirname, '..');
  const distDir = path.join(repoRoot, 'dist');
  const resolved = main.resolveModelCwd({ PORTABLE_EXECUTABLE_DIR: distDir }, 'C:\\Temp\\extracted\\resources\\app');

  assert.equal(resolved, repoRoot);
});

test('createCockpitWindow keeps the renderer sandboxed', () => {
  const main = loadMainWithElectronMock();
  const win = main.createCockpitWindow();

  assert.equal(win.options.title, 'Meridian Cockpit');
  assert.equal(win.options.webPreferences.contextIsolation, true);
  assert.equal(win.options.webPreferences.nodeIntegration, false);
  assert.equal(win.options.webPreferences.sandbox, true);
  assert.equal(win.loadedFile, main.UI_FILE);
});
