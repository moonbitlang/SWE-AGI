#!/usr/bin/env node
'use strict';

// Test runner client for spec-test agents.
// Communicates with the host test runner server via Unix socket.

const fs = require('fs');
const net = require('net');
const path = require('path');

const SOCKET_PATH = process.env.SPEC_TEST_SOCKET || '/var/run/spec-test.sock';
const scriptName = path.basename(process.argv[1]);

function usage() {
  console.log(`Usage: ${scriptName} <action> [filter]`);
  console.log('');
  console.log('Actions:');
  console.log('  test [filter]   Run moon test (optionally with package filter)');
  console.log('  check           Run moon check to verify compilation');
  console.log('  fmt             Run moon fmt to format code');
  console.log('');
  console.log('Examples:');
  console.log(`  ${scriptName} test                  # Run all tests`);
  console.log(`  ${scriptName} test tests/easy       # Run tests in specific package`);
  console.log(`  ${scriptName} check                 # Check for compilation errors`);
  console.log(`  ${scriptName} fmt                   # Format code`);
  process.exit(1);
}

const args = process.argv.slice(2);
if (args.length < 1) {
  usage();
}

const action = args[0];
const filter = args[1];

if (!['test', 'check', 'fmt'].includes(action)) {
  console.error(`Error: Unknown action '${action}'`);
  usage();
}

let socketStat;
try {
  socketStat = fs.statSync(SOCKET_PATH);
} catch (err) {
  console.error(`Error: Test runner socket not found at ${SOCKET_PATH}`);
  console.error('Make sure the test runner server is running on the host.');
  process.exit(1);
}

if (!socketStat.isSocket()) {
  console.error(`Error: ${SOCKET_PATH} exists but is not a Unix socket`);
  process.exit(1);
}

const request = filter ? { action, filter } : { action };
const requestJson = JSON.stringify(request);

const socket = net.createConnection({ path: SOCKET_PATH }, () => {
  socket.write(requestJson);
  socket.end();
});

let responseBuffer = '';
socket.setEncoding('utf8');

socket.on('data', (chunk) => {
  responseBuffer += chunk;
});

socket.on('end', () => {
  if (!responseBuffer.trim()) {
    console.error('Error: No response from test runner server');
    process.exit(1);
  }

  let response;
  try {
    response = JSON.parse(responseBuffer);
  } catch (err) {
    console.error(`Error: Invalid response from test runner server: ${err.message}`);
    process.exit(1);
  }

  const exitCode = Number.isInteger(response.exit_code) ? response.exit_code : 1;
  const output = typeof response.output === 'string' ? response.output : '';
  const error = typeof response.error === 'string' ? response.error : '';

  if (output) {
    process.stdout.write(output);
  }

  if (error && error !== 'null') {
    process.stderr.write(error);
  }

  const testResults = response.test_results;
  if (testResults && typeof testResults === 'object' && typeof testResults.total_tests === 'number') {
    const passed = Number.isInteger(testResults.passed) ? testResults.passed : 0;
    const failed = Number.isInteger(testResults.failed) ? testResults.failed : 0;
    process.stdout.write(`\nTest Results: ${passed}/${testResults.total_tests} passed, ${failed} failed\n`);
  }

  process.exit(exitCode);
});

socket.on('error', (err) => {
  console.error(`Error: ${err.message}`);
  process.exit(1);
});
