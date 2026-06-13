'use strict';

// Meridian cockpit Electron app shell.
//
// Owns the local app runtime: starts the Meridian model bridge when needed,
// opens a desktop window for the cockpit UI, and shuts down only bridge
// processes that this app launched.
//
// Secure defaults:
//   - loadFile() of a local path only (no remote URL load).
//   - contextIsolation: true and nodeIntegration: false in the renderer.
//   - sandbox: true and webSecurity: true.
//   - will-navigate is blocked except to the local UI file.
//   - window.open / target=_blank is denied (V1 cockpit is observation-only).

const { app, BrowserWindow } = require('electron');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { pathToFileURL } = require('node:url');

const UI_FILE = path.resolve(__dirname, '..', 'index.html');
const UI_URL = pathToFileURL(UI_FILE).toString();
const BRIDGE_HOST = process.env.MERIDIAN_MODEL_HOST || '127.0.0.1';
const BRIDGE_PORT = Number(process.env.MERIDIAN_MODEL_PORT || 8767);
const BRIDGE_PROTOCOL = 'http';
const BRIDGE_HEALTH_URL = `${BRIDGE_PROTOCOL}://${BRIDGE_HOST}:${BRIDGE_PORT}/bridge/health`;
const EXPECTED_BRIDGE_VERSION = 'local-bridge-routes-v4';
const BRIDGE_SCRIPT = path.resolve(__dirname, '..', 'scripts', 'meridian-model-bridge.js');
const BRIDGE_LOCAL_COMMANDS = ['/clear', '/status', '/skills', '/debug', '/restart-bridge'];

let ownedBridgeProcess = null;
let bridgeSupervisorActive = false;
let stoppingOwnedBridge = false;
let bridgeRespawnTimer = null;

function buildCommandRegistryRows() {
  return BRIDGE_LOCAL_COMMANDS.map((name) => ({
    name,
    provenance: 'local:meridian-command',
  }));
}

function looksLikeMeridianRoot(candidate) {
  if (!candidate) return false;
  try {
    return (
      fs.existsSync(path.join(candidate, 'package.json')) &&
      fs.existsSync(path.join(candidate, 'scripts', 'meridian-model-bridge.js')) &&
      fs.existsSync(path.join(candidate, 'meridian_core'))
    );
  } catch {
    return false;
  }
}

function resolveModelCwd(baseEnv = process.env, appRoot = path.resolve(__dirname, '..')) {
  if (baseEnv.MERIDIAN_MODEL_CWD && looksLikeMeridianRoot(baseEnv.MERIDIAN_MODEL_CWD)) {
    return baseEnv.MERIDIAN_MODEL_CWD;
  }

  const candidates = [];
  if (baseEnv.PORTABLE_EXECUTABLE_DIR) {
    candidates.push(path.resolve(baseEnv.PORTABLE_EXECUTABLE_DIR, '..'));
    candidates.push(baseEnv.PORTABLE_EXECUTABLE_DIR);
  }
  candidates.push(appRoot);
  candidates.push(process.cwd());

  return candidates.find(looksLikeMeridianRoot) || appRoot;
}

function createCockpitWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    title: 'Meridian Cockpit',
    backgroundColor: '#0f111a',
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
    },
  });

  win.webContents.on('will-navigate', (event, navUrl) => {
    if (navUrl !== UI_URL) {
      event.preventDefault();
    }
  });

  win.webContents.setWindowOpenHandler(() => {
    return { action: 'deny' };
  });

  win.loadFile(UI_FILE);
  return win;
}

function getBridgeLogPaths(electronApp = app) {
  const logDir = path.join(electronApp.getPath('userData'), 'logs');
  return {
    logDir,
    stdoutPath: path.join(logDir, 'meridian-model-bridge.stdout.log'),
    stderrPath: path.join(logDir, 'meridian-model-bridge.stderr.log'),
  };
}

