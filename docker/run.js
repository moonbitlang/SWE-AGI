#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const { spawn, spawnSync } = require("child_process");

// ============================================================================
// Argument Parsing
// ============================================================================

const args = process.argv.slice(2);

if (args.length < 2) {
  console.error("Usage: run.js <spec-dir> <agent-name>");
  console.error(
    "  spec-dir:     Path to the spec test directory (relative or absolute)",
  );
  console.error("  agent-name:   One of: codex, gpt-5.3-codex, claude, sonnet-claude, deepseek-claude, glm-claude, minimax-claude, dashscope-claude, openrouter-claude, claude-openrouter, gemini, opencode, maria, kimi, qoder");
  console.error("");
  console.error("Examples:");
  console.error("  ./scripts/run.js ../toml-spec-test codex");
  console.error("  ./scripts/run.js /path/to/spec claude");
  process.exit(1);
}

const specDir = path.resolve(args[0]);
const runner = args[1];

const supportedRunners = ["codex", "gpt-5.3-codex", "claude", "sonnet-claude", "deepseek-claude", "glm-claude", "minimax-claude", "dashscope-claude", "openrouter-claude", "claude-openrouter", "gemini", "opencode", "maria", "kimi", "qoder"];

if (!supportedRunners.includes(runner)) {
  console.error(`Unknown runner: ${runner}`);
  console.error(`Supported runners: ${supportedRunners.join(", ")}`);
  process.exit(1);
}

// Validate spec directory exists
if (!fs.existsSync(specDir)) {
  console.error(`Spec directory does not exist: ${specDir}`);
  process.exit(1);
}

// Set up paths relative to the spec directory
const taskFile = path.join(specDir, "TASK.md");
const logFile = path.join(specDir, "log.jsonl");
const logYamlFile = path.join(specDir, "log.yaml");
const metricsFile = path.join(specDir, "run-metrics.json");
const serverUrl = process.env.SERVER_URL;

// Validate TASK.md exists
if (!fs.existsSync(taskFile)) {
  console.error(`TASK.md not found in: ${specDir}`);
  process.exit(1);
}

const startTime = new Date();
const startMs = Date.now();
let finalized = false;

