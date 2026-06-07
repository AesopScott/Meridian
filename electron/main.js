'use strict';

// Meridian cockpit Electron app shell.
//
// Opens a desktop window that loads the actual Meridian cockpit UI entrypoint.
// The Bifrost preview writer remains available for backend snapshot proofs, but
// app startup must not regenerate or replace the working UI surface.
//
// Secure defaults:
//   - loadFile() of a local path only (no remote URL load).
//   - contextIsolation: true and nodeIntegration: false in the renderer.
//   - sandbox: true and webSecurity: true.
//   - will-navigate is blocked except to the local UI file.
//   - window.open / target=_blank is denied (V1 cockpit is observation-only).

const { app, BrowserWindow } = require('electron');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const UI_FILE = path.resolve(__dirname, '..', 'index.html');
const UI_URL = pathToFileURL(UI_FILE).toString();

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

app.whenReady().then(() => {
  createCockpitWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createCockpitWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

module.exports = {
  createCockpitWindow,
  UI_FILE,
  UI_URL,
};