function bridgeRuntimePath(baseEnv = process.env) {
  const pathKey = Object.keys(baseEnv).find((key) => key.toLowerCase() === 'path') || 'Path';
  const delimiter = path.delimiter;
  const originalSegments = String(baseEnv[pathKey] || '')
    .split(delimiter)
    .map((item) => item.trim())
    .filter(Boolean);
  const segments = originalSegments.slice();
  const lowerSegments = new Set(segments.map((item) => item.toLowerCase()));
  const addedSegments = [];
  const appendIfMissing = (item) => {
    if (!item || lowerSegments.has(item.toLowerCase())) return;
    segments.push(item);
    lowerSegments.add(item.toLowerCase());
    addedSegments.push(item);
  };

  if (process.platform === 'win32') {
    const home = os.homedir();
    const appData = baseEnv.APPDATA || path.join(home, 'AppData', 'Roaming');
    const localAppData = baseEnv.LOCALAPPDATA || path.join(home, 'AppData', 'Local');
    appendIfMissing(path.join(appData, 'npm'));
    appendIfMissing(path.join(localAppData, 'Microsoft', 'WindowsApps'));
    appendIfMissing('C:\\Program Files\\nodejs');
  }

  return {
    pathKey,
    value: segments.join(delimiter),
    addedSegments,
    originalSegmentCount: originalSegments.length,
    normalizedSegmentCount: segments.length,
    sampleHead: segments.slice(0, 4),
    sampleTail: segments.slice(-4),
  };
}

function persistBridgeRuntimeVisibility(logDir, runtimePath) {
  const visibilityPath = path.join(logDir, 'meridian-model-bridge-runtime-env.json');
  const visibility = {
    recordedAt: new Date().toISOString(),
    pathEnvKey: runtimePath.pathKey,
    platform: process.platform,
    delimiter: path.delimiter,
    originalPathSegmentCount: Number.isInteger(runtimePath.originalSegmentCount) ? runtimePath.originalSegmentCount : 0,
    normalizedPathSegmentCount: Number.isInteger(runtimePath.normalizedSegmentCount)
      ? runtimePath.normalizedSegmentCount
      : runtimePath.value.split(path.delimiter).filter(Boolean).length,
    appendedSegments: runtimePath.addedSegments || [],
    pathValue: runtimePath.value,
    normalizedTail: runtimePath.sampleTail || [],
  };
  try {
    fs.writeFileSync(visibilityPath, JSON.stringify(visibility, null, 2), 'utf8');
  } catch {
    return null;
  }
  return visibilityPath;
}

function buildDiagnosticSignalFailure(reason, extra = {}) {
  return {
    ok: false,
    status: 'fail',
    reason,
    ...extra,
  };
}

function buildDiagnosticSignalWarning(reason, extra = {}) {
  return {
    ok: true,
    status: 'warn',
    reason,
    degraded: true,
    ...extra,
  };
}

function collectPathStartupSignal(baseEnv = process.env) {
  const runtimePath = bridgeRuntimePath(baseEnv);
  return {
    kind: 'path',
    ok: true,
    status: 'pass',
    pathEnvKey: runtimePath.pathKey,
    originalPathSegmentCount: runtimePath.originalSegmentCount,
    normalizedPathSegmentCount: runtimePath.normalizedSegmentCount,
    appendedSegments: runtimePath.addedSegments || [],
    sampleHead: runtimePath.sampleHead || [],
    sampleTail: runtimePath.sampleTail || [],
  };
}

function collectStorageStartupSignal(electronApp = app) {
  const { logDir } = getBridgeLogPaths(electronApp);
  const marker = path.join(logDir, `meridian-startup-${Date.now()}.probe`);
  try {
    fs.mkdirSync(logDir, { recursive: true });
    fs.writeFileSync(marker, 'ok');
    fs.unlinkSync(marker);
    return {
      kind: 'storage',
      ok: true,
      status: 'pass',
      logDir,
    };
  } catch (error) {
    return {
      kind: 'storage',
      ok: false,
      status: 'fail',
      reason: error?.message || 'storage probe failed',
      logDir,
    };
  }
}

