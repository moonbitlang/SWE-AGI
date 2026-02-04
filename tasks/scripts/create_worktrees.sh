#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
worktrees_root="${repo_root}/worktrees"

usage() {
  cat <<'EOF'
Usage:
  create_worktrees.sh <spec> <agent> [--code]
  create_worktrees.sh --all <agent> [--code]
  create_worktrees.sh --list

Agents:
  codex, claude

Notes:
  - <spec> is the spec-test directory name (derived from top-level TASK.md files)
  - Worktrees are created under ./worktrees as <spec>-<agent>
  - Use --code to open VS Code in each created worktree
EOF
}

list_specs() {
  if command -v rg >/dev/null 2>&1; then
    rg --files -g 'TASK.md' "${repo_root}" | while IFS= read -r task; do
      spec_dir="$(dirname "${task}")"
      if [[ "$(dirname "${spec_dir}")" == "${repo_root}" ]]; then
        basename "${spec_dir}"
      fi
    done | sort -u
  else
    find "${repo_root}" -maxdepth 2 -name TASK.md -print0 | while IFS= read -r -d '' task; do
      basename "$(dirname "${task}")"
    done | sort -u
  fi
}

open_code=false
args=()
for arg in "$@"; do
  case "${arg}" in
    --code)
      open_code=true
      ;;
    *)
      args+=("${arg}")
      ;;
  esac
done

if [[ ${#args[@]} -lt 1 ]]; then
  usage
  exit 1
fi

case "${args[0]}" in
  --list)
    list_specs
    exit 0
    ;;
  --all)
    if [[ ${#args[@]} -ne 2 ]]; then
      usage
      exit 1
    fi
    agent="${args[1]}"
    mapfile -t specs < <(list_specs)
    ;;
  *)
    if [[ ${#args[@]} -ne 2 ]]; then
      usage
      exit 1
    fi
    specs=("${args[0]}")
    agent="${args[1]}"
    ;;
esac

case "${agent}" in
  codex|claude)
    ;;
  *)
    echo "Unsupported agent: ${agent}" >&2
    echo "Supported agents: codex, claude" >&2
    exit 1
    ;;
esac

mapfile -t known_specs < <(list_specs)
if [[ ${#known_specs[@]} -eq 0 ]]; then
  echo "No spec-test directories found (expected top-level TASK.md files)." >&2
  exit 1
fi

mkdir -p "${worktrees_root}"

for spec in "${specs[@]}"; do
  spec_found=false
  for known in "${known_specs[@]}"; do
    if [[ "${spec}" == "${known}" ]]; then
      spec_found=true
      break
    fi
  done

  if [[ "${spec_found}" != "true" ]]; then
    echo "Unknown spec: ${spec}" >&2
    echo "Available specs:" >&2
    printf '  %s\n' "${known_specs[@]}" >&2
    exit 1
  fi

  wt_name="${spec}-${agent}"
  wt_path="${worktrees_root}/${wt_name}"
  branch_name="wt/${wt_name}"

  if git -C "${repo_root}" worktree list --porcelain | grep -Fqx "worktree ${wt_path}"; then
    echo "Worktree already exists: ${wt_path}"
  else
    if [[ -e "${wt_path}" ]]; then
      echo "Path exists but is not a worktree: ${wt_path}" >&2
      exit 1
    fi

    if git -C "${repo_root}" show-ref --verify --quiet "refs/heads/${branch_name}"; then
      git -C "${repo_root}" worktree add "${wt_path}" "${branch_name}"
    else
      git -C "${repo_root}" worktree add -b "${branch_name}" "${wt_path}"
    fi
  fi

  if [[ "${open_code}" == "true" ]]; then
    if command -v code >/dev/null 2>&1; then
      (cd "${wt_path}" && code .)
    else
      echo "VS Code 'code' command not found; skipping launch for ${wt_path}." >&2
    fi
  fi
done
