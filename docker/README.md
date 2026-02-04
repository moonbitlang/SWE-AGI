# Docker Evaluation Environment

This directory contains a ready-to-run Docker setup for evaluating MoonBit spec tests using a client/server split. The server runs `moon test` inside the container; the client runs an agent (Codex/Claude/etc.) and streams results back.

## Requirements

- Docker
- Docker Compose
  - This repo's `start.sh`/`stop.sh` use the legacy `docker-compose` command.
  - If you only have the plugin-style `docker compose`, either run it manually or update those scripts.

## Quick Start

1. Prepare test data (copies spec directories into `client_data/` and `server_data/`):

```bash
python3 setup.py
```

1. Build the image:

```bash
docker build --platform=linux/amd64 -t swe-agi:latest .
```

1. Start the containers:

```bash
./start.sh
# or: docker-compose up -d
# or: docker compose up -d
```

1. Enter the client container:

```bash
# If you started via ./start.sh, it prints the TIMESTAMP and container names.
# Otherwise, discover the container name with:
docker ps --filter name=swe-agi-client --format '{{.Names}}'
docker exec -it swe-agi-client-<timestamp> bash
```

1. Run an evaluation (inside the client container `/workspace`):

```bash
swe-agi-run <spec-name> codex
```

You can also run the evaluation from the host using `docker exec`:

```bash
docker exec -d swe-agi-client-<timestamp> swe-agi-run <spec-name> codex
```

Supported runners (keep in sync with `run.js`):
`codex`, `gpt-5.3-codex`, `claude`, `sonnet-claude`, `deepseek-claude`, `glm-claude`, `minimax-claude`, `dashscope-claude`, `openrouter-claude`, `claude-openrouter`, `gemini`, `opencode`, `maria`, `kimi`, `qoder`.

## How It Works

- `server` container
  - Runs `server.py` as a REST service on port 8080 (internal network only by default).
  - Copies project data from `/workspace/client_data` to `/workspace/server_data`, then runs `moon test`.
- `client` container
  - Mounts `./client_data` to `/workspace`.
  - Uses `run.js` (available as `swe-agi-run`) to invoke an agent and write logs.

## Logs and Results

Each run writes outputs to the spec directory under `client_data/`:

- `log.jsonl` (agent stream)
- `log.yaml` (YAML-converted log)
- `run-metrics.json` (elapsed time, exit code, test summary)

Example path on host:

```
./client_data/<spec-name>/run-metrics.json
```

## Server API (from containers)

Health check (run inside client container):

```bash
curl http://server:8080/health
```

From the host without publishing ports, you can also do:

```bash
docker exec -it swe-agi-client-<timestamp> curl http://server:8080/health
```

Submit a project for testing:

```bash
curl -X POST http://server:8080/test \
  -H 'Content-Type: application/json' \
  -d '{"project_name":"toml"}'
```

Note: `docker-compose.yml` uses `expose` (not `ports`), so the server is not reachable from the host by default. To allow host access, add:

```yaml
services:
  server:
    ports:
      - "8080:8080"
```

## Configuration

- Model selection env vars (set inside the client container):
  - Codex: `CODEX_MODEL` (default: `gpt-5.2-codex`)
  - Claude: `CLAUDE_MODEL` (default: `opus`), `SONNET_CLAUDE_MODEL` (default: `sonnet`)
  - DeepSeek (Anthropic-compatible): `DEEPSEEK_CLAUDE_MODEL` (default: `deepseek-reasoner`)
  - OpenRouter: `OPENROUTER_MODEL`
  - Gemini: `GEMINI_MODEL` (default: `gemini-3-pro-preview`)
  - OpenCode: `OPENCODE_MODEL`
  - Maria: `MARIA_MODEL`
  - Kimi: `KIMI_MODEL`
  - Qoder: `QODER_MODEL`
- API keys are not injected by default. Set them when entering the container, or extend `docker-compose.yml` with `environment` entries:
  - DeepSeek: `DEEPSEEK_API_KEY`
  - Zhipu/BigModel (glm-claude): `ZHIPU_API_KEY`
  - MiniMax: `MINIMAX_API_KEY`
  - DashScope: `DASHSCOPE_API_KEY`
  - OpenRouter: `OPENROUTER_API_KEY`

## Stop and Clean Up

```bash
./stop.sh
# or: docker-compose down
# or: docker compose down
```

To reset data:

```bash
rm -rf client_data server_data
python3 setup.py
```

## Troubleshooting

- **Image not found**: run `docker build -t swe-agi:latest .`
- **Permission issues on mounted files**: the image uses UID 501 by default. If your host UID differs, update the `useradd` line in `Dockerfile`.

## Files in This Directory

- `Dockerfile`: base image with MoonBit + agent CLIs
- `docker-compose.yml`: client/server definitions
- `start.sh` / `stop.sh`: convenience scripts
- `run.js`: agent runner (mounted as `swe-agi-run`)
- `server.py`: test server REST API
- `setup.py`: populate `client_data/` and `server_data/`