function fetchBridgeJson(route, { request = http.get, timeoutMs = 250 } = {}) {
  const url = `${BRIDGE_PROTOCOL}://${BRIDGE_HOST}:${BRIDGE_PORT}${route}`;
  return new Promise((resolve) => {
    const req = request(url, (res) => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => {
        body += chunk;
      });
      res.on('end', () => {
        let payload = null;
        try {
          payload = JSON.parse(body);
        } catch {
          payload = null;
        }
        if (res.statusCode !== 200) {
          resolve({
            ok: false,
            statusCode: res.statusCode,
            error: payload?.error || `bridge returned HTTP ${res.statusCode}`,
            payload,
          });
          return;
        }
        if (!payload || typeof payload !== 'object') {
          resolve({
            ok: false,
            statusCode: res.statusCode,
            error: 'bridge payload was not valid JSON',
          });
          return;
        }
        resolve({ ok: true, statusCode: res.statusCode, payload });
      });
    });
    req.on('error', () => {
      resolve({ ok: false, statusCode: null, error: 'bridge request failed' });
    });
    req.setTimeout(timeoutMs, () => {
      req.destroy();
      resolve({ ok: false, statusCode: null, error: 'bridge request timeout' });
    });
  });
}

async function collectAuthStartupSignal({ request = http.get, timeoutMs = 250 } = {}) {
  const response = await fetchBridgeJson('/bridge/models', { request, timeoutMs });
  if (!response.ok) {
    return buildDiagnosticSignalFailure(response.error || 'models endpoint not reachable', { status: 'unreachable' });
  }
  const models = response.payload?.models;
  const codex = Array.isArray(models) ? models.find((entry) => String(entry?.backend).toLowerCase() === 'codex') : null;
  if (!codex) {
    return buildDiagnosticSignalFailure('models snapshot missing codex entry', { status: 'fail' });
  }
  const installed = Boolean(codex.installed);
  const hasAuthVisibility = Boolean(codex.setupHint);
  return {
    kind: 'auth',
    ok: installed,
    status: installed ? (hasAuthVisibility ? 'pass' : 'warn') : 'fail',
    installed,
    hasAuthVisibility,
    backend: 'codex',
    cli: codex.cli,
  };
}

async function collectSkillRegistrySignal({ request = http.get, timeoutMs = 250 } = {}) {
  const [modelsResponse, fileMapResponse] = await Promise.all([
    fetchBridgeJson('/bridge/models', { request, timeoutMs }),
    fetchBridgeJson('/bridge/filemap', { request, timeoutMs }),
  ]);

  if (!modelsResponse.ok) {
    return buildDiagnosticSignalFailure(modelsResponse.error || 'models endpoint not reachable', { status: 'models-unreachable' });
  }
  if (!fileMapResponse.ok) {
    return buildDiagnosticSignalFailure(fileMapResponse.error || 'filemap endpoint not reachable', { status: 'filemap-unreachable' });
  }
  const hasBridgeCommandRegistry = Object.prototype.hasOwnProperty.call(fileMapResponse.payload || {}, 'commandRegistry');
  const fileMapRows = Array.isArray(fileMapResponse.payload?.commandRegistry)
    ? fileMapResponse.payload.commandRegistry
    : (hasBridgeCommandRegistry ? [] : buildCommandRegistryRows());
  const inferredModelRows = Array.isArray(modelsResponse.payload?.models)
    ? modelsResponse.payload.models
      .map((model) => ({
        name: `/${String(model?.backend || model?.label || '').trim() || 'backend'}`,
        provenance: 'backend:models',
      }))
      .filter((row) => row.name !== '//')
    : [];
  const registryRows = [
    ...fileMapRows,
    ...inferredModelRows,
  ];
  const hasModels = Array.isArray(modelsResponse.payload?.models) && modelsResponse.payload.models.length > 0;
  const hasStatusRow = registryRows.some((row) => String(row?.name || '').startsWith('/status'));
  const hasBackendModelRows = registryRows.some((row) => String(row?.provenance || '').includes('backend:models'));
  if (!registryRows.length) {
    return buildDiagnosticSignalWarning('skill registry payload is empty', { status: 'empty-registry', modelEntries: modelsResponse.payload?.models?.length || 0 });
  }
  if (!hasModels) {
    return buildDiagnosticSignalFailure('models snapshot missing models array', { status: 'models-missing', modelEntries: 0 });
  }
  if (!hasStatusRow) {
    return buildDiagnosticSignalWarning('skill registry missing /status row', { status: 'missing-status-row' });
  }
  if (!hasBackendModelRows) {
    return buildDiagnosticSignalWarning('skill registry missing backend model rows', { status: 'missing-model-rows' });
  }
  return {
    kind: 'skillRegistry',
    ok: true,
    status: 'pass',
    registryRows: registryRows.length,
    modelRows: modelsResponse.payload.models.length,
    sampleRows: registryRows.slice(0, 3).map((row) => ({
      name: row?.name || '',
      provenance: row?.provenance || '',
    })),
  };
}

