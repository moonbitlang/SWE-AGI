#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const args = process.argv.slice(2);

if (args.length < 2) {
  console.error('Usage: run-in-docker.js <spec-dir> <agent-name>');
  process.exit(1);
}

const specDirArg = args[0];
const agentName = args[1];
const repoRoot = process.cwd();

if (specDirArg === '.' || specDirArg === '..' || specDirArg.includes('/') || specDirArg.includes('\\')) {
  console.error('spec-dir must be a single directory name under the repo root.');
  process.exit(1);
}

const hostSpecPath = path.resolve(repoRoot, specDirArg);
const scriptsPath = path.resolve(repoRoot, 'scripts');

if (!fs.existsSync(hostSpecPath) || !fs.statSync(hostSpecPath).isDirectory()) {
  console.error(`Spec directory does not exist: ${hostSpecPath}`);
  process.exit(1);
}

if (!fs.existsSync(scriptsPath) || !fs.statSync(scriptsPath).isDirectory()) {
  console.error(`Scripts directory does not exist: ${scriptsPath}`);
  process.exit(1);
}

function sanitizeName(value) {
  let sanitized = value.replace(/[^a-zA-Z0-9_.-]+/g, '-');
  sanitized = sanitized.replace(/^[^a-zA-Z0-9]+/, '');
  sanitized = sanitized.replace(/[^a-zA-Z0-9]+$/, '');
  return sanitized;
}

const agentTag = sanitizeName(agentName);
const specTag = sanitizeName(specDirArg);

if (!agentTag || !specTag) {
  console.error('agent-name and spec-dir must contain at least one alphanumeric character.');
  process.exit(1);
}

const containerName = `spec-tests-${agentTag}-${specTag}`;

function runCommand(command, commandArgs, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, commandArgs, { stdio: 'inherit', ...options });
    child.on('error', (err) => {
      reject(new Error(`Failed to start ${command}: ${err.message}`));
    });
    child.on('close', (code, signal) => {
      if (signal) {
        reject(new Error(`${command} exited with signal ${signal}`));
        return;
      }
      if (code !== 0) {
        reject(new Error(`${command} exited with code ${code}`));
        return;
      }
      resolve();
    });
  });
}

async function main() {
  let containerStarted = false;
  let runError = null;

  try {
    await runCommand('docker', [
      'run',
      '-d',
      '--name',
      containerName,
      'spec-tests-login',
      'sleep',
      'infinity',
    ]);
    containerStarted = true;

    await runCommand('docker', ['cp', hostSpecPath, `${containerName}:/workspace/`]);
    await runCommand('docker', ['cp', scriptsPath, `${containerName}:/workspace/`]);
    await runCommand('docker', [
      'exec',
      '--user',
      'root',
      containerName,
      'chown',
      '-R',
      'agent:agent',
      '/workspace',
    ]);
    await runCommand('docker', [
      'exec',
      '--user',
      'agent',
      '-w',
      '/workspace',
      containerName,
      '/workspace/scripts/run.js',
      specDirArg,
      agentName,
    ]);
  } catch (err) {
    runError = err;
  } finally {
    if (containerStarted) {
      try {
        await runCommand('docker', [
          'cp',
          `${containerName}:/workspace/${specDirArg}/.`,
          hostSpecPath,
        ]);
      } catch (syncErr) {
        console.error(`Failed to sync results: ${syncErr.message}`);
        if (!runError) {
          runError = syncErr;
        }
      }
    }
  }

  if (runError) {
    console.error(runError.message);
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error(err.message);
  process.exitCode = 1;
});
