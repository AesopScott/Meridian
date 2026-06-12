'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
  closeMeridianForBuild,
  isMeridianBuildProcess,
} = require('../scripts/close-meridian-for-build');

const repoRoot = 'c:\\users\\scott\\code\\meridian';

test('isMeridianBuildProcess matches only Meridian app processes', () => {
  assert.equal(isMeridianBuildProcess({
    ProcessId: 101,
    Name: 'electron.exe',
    ExecutablePath: 'C:\\Users\\scott\\Code\\Meridian\\node_modules\\electron\\dist\\electron.exe',
    CommandLine: 'C:\\Users\\scott\\Code\\Meridian\\node_modules\\electron\\dist\\electron.exe .',
  }, repoRoot), true);

  assert.equal(isMeridianBuildProcess({
    ProcessId: 102,
    Name: 'node.exe',
    ExecutablePath: 'C:\\Program Files\\nodejs\\node.exe',
    CommandLine: 'node C:\\Users\\scott\\Code\\Meridian\\node_modules\\.bin\\electron .',
  }, repoRoot), true);

  assert.equal(isMeridianBuildProcess({
    ProcessId: 103,
    Name: 'Meridian.exe',
    ExecutablePath: 'C:\\Users\\scott\\Code\\Meridian\\dist\\win-unpacked\\Meridian.exe',
    CommandLine: 'C:\\Users\\scott\\Code\\Meridian\\dist\\win-unpacked\\Meridian.exe',
  }, repoRoot), true);

  assert.equal(isMeridianBuildProcess({
    ProcessId: 104,
    Name: 'electron.exe',
    ExecutablePath: 'C:\\OtherApp\\electron.exe',
    CommandLine: 'C:\\OtherApp\\electron.exe .',
  }, repoRoot), false);

  assert.equal(isMeridianBuildProcess({
    ProcessId: 105,
    Name: 'node.exe',
    ExecutablePath: 'C:\\Program Files\\nodejs\\node.exe',
    CommandLine: 'node C:\\Users\\scott\\Code\\Meridian\\scripts\\meridian-model-bridge.js',
  }, repoRoot), false);
});

test('closeMeridianForBuild stops only matched processes', () => {
  const stopped = [];
  const processes = [
    {
      ProcessId: 201,
      Name: 'electron.exe',
      ExecutablePath: 'C:\\Users\\scott\\Code\\Meridian\\node_modules\\electron\\dist\\electron.exe',
      CommandLine: 'C:\\Users\\scott\\Code\\Meridian\\node_modules\\electron\\dist\\electron.exe .',
    },
    {
      ProcessId: 202,
      Name: 'electron.exe',
      ExecutablePath: 'C:\\OtherApp\\electron.exe',
      CommandLine: 'C:\\OtherApp\\electron.exe .',
    },
  ];
  const execFile = (bin, args) => {
    const command = args.join(' ');
    if (command.includes('Get-CimInstance')) return JSON.stringify(processes);
    const match = command.match(/Stop-Process -Id (\d+)/);
    if (match) stopped.push(Number(match[1]));
    return '';
  };

  const closed = closeMeridianForBuild({ execFile, root: repoRoot });

  assert.deepEqual(closed.map((item) => item.ProcessId), [201]);
  assert.deepEqual(stopped, [201]);
});