async function collectStartupDiagnostics({
  electronApp = app,
  request = http.get,
  timeoutMs = 250,
  includeBridgeSignals = false,
  bridgeReady = false,
  env = process.env,
} = {}) {
  const startupDiagnostics = {
    path: collectPathStartupSignal(env),
    storage: collectStorageStartupSignal(electronApp),
    auth: {
      kind: 'auth',
      ok: null,
      status: includeBridgeSignals && bridgeReady ? 'not-started' : 'skipped',
      reason: includeBridgeSignals && bridgeReady ? 'auth probe not run' : 'bridge probes disabled',
    },
    skillRegistry: {
      kind: 'skillRegistry',
      ok: null,
      status: includeBridgeSignals && bridgeReady ? 'not-started' : 'skipped',
      reason: includeBridgeSignals && bridgeReady ? 'skill registry probe not run' : 'bridge probes disabled',
    },
  };

  if (!includeBridgeSignals || !bridgeReady) {
    return startupDiagnostics;
  }

  const [authSignal, skillRegistrySignal] = await Promise.all([
    collectAuthStartupSignal({ request, timeoutMs }).catch((error) => buildDiagnosticSignalFailure(error?.message || 'auth probe failed', { status: 'error' })),
    collectSkillRegistrySignal({ request, timeoutMs }).catch((error) => buildDiagnosticSignalFailure(error?.message || 'registry probe failed', { status: 'error' })),
  ]);
  startupDiagnostics.auth = authSignal;
  startupDiagnostics.skillRegistry = skillRegistrySignal;
  return startupDiagnostics;
}

function bridgeHealthCheck({ request = http.get, timeoutMs = 700 } = {}) {
  return new Promise((resolve) => {
    const req = request(BRIDGE_HEALTH_URL, (res) => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => {
        body += chunk;
      });
      res.on('end', () => {
        let parsed;
        try {
          parsed = JSON.parse(body);
        } catch {
          parsed = null;
        }

        if (res.statusCode !== 200) {
          if (parsed && typeof parsed === 'object') {
            resolve({
              ...parsed,
              ok: false,
              state: parsed.state || 'degraded',
              statusCode: res.statusCode,
              error: parsed.error || `bridge returned HTTP ${res.statusCode}`,
            });
            return;
          }
          resolve({
            ok: false,
            state: 'degraded',
            statusCode: res.statusCode,
            error: `bridge returned HTTP ${res.statusCode}`,
          });
          return;
        }
        if (!parsed || typeof parsed !== 'object') {
          resolve({ ok: false, state: 'degraded', error: 'bridge health payload was not valid JSON' });
          return;
        }
        resolve(parsed);
      });
    });
    req.on('error', () => resolve({
      ok: false,
      state: 'unreachable',
      error: 'bridge health request failed',
    }));
    req.setTimeout(timeoutMs, () => {
      req.destroy();
      resolve({ ok: false, state: 'unreachable', error: 'bridge health request timeout' });
    });
  });
}

function normalizeHealthResult(result) {
  if (typeof result === 'boolean') return { ok: result };
  if (!result || typeof result !== 'object') return { ok: false };
  return { ok: Boolean(result.ok), ...result };
}

function isBridgeReady(result) {
  const status = normalizeHealthResult(result);
  if (status.state && status.state !== 'healthy' && status.ok === true) {
    return false;
  }
  if (status.version && status.version !== EXPECTED_BRIDGE_VERSION) return false;
  return status.ok === true;
}

function isBridgeStarting(result) {
  const status = normalizeHealthResult(result);
  return status.state === 'starting';
}

