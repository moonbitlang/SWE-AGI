#!/usr/bin/env node
'use strict';

/**
 * Test Runner Server
 *
 * Listens on a Unix socket and handles test/check/fmt requests from agents
 * running inside Docker containers. Executes moon commands on the host
 * and returns JSON results.
 */

const net = require('net');
const fs = require('fs');
const { spawn } = require('child_process');

// ============================================================================
// Configuration
// ============================================================================

const socketPath = process.argv[2];
const specDir = process.argv[3];

if (!socketPath || !specDir) {
  console.error('Usage: test-runner-server.js <socket-path> <spec-dir>');
  process.exit(1);
}

if (!fs.existsSync(specDir)) {
  console.error(`Spec directory does not exist: ${specDir}`);
  process.exit(1);
}

// ============================================================================
// Utility Functions
// ============================================================================

function parseTestOutput(output) {
  const match = output.match(/Total tests:\s*(\d+),\s*passed:\s*(\d+),\s*failed:\s*(\d+)/);
  if (match) {
    return {
      total_tests: parseInt(match[1], 10),
      passed: parseInt(match[2], 10),
      failed: parseInt(match[3], 10),
    };
  }
  return null;
}

function runMoonCommand(action, filter) {
  return new Promise((resolve) => {
    let args;
    switch (action) {
      case 'test':
        args = filter ? ['test', '-p', filter] : ['test'];
        break;
      case 'check':
        args = ['check'];
        break;
      case 'fmt':
        args = ['fmt'];
        break;
      default:
        resolve({
          exit_code: 1,
          error: `Unknown action: ${action}`,
        });
        return;
    }

    const proc = spawn('moon', args, {
      cwd: specDir,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      stdout += data;
    });

    proc.stderr.on('data', (data) => {
      stderr += data;
    });

    proc.on('error', (err) => {
      resolve({
        exit_code: 1,
        error: `Failed to start moon: ${err.message}`,
      });
    });

    proc.on('close', (code) => {
      const result = {
        exit_code: code === null ? 1 : code,
        output: stdout,
      };

      if (stderr) {
        result.error = stderr;
      }

      // Parse test output for test action
      if (action === 'test') {
        const testResults = parseTestOutput(stdout + stderr);
        if (testResults) {
          result.test_results = testResults;
        }
      }

      resolve(result);
    });
  });
}

// ============================================================================
// Server Setup
// ============================================================================

// Remove existing socket file if it exists
if (fs.existsSync(socketPath)) {
  fs.unlinkSync(socketPath);
}

const server = net.createServer({ allowHalfOpen: true }, (socket) => {
  let buffer = '';

  socket.on('data', (data) => {
    buffer += data.toString();
  });

  socket.on('end', async () => {
    try {
      const request = JSON.parse(buffer);
      const { action, filter } = request;

      if (!action) {
        socket.end(JSON.stringify({ exit_code: 1, error: 'Missing action' }));
        return;
      }

      console.log(`[test-runner] Received ${action}${filter ? ` with filter: ${filter}` : ''}`);

      const result = await runMoonCommand(action, filter);

      console.log(`[test-runner] ${action} completed with exit code ${result.exit_code}`);
      if (result.test_results) {
        console.log(`[test-runner] Tests: ${result.test_results.passed}/${result.test_results.total_tests} passed`);
      }

      socket.end(JSON.stringify(result));
    } catch (err) {
      console.error('[test-runner] Error processing request:', err.message);
      socket.end(JSON.stringify({
        exit_code: 1,
        error: `Failed to process request: ${err.message}`,
      }));
    }
  });

  socket.on('error', (err) => {
    console.error('[test-runner] Socket error:', err.message);
  });
});

server.on('error', (err) => {
  console.error('[test-runner] Server error:', err.message);
  process.exit(1);
});

server.listen(socketPath, () => {
  console.log(`[test-runner] Server listening on ${socketPath}`);
  console.log(`[test-runner] Spec directory: ${specDir}`);

  // Make socket accessible
  fs.chmodSync(socketPath, 0o666);
});

// Graceful shutdown
function shutdown() {
  console.log('[test-runner] Shutting down...');
  server.close(() => {
    if (fs.existsSync(socketPath)) {
      fs.unlinkSync(socketPath);
    }
    process.exit(0);
  });
}

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);

// Export for testing
module.exports = { parseTestOutput, runMoonCommand };
