#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const { spawn, spawnSync } = require('child_process');

// ============================================================================
// Argument Parsing
// ============================================================================

const allArgs = process.argv.slice(2);

// Parse flags
const useTaskMd = allArgs.includes('--use-task-md');
const useTaskPubMd = allArgs.includes('--use-task-pub-md');
const resume = allArgs.includes('--resume');

// Filter out flags to get positional args
const args = allArgs.filter(arg => !arg.startsWith('--'));

if (args.length < 2) {
  console.error('Usage: run.js [options] <spec-dir> <agent-name>');
  console.error(
    '  spec-dir:     Path to the spec test directory (relative or absolute)'
  );
  console.error('  agent-name:   One of: codex, claude, deepseek-claude, glm-claude, minimax-claude, dashscope-claude, opencode, maria, kimi, qoder');
  console.error('');
  console.error('Options:');
  console.error('  --use-task-md      Use TASK.md (default in Docker)');
  console.error('  --use-task-pub-md  Use TASK.pub.md (default outside Docker)');
  console.error('  --resume           Resume a previous session using log.jsonl');
  console.error('');
  console.error('Examples:');
  console.error('  ./scripts/run.js ../toml-spec-test codex');
  console.error('  ./scripts/run.js --use-task-md /path/to/spec claude');
  process.exit(1);
}

// Validate conflicting flags
if (useTaskMd && useTaskPubMd) {
  console.error('Error: Cannot use both --use-task-md and --use-task-pub-md');
  process.exit(1);
}

function isRunningInDocker() {
  if (fs.existsSync('/.dockerenv')) {
    return true;
  }
  const cgroupPath = '/proc/1/cgroup';
  if (fs.existsSync(cgroupPath)) {
    try {
      const cgroup = fs.readFileSync(cgroupPath, 'utf-8');
      return /(docker|containerd|kubepods)/i.test(cgroup);
    } catch (err) {
      return false;
    }
  }
  return false;
}

// Determine task file name (default: TASK.pub.md on host, TASK.md in Docker)
const taskFileName = useTaskMd
  ? 'TASK.md'
  : useTaskPubMd
    ? 'TASK.pub.md'
    : (isRunningInDocker() ? 'TASK.md' : 'TASK.pub.md');

const specDir = path.resolve(args[0]);
const runner = args[1];

const supportedRunners = ['codex', 'claude', 'deepseek-claude', 'glm-claude', 'minimax-claude', 'dashscope-claude', 'opencode', 'maria', 'kimi', 'qoder'];

if (!supportedRunners.includes(runner)) {
  console.error(`Unknown runner: ${runner}`);
  console.error(`Supported runners: ${supportedRunners.join(', ')}`);
  process.exit(1);
}

// Validate --resume is only used with supported runners
if (resume && !['claude', 'deepseek-claude', 'glm-claude', 'minimax-claude', 'dashscope-claude', 'codex', 'qoder'].includes(runner)) {
  console.error(`--resume is not supported for runner: ${runner}`);
  process.exit(1);
}

// Validate spec directory exists
if (!fs.existsSync(specDir)) {
  console.error(`Spec directory does not exist: ${specDir}`);
  process.exit(1);
}

// Set up paths relative to the spec directory
const taskFile = path.join(specDir, taskFileName);
const logFile = path.join(specDir, 'log.jsonl');
const logYamlFile = path.join(specDir, 'log.yaml');
const metricsFile = path.join(specDir, 'run-metrics.json');

// Validate task file exists
if (!fs.existsSync(taskFile)) {
  console.error(`${taskFileName} not found in: ${specDir}`);
  process.exit(1);
}

const startTime = new Date();
const startMs = Date.now();
let finalized = false;