async function waitForBridgeReady({ attempts = 30, intervalMs = 200, healthCheck = bridgeHealthCheck, initialHealth } = {}) {
  let last;
  const hasInitialHealth = typeof initialHealth !== 'undefined';
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    let health;
    try {
      health = hasInitialHealth && attempt === 0 ? initialHealth : await healthCheck();
    } catch (error) {
      health = {
        ok: false,
        state: 'unreachable',
        error: error?.message || 'bridge health request failed',
      };
    }
    last = normalizeHealthResult(health);
    if (isBridgeReady(health)) {
      return {
        ready: true,
        attempts: attempt + 1,
        last,
      };
    }
    if (hasInitialHealth && attempt === 0) continue;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  return {
    ready: false,
    attempts,
    last,
  };
}

async function ensureModelBridge({
  electronApp = app,
  healthCheck = bridgeHealthCheck,
  spawnProcess = spawn,
  bridgeScript = BRIDGE_SCRIPT,
  nodeRuntime = process.execPath,
  startupDiagnosticsEnabled = false,
  startupDiagnosticRequest = http.get,
  startupDiagnosticTimeoutMs = 250,
  supervise = bridgeSupervisorActive,
  respawnDelayMs = 750,
  } = {}) {
  if (supervise) {
    bridgeSupervisorActive = true;
    stoppingOwnedBridge = false;
  }
  const diagnosticsBase = {
    env: process.env,
    includeBridgeSignals: startupDiagnosticsEnabled,
    request: startupDiagnosticRequest,
    timeoutMs: startupDiagnosticTimeoutMs,
  };
  const initialHealth = await healthCheck();
  if (isBridgeReady(initialHealth)) {
    const startupDiagnostics = await collectStartupDiagnostics({
      ...diagnosticsBase,
      electronApp,
      bridgeReady: true,
      env: process.env,
    });
    return {
      started: false,
      alreadyRunning: true,
      process: null,
      startupDiagnostics,
    };
  }
  if (isBridgeStarting(initialHealth)) {
    const startup = await waitForBridgeReady({ healthCheck });
    if (startup.ready) {
      const startupDiagnostics = await collectStartupDiagnostics({
        ...diagnosticsBase,
        electronApp,
        bridgeReady: true,
        env: process.env,
      });
      return {
        started: false,
        alreadyRunning: true,
        process: null,
        startup,
        startupDiagnostics,
      };
    }
  }

  const { logDir, stdoutPath, stderrPath } = getBridgeLogPaths(electronApp);
  fs.mkdirSync(logDir, { recursive: true });
  const stdout = fs.openSync(stdoutPath, 'a');
  const stderr = fs.openSync(stderrPath, 'a');
  const runtimePath = bridgeRuntimePath(process.env);
  const runtimeVisibilityPath = persistBridgeRuntimeVisibility(logDir, runtimePath);
  const modelCwd = resolveModelCwd(process.env, path.resolve(__dirname, '..'));
  const childEnv = {
    ...process.env,
    ELECTRON_RUN_AS_NODE: '1',
    MERIDIAN_APP_SUPERVISED: supervise ? '1' : '0',
    MERIDIAN_MODEL_HOST: BRIDGE_HOST,
    MERIDIAN_MODEL_PORT: String(BRIDGE_PORT),
    MERIDIAN_MODEL_CWD: modelCwd,
    [runtimePath.pathKey]: runtimePath.value,
  };
  const child = spawnProcess(nodeRuntime, [bridgeScript], {
    cwd: path.resolve(__dirname, '..'),
    detached: false,
    env: childEnv,
    stdio: ['ignore', stdout, stderr],
    windowsHide: true,
  });

  ownedBridgeProcess = child;
  stoppingOwnedBridge = false;
  child.once('exit', (code, signal) => {
    if (ownedBridgeProcess === child) ownedBridgeProcess = null;
    if (supervise && bridgeSupervisorActive && !stoppingOwnedBridge) {
      scheduleBridgeRespawn({
        electronApp,
        healthCheck,
        spawnProcess,
        bridgeScript,
        nodeRuntime,
        startupDiagnosticsEnabled,
        startupDiagnosticRequest,
        startupDiagnosticTimeoutMs,
        respawnDelayMs,
        reason: `bridge exited with code ${code ?? 'unknown'}${signal ? ` signal ${signal}` : ''}`,
      });
    }
  });

  const startup = await waitForBridgeReady({ healthCheck, initialHealth });
  if (!startup.ready) {
    console.error(
      `[meridian-runtime] bridge startup incomplete after ${startup.attempts} attempts; last=${JSON.stringify(startup.last)}`,
    );
  }

  const startupDiagnostics = await collectStartupDiagnostics({
    ...diagnosticsBase,
    electronApp,
    bridgeReady: startup.ready,
    env: childEnv,
  });

  return {
    started: true,
    alreadyRunning: false,
    process: child,
    runtimeVisibilityPath,
    runtimePath,
    stdoutPath,
    stderrPath,
    ready: startup.ready,
    attempts: startup.attempts,
    startup,
    startupDiagnostics,
  };
}