// Runner configurations
const runners = {
  codex: {
    command: "codex",
    args: [
      "exec",
      "--json",
      "--dangerously-bypass-approvals-and-sandbox",
      "--skip-git-repo-check",
      "--config",
      "model_reasoning_effort=high",
      "-m",
      process.env.CODEX_MODEL || "gpt-5.2-codex",
      "-",
    ],
    useStdin: true,
    writesLogFile: false,
    stdio: ["pipe", "pipe", "inherit"],
  },
  "gpt-5.3-codex": {
    command: "codex",
    args: [
      "exec",
      "--json",
      "--dangerously-bypass-approvals-and-sandbox",
      "--skip-git-repo-check",
      "--config",
      "model_reasoning_effort=xhigh",
      "-m",
      "gpt-5.3-codex",
      "-",
    ],
    useStdin: true,
    writesLogFile: false,
    stdio: ["pipe", "pipe", "inherit"],
  },
  claude: {
    command: "claude",
    args: [
      "--print",
      "--output-format",
      "stream-json",
      "--verbose",
      "--dangerously-skip-permissions",
      "--model",
      process.env.CLAUDE_MODEL || "opus",
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ["inherit", "pipe", "inherit"],
  },
  "sonnet-claude": {
    command: "claude",
    args: [
      "--print",
      "--output-format",
      "stream-json",
      "--verbose",
      "--dangerously-skip-permissions",
      "--model",
      process.env.SONNET_CLAUDE_MODEL || "sonnet",
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ["inherit", "pipe", "inherit"],
  },
  "deepseek-claude": {
    command: "claude",
    args: [
      "--print",
      "--output-format",
      "stream-json",
      "--verbose",
      "--dangerously-skip-permissions",
      "--model",
      process.env.DEEPSEEK_CLAUDE_MODEL || "deepseek-reasoner",
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ["inherit", "pipe", "inherit"],
    env: {
      ANTHROPIC_BASE_URL: "https://api.deepseek.com/anthropic",
      ANTHROPIC_AUTH_TOKEN: process.env.DEEPSEEK_API_KEY || "",
      API_TIMEOUT_MS: "600000",
      ANTHROPIC_MODEL: "deepseek-reasoner",
      ANTHROPIC_SMALL_FAST_MODEL: "deepseek-reasoner",
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1",
      CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: "50",
    },
  },
  "glm-claude": {
    command: "claude",
    args: [
      "--print",
      "--output-format",
      "stream-json",
      "--verbose",
      "--dangerously-skip-permissions",
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ["inherit", "pipe", "inherit"],
    env: {
      ANTHROPIC_AUTH_TOKEN: process.env.ZHIPU_API_KEY || "",
      ANTHROPIC_BASE_URL: "https://open.bigmodel.cn/api/anthropic",
      API_TIMEOUT_MS: "3000000",
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1",
    },
  },
  "minimax-claude": {
    command: "claude",
    args: [
      "--print",
      "--output-format",
      "stream-json",
      "--verbose",
      "--dangerously-skip-permissions",
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ["inherit", "pipe", "inherit"],
    env: {
      ANTHROPIC_BASE_URL: "https://api.minimaxi.com/anthropic",
      ANTHROPIC_AUTH_TOKEN: process.env.MINIMAX_API_KEY || "",
      API_TIMEOUT_MS: "3000000",
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1",
      ANTHROPIC_MODEL: "MiniMax-M2.1",
      ANTHROPIC_SMALL_FAST_MODEL: "MiniMax-M2.1",
      ANTHROPIC_DEFAULT_SONNET_MODEL: "MiniMax-M2.1",
      ANTHROPIC_DEFAULT_OPUS_MODEL: "MiniMax-M2.1",
      ANTHROPIC_DEFAULT_HAIKU_MODEL: "MiniMax-M2.1",
    },
  },
  "dashscope-claude": {
    command: "claude",
    args: [
      "--print",
      "--output-format",
      "stream-json",
      "--verbose",
      "--dangerously-skip-permissions",
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ["inherit", "pipe", "inherit"],
    env: {
      ANTHROPIC_BASE_URL: "https://dashscope.aliyuncs.com/apps/anthropic",
      ANTHROPIC_AUTH_TOKEN: process.env.DASHSCOPE_API_KEY || "",
      API_TIMEOUT_MS: "600000",
      ANTHROPIC_MODEL: "qwen3-max-2026-01-23",
      ANTHROPIC_SMALL_FAST_MODEL: "qwen3-max-2026-01-23",
      ANTHROPIC_DEFAULT_SONNET_MODEL: "qwen3-max-2026-01-23",
      ANTHROPIC_DEFAULT_OPUS_MODEL: "qwen3-max-2026-01-23",
      ANTHROPIC_DEFAULT_HAIKU_MODEL: "qwen3-max-2026-01-23",
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1",
      CLAUDE_AUTOCOMPACT_PCT_OVERRIDE: "50",
    },
  },
  "openrouter-claude": {
    command: "claude",
    args: [
      "--print",
      "--output-format",
      "stream-json",
      "--verbose",
      "--dangerously-skip-permissions",
      "--model",
      process.env.OPENROUTER_MODEL || "anthropic/claude-sonnet-4",
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ["inherit", "pipe", "inherit"],
    env: {
      ANTHROPIC_BASE_URL: "https://openrouter.ai/api",
      ANTHROPIC_AUTH_TOKEN: process.env.OPENROUTER_API_KEY || "",
      ANTHROPIC_API_KEY: "",  // Must be explicitly empty
      API_TIMEOUT_MS: "600000",
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1",
      ...(process.env.OPENROUTER_MODEL && {
        ANTHROPIC_MODEL: process.env.OPENROUTER_MODEL,
        ANTHROPIC_SMALL_FAST_MODEL: process.env.OPENROUTER_MODEL,
        ANTHROPIC_DEFAULT_SONNET_MODEL: process.env.OPENROUTER_MODEL,
        ANTHROPIC_DEFAULT_OPUS_MODEL: process.env.OPENROUTER_MODEL,
        ANTHROPIC_DEFAULT_HAIKU_MODEL: process.env.OPENROUTER_MODEL,
      }),
    },
  },
  "claude-openrouter": {
    command: "claude",
    args: [
      "--print",
      "--output-format",
      "stream-json",
      "--verbose",
      "--dangerously-skip-permissions",
      "--model",
      process.env.OPENROUTER_MODEL || "anthropic/claude-opus-4.6",
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ["inherit", "pipe", "inherit"],
    env: {
      ANTHROPIC_BASE_URL: "https://openrouter.ai/api",
      ANTHROPIC_AUTH_TOKEN: process.env.OPENROUTER_API_KEY || "",
      ANTHROPIC_API_KEY: "",  // Must be explicitly empty
      API_TIMEOUT_MS: "600000",
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1",
      ANTHROPIC_MODEL: "anthropic/claude-opus-4.6",
      ANTHROPIC_SMALL_FAST_MODEL: "anthropic/claude-haiku-4.5",
      ANTHROPIC_DEFAULT_SONNET_MODEL: "anthropic/claude-sonnet-4.5",
      ANTHROPIC_DEFAULT_OPUS_MODEL: "anthropic/claude-opus-4.6",
      ANTHROPIC_DEFAULT_HAIKU_MODEL: "anthropic/claude-haiku-4.5",
    },
  },
  gemini: {
    command: "gemini",
    args: [
      "--output-format",
      "stream-json",
      "--approval-mode",
      "yolo",
      "--model",
      process.env.GEMINI_MODEL || "gemini-3-pro-preview",
    ],
    useStdin: true,
    writesLogFile: false,
    stdio: ["pipe", "pipe", "inherit"],
  },
  opencode: {
    command: "opencode",
    args: [
      "run",
      "--format",
      "json",
      "-m",
      process.env.OPENCODE_MODEL || "anthropic/claude-sonnet-4-20250514",
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ["inherit", "pipe", "inherit"],
  },
  maria: {
    command: "maria",
    args: [
      "exec",
      "--prompt-file",
      taskFile,
      "--model",
      process.env.MARIA_MODEL || "claude-sonnet-4-20250514",
      "--log-file",
      logFile,
    ],
    useStdin: false,
    writesLogFile: true,
    stdio: ["inherit", "inherit", "inherit"],
  },
  kimi: {
    command: "kimi",
    args: [
      "--print",
      "--output-format",
      "stream-json",
      "--yolo",
      "--thinking",
      "--max-steps-per-turn",
      "10000",
      "--model",
      process.env.KIMI_MODEL || "kimi-code/kimi-for-coding",
    ],
    useStdin: true,
    writesLogFile: false,
    stdio: ["pipe", "pipe", "inherit"],
  },
  qoder: {
    command: "qodercli",
    args: [
      "--output-format",
      "stream-json",
      "--dangerously-skip-permissions",
      "--model",
      process.env.QODER_MODEL || "performance",
      "--print",
    ],
    useStdin: false,
    writesLogFile: false,
    stdio: ["inherit", "pipe", "inherit"],
  },
};

const config = runners[runner];

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
    fs.writeFileSync(metricsFile, JSON.stringify(metrics, null, 2) + "\n");
  } catch (err) {
    console.error(`Failed to write ${metricsFile}:`, err);
  }

  if (signal) {
    console.error(`${runner} exited with signal ${signal}`);
  }

  process.exitCode = exitCode === null ? 1 : exitCode;
}

function runJsonlToYaml(callback) {
  let doneCalled = false;
  const done = (code) => {
    if (doneCalled) {
      return;
    }
    doneCalled = true;
    callback(code);
  };

  const jq = spawn("jq", ["-s", ".", logFile], {
    cwd: specDir,
    stdio: ["ignore", "pipe", "inherit"],
  });

  jq.on("error", (err) => {
    console.error("Failed to start jq:", err);
    done(1);
  });

  const yq = spawn("yq", ["-p=json", "-o=yaml", "-P", "."], {
    cwd: specDir,
    stdio: ["pipe", "pipe", "inherit"],
  });

  yq.on("error", (err) => {
    console.error("Failed to start yq:", err);
    jq.kill("SIGTERM");
    done(1);
  });

  const yamlOut = fs.createWriteStream(logYamlFile, { flags: "w" });
  yamlOut.on("error", (err) => {
    console.error(`Failed to write ${logYamlFile}:`, err);
    jq.kill("SIGTERM");
    yq.kill("SIGTERM");
    done(1);
  });

  jq.stdout.pipe(yq.stdin);
  yq.stdout.pipe(yamlOut);

  let jqExit = null;
  let yqExit = null;

  function maybeDone() {
    if (jqExit === null || yqExit === null) {
      return;
    }
    done(jqExit === 0 && yqExit === 0 ? 0 : 1);
  }

  jq.on("close", (code, signal) => {
    if (signal) {
      console.error(`jq exited with signal ${signal}`);
      jqExit = 1;
      yq.kill("SIGTERM");
      maybeDone();
      return;
    }
    jqExit = code === null ? 1 : code;
    maybeDone();
  });

  yq.on("close", (code, signal) => {
    if (signal) {
      console.error(`yq exited with signal ${signal}`);
      yqExit = 1;
      jq.kill("SIGTERM");
      maybeDone();
      return;
    }
    yqExit = code === null ? 1 : code;
    maybeDone();
  });
}

function parseTestOutput(output) {
  const match = output.match(
    /Total tests:\s*(\d+),\s*passed:\s*(\d+),\s*failed:\s*(\d+)/,
  );
  if (match) {
    return {
      total_tests: parseInt(match[1], 10),
      passed: parseInt(match[2], 10),
      failed: parseInt(match[3], 10),
    };
  }
  return null;
}

function runMoonTestLocal(callback) {
  const moonTest = spawn("moon", ["test"], {
    cwd: specDir,
    stdio: ["ignore", "pipe", "pipe"],
  });

  let output = "";

  moonTest.stdout.on("data", (data) => {
    output += data;
  });
  moonTest.stderr.on("data", (data) => {
    output += data;
  });

  moonTest.on("error", (err) => {
    console.error("Failed to start moon test:", err);
    callback(1, null);
  });

  moonTest.on("close", (code, signal) => {
    if (signal) {
      console.error(`moon test exited with signal ${signal}`);
      callback(1, null);
      return;
    }

    const testResults = parseTestOutput(output);
    callback(code === null ? 1 : code, testResults);
  });
}

function runMoonTestViaServer(callback) {
  if (!serverUrl) {
    runMoonTestLocal(callback);
    return;
  }

  let url;
  try {
    url = new URL("/test", serverUrl);
  } catch (err) {
    console.error(`Invalid SERVER_URL: ${serverUrl}`);
    callback(1, null);
    return;
  }

  const projectName = path.basename(specDir);
  const payload = JSON.stringify({ project_name: projectName });
  const transport =
    url.protocol === "https:" ? require("https") : require("http");
  const options = {
    method: "POST",
    hostname: url.hostname,
    port: url.port || (url.protocol === "https:" ? 443 : 80),
    path: `${url.pathname}${url.search}`,
    headers: {
      "Content-Type": "application/json",
      "Content-Length": Buffer.byteLength(payload),
    },
  };

  const req = transport.request(options, (res) => {
    let body = "";
    res.setEncoding("utf8");
    res.on("data", (chunk) => {
      body += chunk;
    });
    res.on("end", () => {
      if (res.statusCode < 200 || res.statusCode >= 300) {
        console.error(
          `Server test failed (${res.statusCode || "unknown"}): ${body || "no response body"}`,
        );
        callback(1, null);
        return;
      }

      let data;
      try {
        data = JSON.parse(body);
      } catch (err) {
        console.error("Failed to parse server response:", err);
        callback(1, null);
        return;
      }

      const testResult = data.test_result || {};
      const summary = testResult.summary || null;
      let testResults = null;
      if (summary) {
        testResults = {
          total_tests: summary.total || 0,
          passed: summary.passed || 0,
          failed: summary.failed || 0,
        };
      }

      callback(
        testResult.exit_code === undefined ? 1 : testResult.exit_code,
        testResults,
      );
    });
  });

  req.on("error", (err) => {
    console.error("Failed to reach test server:", err);
    callback(1, null);
  });

  req.setTimeout(300000, () => {
    console.error("Test server request timed out");
    req.destroy(new Error("Request timeout"));
  });

  req.write(payload);
  req.end();
}

function runMoonTest(callback) {
  if (serverUrl) {
    runMoonTestViaServer(callback);
    return;
  }
  runMoonTestLocal(callback);
}

console.log(`Running ${runner} in ${specDir}...`);

// Build final args based on runner type
let finalArgs = config.args;
if (!config.useStdin && !config.writesLogFile) {
  // Claude/opencode/qoder: pass task content as final argument
  const taskContent = fs.readFileSync(taskFile, "utf-8");
  finalArgs = [...config.args, taskContent];
}

console.log('finalArgs: ', finalArgs);

const env = config.env ? { ...process.env, ...config.env } : process.env;

// Clean MoonBit build artifacts before running the agent
spawnSync("moon", ["clean"], { cwd: specDir, stdio: "inherit" });

const child = spawn(config.command, finalArgs, {
  cwd: specDir,
  stdio: config.stdio,
  env,
});

let logWriteStream = null;

child.on("error", (err) => {
  console.error(`Failed to start ${runner}:`, err);
  finalize(1, null, null);
});

// Pipe stdin if required (for codex/gemini)
if (config.useStdin) {
  const input = fs.createReadStream(taskFile);
  input.on("error", (err) => {
    console.error(`Failed to read ${taskFile}:`, err);
    child.kill("SIGTERM");
    finalize(1, "SIGTERM", null);
  });
  input.pipe(child.stdin);
}

// Only pipe stdout to log file if runner doesn't write it directly
if (!config.writesLogFile) {
  logWriteStream = fs.createWriteStream(logFile, { flags: "w" });
  logWriteStream.on("error", (err) => {
    console.error(`Failed to write ${logFile}:`, err);
    child.kill("SIGTERM");
  });
  child.stdout.pipe(logWriteStream);
}

child.on("close", (code, signal) => {
  if (code !== 0 || signal) {
    finalize(code, signal, null);
    return;
  }

  const waitForLog = (cb) => {
    if (!logWriteStream) {
      cb();
      return;
    }
    if (logWriteStream.writableFinished || logWriteStream.destroyed) {
      cb();
      return;
    }
    logWriteStream.once("finish", cb);
    logWriteStream.once("close", cb);
  };

  waitForLog(() => {
    runJsonlToYaml((yqExitCode) => {
      if (yqExitCode !== 0) {
        finalize(yqExitCode, null, null);
        return;
      }

      runMoonTest((testExitCode, testResults) => {
        finalize(testExitCode, null, testResults);
      });
    });
  });
});