// Runner configurations
const runners = {
  codex: {
    command: 'codex',
    args: [
      'exec',
      '--json',
      '--dangerously-bypass-approvals-and-sandbox',
      '--skip-git-repo-check',
      '--config',
      'model_reasoning_effort=high',
      '-m',
      process.env.CODEX_MODEL || 'gpt-5.2-codex',
      '-',
    ],
    useStdin: true,
    writesLogFile: false,
    stdio: ['pipe', 'pipe', 'inherit'],
  },
  claude: {
    command: 'claude',
    args: [
      '--print',
      '--output-format', 'stream-json',
      '--verbose',
      '--dangerously-skip-permissions',
      '--model', process.env.CLAUDE_MODEL || 'opus',
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ['inherit', 'pipe', 'inherit'],
  },
  'deepseek-claude': {
    command: 'claude',
    args: [
      '--print',
      '--output-format', 'stream-json',
      '--verbose',
      '--dangerously-skip-permissions',
      '--model', process.env.DEEPSEEK_CLAUDE_MODEL || 'deepseek-chat',
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ['inherit', 'pipe', 'inherit'],
    env: {
      ANTHROPIC_BASE_URL: 'https://api.deepseek.com/anthropic',
      ANTHROPIC_AUTH_TOKEN: process.env.DEEPSEEK_API_KEY || '',
      API_TIMEOUT_MS: '600000',
      ANTHROPIC_MODEL: 'deepseek-chat',
      ANTHROPIC_SMALL_FAST_MODEL: 'deepseek-chat',
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: '1',
      CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '50',
    },
  },
  'glm-claude': {
    command: 'claude',
    args: [
      '--print',
      '--output-format', 'stream-json',
      '--verbose',
      '--dangerously-skip-permissions',
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ['inherit', 'pipe', 'inherit'],
    env: {
      ANTHROPIC_AUTH_TOKEN: process.env.ZHIPU_API_KEY || '',
      ANTHROPIC_BASE_URL: 'https://open.bigmodel.cn/api/anthropic',
      API_TIMEOUT_MS: '3000000',
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: '1',
    },
  },
  'minimax-claude': {
    command: 'claude',
    args: [
      '--print',
      '--output-format', 'stream-json',
      '--verbose',
      '--dangerously-skip-permissions',
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ['inherit', 'pipe', 'inherit'],
    env: {
      ANTHROPIC_BASE_URL: 'https://api.minimaxi.com/anthropic',
      ANTHROPIC_AUTH_TOKEN: process.env.MINIMAX_API_KEY || '',
      API_TIMEOUT_MS: '3000000',
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: '1',
      ANTHROPIC_MODEL: 'MiniMax-M2.1',
      ANTHROPIC_SMALL_FAST_MODEL: 'MiniMax-M2.1',
      ANTHROPIC_DEFAULT_SONNET_MODEL: 'MiniMax-M2.1',
      ANTHROPIC_DEFAULT_OPUS_MODEL: 'MiniMax-M2.1',
      ANTHROPIC_DEFAULT_HAIKU_MODEL: 'MiniMax-M2.1',
    },
  },
  'dashscope-claude': {
    command: 'claude',
    args: [
      '--print',
      '--output-format', 'stream-json',
      '--verbose',
      '--dangerously-skip-permissions',
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ['inherit', 'pipe', 'inherit'],
    env: {
      ANTHROPIC_BASE_URL: 'https://dashscope.aliyuncs.com/apps/anthropic',
      ANTHROPIC_AUTH_TOKEN: process.env.DASHSCOPE_API_KEY || '',
      API_TIMEOUT_MS: '600000',
      ANTHROPIC_MODEL: 'qwen3-max-2026-01-23',
      ANTHROPIC_SMALL_FAST_MODEL: 'qwen3-max-2026-01-23',
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: '1',
      CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: '50',
    },
  },
  opencode: {
    command: 'opencode',
    args: [
      'run',
      '--format', 'json',
      '-m', process.env.OPENCODE_MODEL || 'anthropic/claude-sonnet-4-20250514',
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ['inherit', 'pipe', 'inherit'],
  },
  maria: {
    command: 'maria',
    args: [
      'exec',
      '--prompt-file', taskFile,
      '--model', process.env.MARIA_MODEL || 'claude-sonnet-4-20250514',
      '--log-file', logFile,
    ],
    useStdin: false,
    writesLogFile: true,
    stdio: ['inherit', 'inherit', 'inherit'],
  },
  kimi: {
    command: 'kimi',
    args: [
      '--print',
      '--output-format', 'stream-json',
      '--yolo',
      '--max-steps-per-turn', '10000',
      '--model', process.env.KIMI_MODEL || 'kimi-code/kimi-for-coding',
    ],
    useStdin: true,
    writesLogFile: false,
    stdio: ['pipe', 'pipe', 'inherit'],
  },
  qoder: {
    command: 'qodercli',
    args: [
      '--output-format', 'stream-json',
      '--dangerously-skip-permissions',
      '--model', process.env.QODER_MODEL || 'performance',
      '--print',
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ['inherit', 'pipe', 'inherit'],
  },
};

let config = runners[runner];

function parseSessionId(logFilePath, runnerName) {
  if (!fs.existsSync(logFilePath)) {
    console.error(`Log file not found for resume: ${logFilePath}`);
    process.exit(1);
  }

  const content = fs.readFileSync(logFilePath, 'utf-8');
  const firstLine = content.split('\n')[0];

  try {
    const json = JSON.parse(firstLine);

    if (runnerName === 'claude' || runnerName === 'deepseek-claude' || runnerName === 'dashscope-claude' || runnerName === 'qoder') {
      if (json.session_id) return json.session_id;
      throw new Error('session_id not found in first line');
    } else if (runnerName === 'codex') {
      if (json.type === 'thread.started' && json.thread_id) {
        return json.thread_id;
      }
      throw new Error('thread_id not found in thread.started event');
    }
  } catch (err) {
    console.error(`Failed to parse session ID from ${logFilePath}: ${err.message}`);
    process.exit(1);
  }
}

function finalize(exitCode, signal, testResults) {
  if (finalized) {
    return;
  }
  finalized = true;

  const endTime = new Date();
  const metrics = {
    runner,
    start_time: startTime.toISOString(),
    end_time: endTime.toISOString(),
    elapsed_ms: Date.now() - startMs,
    exit_code: exitCode === null ? null : exitCode,
    test_results: testResults || null,
  };

  try {
    fs.writeFileSync(metricsFile, JSON.stringify(metrics, null, 2) + '\n');
  } catch (err) {
    console.error(`Failed to write ${metricsFile}:`, err);
  }

  if (signal) {
    console.error(`${runner} exited with signal ${signal}`);
  }

  process.exitCode = exitCode === null ? 1 : exitCode;
}

function runJsonlToYaml(callback) {
  const yq = spawn('yq', ['-p=json', '-o=yaml', '-P', '.', logFile], {
    cwd: specDir,
    stdio: ['ignore', 'pipe', 'inherit'],
  });

  yq.on('error', (err) => {
    console.error('Failed to start yq:', err);
    callback(1);
  });

  const yamlOut = fs.createWriteStream(logYamlFile, { flags: 'w' });
  yamlOut.on('error', (err) => {
    console.error(`Failed to write ${logYamlFile}:`, err);
    yq.kill('SIGTERM');
    callback(1);
  });

  yq.stdout.pipe(yamlOut);
  yq.on('close', (code, signal) => {
    if (signal) {
      console.error(`yq exited with signal ${signal}`);
      callback(1);
      return;
    }
    callback(code === null ? 1 : code);
  });
}

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

function runMoonTest(callback) {
  const moonTest = spawn('moon', ['test'], {
    cwd: specDir,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  let output = '';

  moonTest.stdout.on('data', (data) => { output += data; });
  moonTest.stderr.on('data', (data) => { output += data; });

  moonTest.on('error', (err) => {
    console.error('Failed to start moon test:', err);
    callback(1, null);
  });

  moonTest.on('close', (code, signal) => {
    if (signal) {
      console.error(`moon test exited with signal ${signal}`);
      callback(1, null);
      return;
    }

    const testResults = parseTestOutput(output);
    callback(code === null ? 1 : code, testResults);
  });
}

console.log(`Running ${runner}${resume ? ' (resume)' : ''} in ${specDir}...`);

// Handle resume mode
if (resume) {
  const sessionId = parseSessionId(logFile, runner);
  const taskContent = fs.readFileSync(taskFile, 'utf-8');

  if (runner === 'claude' || runner === 'deepseek-claude' || runner === 'glm-claude' || runner === 'minimax-claude' || runner === 'dashscope-claude' || runner === 'qoder') {
    // Claude/deepseek-claude/dashscope-claude/qoder: use -r <session_id> flag with task content as final arg
    config = {
      ...config,
      args: [...config.args, '-r', sessionId, taskContent],
      useStdin: false,
    };
  } else if (runner === 'codex') {
    // Codex: use codex exec resume <thread_id> - (read prompt from stdin)
    config = {
      command: 'codex',
      args: [
        'exec',
        'resume',
        sessionId,
        '--json',
        '--dangerously-bypass-approvals-and-sandbox',
        '--skip-git-repo-check',
        '--config', 'model_reasoning_effort=high',
        '-m', process.env.CODEX_MODEL || 'gpt-5.2-codex',
        '-',  // read prompt from stdin
      ],
      useStdin: true,
      writesLogFile: false,
      stdio: ['pipe', 'pipe', 'inherit'],
    };
  }
}

// Build final args based on runner type
let finalArgs = config.args;
if (!resume && !config.useStdin && !config.writesLogFile) {
  // Claude/opencode/qoder: pass task content as final argument
  const taskContent = fs.readFileSync(taskFile, 'utf-8');
  finalArgs = [...config.args, taskContent];
}

const env = config.env ? { ...process.env, ...config.env } : process.env;

// Clean MoonBit build artifacts before running the agent
spawnSync('moon', ['clean'], { cwd: specDir, stdio: 'inherit' });

const child = spawn(config.command, finalArgs, {
  cwd: specDir,
  stdio: config.stdio,
  env,
});

child.on('error', (err) => {
  console.error(`Failed to start ${runner}:`, err);
  finalize(1, null, null);
});

// Pipe stdin if required (for codex)
if (config.useStdin) {
  const input = fs.createReadStream(taskFile);
  input.on('error', (err) => {
    console.error(`Failed to read ${taskFile}:`, err);
    child.kill('SIGTERM');
    finalize(1, 'SIGTERM', null);
  });
  input.pipe(child.stdin);
}

// Only pipe stdout to log file if runner doesn't write it directly
if (!config.writesLogFile) {
  const output = fs.createWriteStream(logFile, { flags: resume ? 'a' : 'w' });
  output.on('error', (err) => {
    console.error(`Failed to write ${logFile}:`, err);
    child.kill('SIGTERM');
  });
  child.stdout.pipe(output);
}

child.on('close', (code, signal) => {
  if (code !== 0 || signal) {
    finalize(code, signal, null);
    return;
  }

  runJsonlToYaml((yqExitCode) => {
    if (yqExitCode !== 0) {
      finalize(yqExitCode, null, null);
      return;
    }

    runMoonTest((_testExitCode, testResults) => {
      finalize(code, null, testResults);
    });
  });
});
