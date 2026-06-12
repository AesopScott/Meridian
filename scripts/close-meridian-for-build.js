'use strict';

const { execFileSync } = require('node:child_process');
const path = require('node:path');

const repoRoot = path.resolve(__dirname, '..');
const repoRootLower = repoRoot.toLowerCase();
const packagedName = 'meridian.exe';
const portableNamePattern = /^meridian-\d+\.\d+\.\d+-x64\.exe$/i;
const ownPid = process.pid;

function normalizeCommandLine(value = '') {
  return String(value || '').replace(/\//g, '\\').toLowerCase();
}

function isMeridianBuildProcess(processInfo, root = repoRootLower) {
  const name = String(processInfo.Name || processInfo.ProcessName || '').toLowerCase();
  const commandLine = normalizeCommandLine(processInfo.CommandLine || '');
  const executable = normalizeCommandLine(processInfo.ExecutablePath || '');
  const basename = path.basename(executable || name).toLowerCase();

  if (Number(processInfo.ProcessId) === ownPid) return false;
  if (!['electron.exe', 'node.exe', packagedName].includes(name) && !portableNamePattern.test(name) && !portableNamePattern.test(basename)) {
    return false;
  }

  const pointsAtRepo = commandLine.includes(root) || executable.includes(root);
  const isPackagedMeridian = basename === packagedName || portableNamePattern.test(basename) || commandLine.includes('\\meridian.exe');
  const isRepoElectron = name === 'electron.exe' && pointsAtRepo;
  const isRepoNodeElectron = name === 'node.exe' && pointsAtRepo && (
    commandLine.includes('\\node_modules\\.bin\\electron') ||
    commandLine.includes('\\node_modules\\electron\\') ||
    commandLine.includes('\\electron\\cli.js')
  );

  return isPackagedMeridian || isRepoElectron || isRepoNodeElectron;
}

function listWindowsProcesses({ execFile = execFileSync } = {}) {
  if (process.platform !== 'win32') return [];
  const output = execFile('powershell.exe', [
    '-NoProfile',
    '-Command',
    'Get-CimInstance Win32_Process | Where-Object { $_.Name -in @("electron.exe","node.exe","Meridian.exe") -or $_.Name -like "Meridian-*.exe" } | Select-Object ProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Compress',
  ], { encoding: 'utf8', windowsHide: true });
  const trimmed = output.trim();
  if (!trimmed) return [];
  const parsed = JSON.parse(trimmed);
  return Array.isArray(parsed) ? parsed : [parsed];
}

function stopProcess(processId, { execFile = execFileSync } = {}) {
  execFile('powershell.exe', [
    '-NoProfile',
    '-Command',
    `Stop-Process -Id ${Number(processId)} -Force -ErrorAction SilentlyContinue`,
  ], { stdio: 'ignore', windowsHide: true });
}

function closeMeridianForBuild({ execFile = execFileSync, root = repoRootLower } = {}) {
  const candidates = listWindowsProcesses({ execFile })
    .filter((processInfo) => isMeridianBuildProcess(processInfo, root));
  candidates.forEach((processInfo) => stopProcess(processInfo.ProcessId, { execFile }));
  return candidates;
}

if (require.main === module) {
  const closed = closeMeridianForBuild();
  if (closed.length) {
    console.log(`Closed ${closed.length} Meridian process${closed.length === 1 ? '' : 'es'} before build.`);
  }
}

module.exports = {
  closeMeridianForBuild,
  isMeridianBuildProcess,
  listWindowsProcesses,
  normalizeCommandLine,
};
