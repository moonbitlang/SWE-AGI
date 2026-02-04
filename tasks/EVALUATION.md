# Agent Evaluation with Public/Private Test Split

This repository includes a Docker-based evaluation infrastructure for testing AI
agents with a public/private test split. Agents iterate locally against public
tests, while scoring is performed only on final submissions evaluated against
hidden private tests.

## Overview

- **Public tests** (`*_pub_test.mbt`): visible to the agent during development
- **Private tests** (`*_priv_test.mbt`): hidden from the agent and used only for
  final evaluation

The Docker setup isolates the agent so it can only see public tests while the server has access to the full test suite for validation.

## Prerequisites

- Docker and Docker Compose installed
- One of the following workspace layouts:
  - **In-repo layout (recommended):** run directly from this repository root,
    where both `tasks/` and `docker/` already exist.
  - **Isolated bundle layout:** from this repository root, copy `tasks/*` plus
    `docker/` into a scratch directory under `eval/`.

## Workflow

1. **Choose a workspace layout**

   Option A (in-repo):

   ```bash
   cd <path-to-SWE-AGI>
   ```

   Option B (isolated bundle, from this repository root):

   ```bash
   mkdir -p eval/<date>/<name>
   cp -R tasks/* eval/<date>/<name>/
   cp -R docker eval/<date>/<name>/
   cd eval/<date>/<name>
   ```

2. **Enter `docker/` and build the image**

   ```bash
   cd docker
   docker build --platform=linux/amd64 -t swe-agi:latest .
   ```

3. **Run `setup.py` to prepare client/server data**

   ```bash
   python3 setup.py
   ```

   This creates:
   - `server_data/`: full checkout (public + private tests)
   - `client_data/`: agent-visible checkout (private tests excluded)

4. **Start containers**

   ```bash
   ./start.sh
   ```

   Note: `docker/start.sh` uses the legacy `docker-compose` command. If you only
   have the plugin-style `docker compose`, run it manually or update the script.

5. **Perform runner login (one-time setup)**

   ```bash
   docker ps --filter name=swe-agi-client
   docker exec -it swe-agi-client-<timestamp> bash
   # Inside container: run the CLI you plan to use (e.g. `codex`, `claude`,
   # `gemini`, `opencode`, ...) to authenticate.
   exit
   ```

6. **Run the agent**

   ```bash
   docker exec -d swe-agi-client-<timestamp> swe-agi-run <spec> <agent>
   ```

   Example: `docker exec -d swe-agi-client-20250122-123456 swe-agi-run toml claude`

   For the up-to-date list of supported runners and environment variables, see:
   - `docker/README.md`
   - `docker/run.js`

7. **Monitor progress**

   Check `client_data/<spec>/` for:
   - `log.jsonl`: Agent activity stream
   - `log.yaml`: YAML-formatted log
   - `run-metrics.json`: Appears when run completes (contains elapsed time, exit code, test summary)

8. **Validation**

   When the agent calls `swe-agi-submit`, the server:
   - Copies implementation from `client_data` to `server_data`
   - Runs `moon test` against the full test suite (pub + priv)
   - Returns pass/fail status with summary

## Stopping Containers

```bash
# run from docker/
./stop.sh
# or: docker-compose down
# or: docker compose down
```

## Results

Each completed run produces:

- `log.jsonl`: Full agent conversation log
- `log.yaml`: YAML-formatted log
- `run-metrics.json`: Timing and test results

See `docker/README.md` for additional configuration options.