function scheduleBridgeRespawn({
  electronApp = app,
  healthCheck = bridgeHealthCheck,
  spawnProcess = spawn,
  bridgeScript = BRIDGE_SCRIPT,
  nodeRuntime = process.execPath,
  startupDiagnosticsEnabled = true,
  startupDiagnosticRequest = http.get,
  startupDiagnosticTimeoutMs = 250,
  respawnDelayMs = 750,
  reason = 'bridge exited',
} = {}) {
  if (!bridgeSupervisorActive || bridgeRespawnTimer) return false;
  console.warn(`[meridian-runtime] scheduling bridge restart: ${reason}`);
  bridgeRespawnTimer = setTimeout(async () => {
    bridgeRespawnTimer = null;
    if (!bridgeSupervisorActive || stoppingOwnedBridge) return;
    try {
      await ensureModelBridge({
        electronApp,
        healthCheck,
        spawnProcess,
        bridgeScript,
        nodeRuntime,
        startupDiagnosticsEnabled,
        startupDiagnosticRequest,
        startupDiagnosticTimeoutMs,
        supervise: true,
        respawnDelayMs,
      });
    } catch (error) {
      console.error(`[meridian-runtime] bridge restart failed: ${error?.message || error}`);
      scheduleBridgeRespawn({
        electronApp,
        healthCheck,
        spawnProcess,
        bridgeScript,
        nodeRuntime,
        startupDiagnosticsEnabled,
        startupDiagnosticRequest,
        startupDiagnosticTimeoutMs,
        respawnDelayMs: Math.max(respawnDelayMs, 2000),
        reason: 'previous bridge restart failed',
      });
    }
  }, respawnDelayMs);
  if (typeof bridgeRespawnTimer.unref === 'function') bridgeRespawnTimer.unref();
  return true;
}

function stopOwnedBridge() {
  bridgeSupervisorActive = false;
  stoppingOwnedBridge = true;
  if (bridgeRespawnTimer) {
    clearTimeout(bridgeRespawnTimer);
    bridgeRespawnTimer = null;
  }
  if (!ownedBridgeProcess || ownedBridgeProcess.killed) return false;
  const child = ownedBridgeProcess;
  ownedBridgeProcess = null;
  child.kill();
  return true;
}

async function startMeridianApp() {
  bridgeSupervisorActive = true;
  stoppingOwnedBridge = false;
  await ensureModelBridge({ startupDiagnosticsEnabled: true, supervise: true });
  createCockpitWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createCockpitWindow();
    }
  });
}

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopOwnedBridge();
});

if (require.main === module) {
  app.whenReady().then(startMeridianApp);
}

module.exports = {
  BRIDGE_HEALTH_URL,
  BRIDGE_SCRIPT,
  createCockpitWindow,
  ensureModelBridge,
  getBridgeLogPaths,
  bridgeRuntimePath,
  looksLikeMeridianRoot,
  resolveModelCwd,
  startMeridianApp,
  collectStartupDiagnostics,
  bridgeHealthCheck,
  stopOwnedBridge,
  UI_FILE,
  UI_URL,
  waitForBridgeReady,
};
