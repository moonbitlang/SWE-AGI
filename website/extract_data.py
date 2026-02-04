#!/usr/bin/env python3
"""Extract evaluation data from SWE-AGI-Eval and generate leaderboards.json."""

import json
import importlib.util
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

EVAL_REPO = "https://github.com/moonbitlang/SWE-AGI-Eval.git"


def get_eval_dir() -> Path:
    """Clone SWE-AGI-Eval repo to cache directory and return path."""
    cache_dir = Path(__file__).parent / ".cache" / "SWE-AGI-Eval"

    if cache_dir.exists():
        # Pull latest changes
        print(f"Updating {cache_dir}...")
        subprocess.run(["git", "-C", str(cache_dir), "pull"], check=True)
    else:
        # Clone fresh
        print(f"Cloning {EVAL_REPO}...")
        cache_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth=1", EVAL_REPO, str(cache_dir)], check=True)

    return cache_dir


# Canonical test counts per task
TOTAL_TESTS_BY_TASK = {
    "c99": 117,
    "capnp": 111,
    "cdcl": 4312,
    "csv": 98,
    "ecma262": 618,
    "git_object": 1000,
    "hpack": 129,
    "html5": 8221,
    "ini": 98,
    "jq": 218,
    "lua": 137,
    "protobuf": 141,
    "pug": 251,
    "python": 653,
    "r6rs": 1362,
    "toml": 733,
    "uri": 138,
    "url": 1220,
    "wasm": 800,
    "xml": 735,
    "yaml": 345,
    "zip": 1089,
}

# Task difficulty tiers
DIFFICULTY_TASKS = {
    "easy": ["csv", "git_object", "hpack", "ini", "protobuf", "uri"],
    "medium": ["pug", "yaml", "toml", "xml", "zip", "capnp", "wasm", "url"],
    "hard": ["jq", "html5", "c99", "lua", "ecma262", "python", "r6rs", "cdcl"],
}

# Task display names
TASK_DISPLAY_NAMES = {
    "c99": "C99 Parser",
    "capnp": "Cap'n Proto",
    "cdcl": "CDCL SAT Solver",
    "csv": "CSV Parser",
    "ecma262": "ECMAScript Parser",
    "git_object": "Git Object Parser",
    "hpack": "HPACK Decoder",
    "html5": "HTML5 Parser",
    "ini": "INI Parser",
    "jq": "jq Interpreter",
    "lua": "Lua Interpreter",
    "protobuf": "Protocol Buffers",
    "pug": "Pug Template Engine",
    "python": "Python Parser",
    "r6rs": "R6RS Scheme",
    "toml": "TOML Parser",
    "uri": "URI Parser",
    "url": "URL Parser",
    "wasm": "WebAssembly Validator",
    "xml": "XML Parser",
    "yaml": "YAML Parser",
    "zip": "ZIP Decoder",
}

# Model display names and organizations
MODEL_INFO = {
    "gpt-5.2-codex-high": {"display_name": "GPT-5.2 Codex", "org": "OpenAI"},
    "gpt-5.3-codex-xhigh": {"display_name": "GPT-5.3 Codex", "org": "OpenAI"},
    "claude-opus-4.5": {"display_name": "Claude Opus 4.5", "org": "Anthropic"},
    "claude-opus-4.6": {"display_name": "Claude Opus 4.6", "org": "Anthropic"},
    "claude-sonnet-4.5": {"display_name": "Claude Sonnet 4.5", "org": "Anthropic"},
    "deepseek-v3.2": {"display_name": "DeepSeek V3.2", "org": "DeepSeek"},
    "gemini-3-flash-preview": {"display_name": "Gemini 3 Flash", "org": "Google"},
    "gemini-3-pro-preview": {"display_name": "Gemini 3 Pro", "org": "Google"},
    "glm-4.7": {"display_name": "GLM-4.7", "org": "Zhipu AI"},
    "kimi-k2.5": {"display_name": "Kimi K2.5", "org": "Moonshot AI"},
    "qwen3-max-2026-01-23": {"display_name": "Qwen3 Max", "org": "Alibaba"},
    "step-3.5-flash": {"display_name": "Step 3.5 Flash", "org": "StepFun"},
}

# Behavior analysis categories from SWE-AGI-Eval/report/behavior_stats.py
BEHAVIOR_KEYS = (
    "spec_understanding",
    "planning",
    "code_understanding",
    "code_writing",
    "debugging",
    "hygiene",
    "external_search",
    "other",
)

BEHAVIOR_HEADERS = {
    "spec_understanding": "Spec Understanding",
    "planning": "Planning",
    "code_understanding": "Code Understanding",
    "code_writing": "Code Writing",
    "debugging": "Debugging",
    "hygiene": "Hygiene",
    "external_search": "External Search",
    "other": "Other",
}

# EVAL_DIR is set dynamically via get_eval_dir()


def code_loc_for_task_dir(task_dir: Path) -> int:
    """Count total lines of *.mbt files excluding test files."""
    total = 0
    excluded_dirs = {"target", "_build", ".mooncakes"}
    for path in task_dir.rglob("*.mbt"):
        if any(part in excluded_dirs for part in path.parts):
            continue
        name = path.name
        if name.endswith("_pub_test.mbt") or name.endswith("_priv_test.mbt"):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                total += sum(1 for _ in f)
        except OSError:
            continue
    return total


def discover_models(base_dir: Path) -> list[Path]:
    """Find all model directories."""
    models = []
    for entry in sorted(base_dir.iterdir()):
        if entry.is_dir() and not entry.name.startswith('.') and entry.name != 'report':
            models.append(entry)
    return models


def _read_tail_text(path: Path, max_bytes: int = 200_000) -> str:
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            start = max(0, size - max_bytes)
            f.seek(start, 0)
            blob = f.read()
        return blob.decode("utf-8", errors="ignore")
    except OSError:
        return ""


def _extract_usage_cost_from_log(log_path: Path) -> tuple[Optional[int], Optional[int], Optional[float], Optional[int]]:
    """Extract total (input_tokens, output_tokens, cost_usd, cached_input_tokens) from a log.yaml."""
    if not log_path.exists():
        return None, None, None, None

    tail = _read_tail_text(log_path)
    if not tail:
        return None, None, None, None

    # Gemini runner logs
    if "stats:" in tail and "input_tokens:" in tail and "output_tokens:" in tail:
        stats_idx = tail.rfind("stats:")
        stats_chunk = tail[stats_idx:]
        m_in = re.search(r"\binput_tokens:\s*(\d+)\b", stats_chunk)
        m_out = re.search(r"\boutput_tokens:\s*(\d+)\b", stats_chunk)
        if m_in and m_out:
            return int(m_in.group(1)), int(m_out.group(1)), None, None

    # Claude Code-style logs
    if "total_cost_usd:" in tail and "usage:" in tail:
        cost_idx = tail.rfind("total_cost_usd:")
        cost_chunk = tail[cost_idx:]
        m_cost = re.search(r"\btotal_cost_usd:\s*([0-9]+(?:\.[0-9]+)?)\b", cost_chunk)
        usage_idx = tail.rfind("usage:")
        usage_chunk = tail[usage_idx:]

        def _int_from(key):
            m = re.search(rf"\b{re.escape(key)}:\s*(\d+)\b", usage_chunk)
            return int(m.group(1)) if m else None

        in_tokens = _int_from("input_tokens")
        out_tokens = _int_from("output_tokens")
        cache_creation = _int_from("cache_creation_input_tokens") or 0
        cache_read = _int_from("cache_read_input_tokens") or 0
        if in_tokens is not None and out_tokens is not None:
            cost = float(m_cost.group(1)) if m_cost else None
            return in_tokens + cache_creation + cache_read, out_tokens, cost, None

    # Codex logs
    start_idx = tail.rfind("type: turn.completed")
    chunk = tail[start_idx:] if start_idx != -1 else tail[tail.rfind("usage:"):]
    if "input_tokens:" in chunk and "output_tokens:" in chunk:
        m_in = re.search(r"\binput_tokens:\s*(\d+)\b", chunk)
        m_out = re.search(r"\boutput_tokens:\s*(\d+)\b", chunk)
        if m_in and m_out:
            m_cached = re.search(r"\bcached_input_tokens:\s*(\d+)\b", chunk)
            cached = int(m_cached.group(1)) if m_cached else None
            return int(m_in.group(1)), int(m_out.group(1)), None, cached

    return None, None, None, None


def cost_scale_for_model(model_name: str) -> float:
    """Apply repo-specific normalization factors."""
    if model_name == "glm-4.7":
        return 0.1
    if model_name == "deepseek-v3.2":
        return 1.0 / 30.0
    return 1.0


def estimate_cost_usd_for_model(model_name: str, result: dict) -> Optional[float]:
    """Best-effort cost estimate when the front-end didn't log cost."""
    in_tokens = result.get("tokens_in")
    out_tokens = result.get("tokens_out")
    if not isinstance(in_tokens, int) or not isinstance(out_tokens, int):
        return None

    if model_name in ("gpt-5.2-codex-high", "gpt-5.3-codex-xhigh"):
        cached_in = result.get("tokens_cached_in")
        cached = int(cached_in) if isinstance(cached_in, int) else 0
        cached = max(0, min(cached, in_tokens))
        uncached = in_tokens - cached
        input_rate = 1.75
        cached_input_rate = 0.175
        output_rate = 14.0
        return (uncached * input_rate + cached * cached_input_rate + out_tokens * output_rate) / 1_000_000

    if model_name == "gemini-3-flash-preview":
        input_rate = 0.50
        output_rate = 3.00
        return (in_tokens * input_rate + out_tokens * output_rate) / 1_000_000

    return None


def get_cost_for_model(model_name: str, result: dict) -> Optional[float]:
    """Get cost with scaling applied, or estimate if not available."""
    cost = result.get("cost_usd")
    if isinstance(cost, (int, float)):
        return cost * cost_scale_for_model(model_name)
    return estimate_cost_usd_for_model(model_name, result)


def load_behavior_stats_module(eval_dir: Path) -> Optional[Any]:
    """Load behavior_stats.py dynamically for behavior/action counting."""
    module_path = eval_dir / "report" / "behavior_stats.py"
    if not module_path.exists():
        print(f"Warning: {module_path} not found; behavior metrics will be unavailable.")
        return None

    module_name = "swe_agi_behavior_stats_runtime"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        print("Warning: Failed to load behavior_stats module spec; behavior metrics will be unavailable.")
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"Warning: Failed to import behavior_stats.py: {e}; behavior metrics will be unavailable.")
        sys.modules.pop(module_name, None)
        return None

    return module


def behavior_stats_for_task(task_dir: Path, behavior_stats_module: Optional[Any]) -> Optional[dict[str, int]]:
    """Collect behavior totals for a task by reusing report/behavior_stats.py logic."""
    if behavior_stats_module is None:
        return None

    log_path = task_dir / "log.yaml"
    if not log_path.exists():
        return None

    try:
        log_kind = behavior_stats_module._detect_log_kind(log_path)
        if log_kind == "codex":
            stats = behavior_stats_module.analyze_codex_log(log_path)
        elif log_kind == "tool_use":
            stats = behavior_stats_module.analyze_tool_use_log(log_path)
        elif log_kind == "tool_calls":
            stats = behavior_stats_module.analyze_tool_calls_log(log_path)
        else:
            return None
    except Exception as e:
        print(f"Warning: Failed to parse actions for {task_dir}: {e}")
        return None

    total_actions = getattr(stats, "total", None)
    if not isinstance(total_actions, (int, float)):
        return None

    counts = getattr(stats, "counts", None)
    behavior: dict[str, int] = {"total": int(total_actions)}
    for key in BEHAVIOR_KEYS:
        value = None
        if isinstance(counts, dict):
            value = counts.get(key)
        if not isinstance(value, (int, float)):
            value = 0
        behavior[key] = int(value)
    return behavior


def load_task_results(model_dir: Path, behavior_stats_module: Optional[Any]) -> list[dict]:
    """Load run-metrics.json from all tasks in a model directory."""
    results = []
    for task_dir in sorted(model_dir.iterdir()):
        if not task_dir.is_dir():
            continue
        metrics_file = task_dir / "run-metrics.json"
        if metrics_file.exists():
            try:
                with open(metrics_file) as f:
                    data = json.load(f)
                    data['task'] = task_dir.name
                    data['code_loc'] = code_loc_for_task_dir(task_dir)
                    in_tokens, out_tokens, cost, cached_in_tokens = _extract_usage_cost_from_log(task_dir / "log.yaml")
                    data["tokens_in"] = in_tokens
                    data["tokens_out"] = out_tokens
                    data["tokens_cached_in"] = cached_in_tokens
                    data["cost_usd"] = cost
                    behavior = behavior_stats_for_task(task_dir, behavior_stats_module)
                    data["behavior"] = behavior
                    data["actions"] = behavior.get("total") if behavior else None
                    results.append(data)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load {metrics_file}: {e}")
    return results


def task_passed(task_name: str, result: dict) -> bool:
    """Check if a task passed (all canonical tests passed)."""
    total = total_tests_for_task(task_name, result)
    passed = passed_tests_for_task(task_name, result)
    return total > 0 and passed >= total


def total_tests_for_task(task_name: str, result: dict) -> int:
    """Return canonical total test count for a task."""
    if task_name in TOTAL_TESTS_BY_TASK:
        return TOTAL_TESTS_BY_TASK[task_name]
    test_results = result.get("test_results") or {}
    return test_results.get("total_tests", 0) or 0


def passed_tests_for_task(task_name: str, result: dict) -> int:
    """Return adjusted passed test count for a task."""
    test_results = result.get("test_results") or {}
    passed = test_results.get("passed", 0) or 0
    reported_total = test_results.get("total_tests", 0) or 0
    canonical_total = total_tests_for_task(task_name, result)

    if canonical_total > 0 and reported_total > canonical_total:
        extra = reported_total - canonical_total
        passed = max(0, passed - extra)

    if canonical_total > 0:
        passed = min(passed, canonical_total)

    return passed


def get_task_difficulty(task_name: str) -> str:
    """Get difficulty tier for a task."""
    for difficulty, tasks in DIFFICULTY_TASKS.items():
        if task_name in tasks:
            return difficulty
    return "unknown"


def average_task_pass_rate(results: list[dict]) -> float:
    """Compute unweighted mean of per-task pass rates."""
    if not results:
        return 0.0

    per_task_rates = []
    for r in results:
        task_id = r.get("task", "")
        total = total_tests_for_task(task_id, r)
        passed = passed_tests_for_task(task_id, r)
        per_task_rates.append((passed / total * 100) if total > 0 else 0.0)

    return sum(per_task_rates) / len(per_task_rates)


def generate_leaderboards_json(eval_dir: Path) -> dict:
    """Generate the leaderboards.json data structure."""
    models = discover_models(eval_dir)
    behavior_stats_module = load_behavior_stats_module(eval_dir)

    all_results = {}
    for model_dir in models:
        results = load_task_results(model_dir, behavior_stats_module)
        if results:
            all_results[model_dir.name] = results

    # Build models list
    models_list = []
    for model_id in sorted(all_results.keys()):
        info = MODEL_INFO.get(model_id, {"display_name": model_id, "org": "Unknown"})
        models_list.append({
            "id": model_id,
            "display_name": info["display_name"],
            "org": info["org"],
        })

    # Build tasks list
    tasks_list = []
    for task_id in sorted(TOTAL_TESTS_BY_TASK.keys()):
        tasks_list.append({
            "id": task_id,
            "display_name": TASK_DISPLAY_NAMES.get(task_id, task_id),
            "difficulty": get_task_difficulty(task_id),
            "total_tests": TOTAL_TESTS_BY_TASK[task_id],
        })

    # Build results list
    results_list = []
    for model_id, model_results in all_results.items():
        for result in model_results:
            task_id = result.get("task", "")
            if not task_id:
                continue

            total = total_tests_for_task(task_id, result)
            passed = passed_tests_for_task(task_id, result)
            pass_rate = (passed / total * 100) if total > 0 else 0.0

            results_list.append({
                "model_id": model_id,
                "task_id": task_id,
                "difficulty": get_task_difficulty(task_id),
                "task_passed": task_passed(task_id, result),
                "exit_code": result.get("exit_code"),
                "tests": {
                    "total": total,
                    "passed": passed,
                    "pass_rate": round(pass_rate, 2),
                },
                "metrics": {
                    "elapsed_ms": result.get("elapsed_ms"),
                    "code_loc": result.get("code_loc"),
                    "tokens_in": result.get("tokens_in"),
                    "tokens_out": result.get("tokens_out"),
                    "cost_usd": get_cost_for_model(model_id, result),
                    "actions": result.get("actions"),
                    "behavior": result.get("behavior"),
                },
            })

    # Build summaries
    summaries = {
        "by_model": [],
        "by_difficulty": [],
    }

    # Summary by model
    for model_id in sorted(all_results.keys()):
        model_results = all_results[model_id]
        total_tasks = len(model_results)
        passed_tasks = sum(1 for r in model_results if task_passed(r.get("task", ""), r))

        total_tests = 0
        passed_tests = 0
        total_cost = 0.0
        total_time_ms = 0
        total_actions = 0
        tasks_with_actions = 0

        for r in model_results:
            task_id = r.get("task", "")
            t_total = total_tests_for_task(task_id, r)
            t_passed = passed_tests_for_task(task_id, r)
            total_tests += t_total
            passed_tests += t_passed

            cost = get_cost_for_model(model_id, r)
            if cost:
                total_cost += cost
            if r.get("elapsed_ms"):
                total_time_ms += r["elapsed_ms"]
            actions = r.get("actions")
            if isinstance(actions, (int, float)):
                total_actions += actions
                tasks_with_actions += 1

        pass_rate = average_task_pass_rate(model_results)
        avg_actions = (total_actions / tasks_with_actions) if tasks_with_actions > 0 else None

        summaries["by_model"].append({
            "model_id": model_id,
            "tasks_passed": passed_tasks,
            "tasks_total": total_tasks,
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "pass_rate": round(pass_rate, 2),
            "total_cost_usd": round(total_cost, 2) if total_cost > 0 else None,
            "total_time_ms": total_time_ms,
            "avg_actions": round(avg_actions, 2) if avg_actions is not None else None,
        })

    # Summary by difficulty for each model
    for difficulty in ["easy", "medium", "hard"]:
        tasks_in_tier = set(DIFFICULTY_TASKS.get(difficulty, []))

        for model_id in sorted(all_results.keys()):
            model_results = all_results[model_id]
            tier_results = [r for r in model_results if r.get("task") in tasks_in_tier]

            if not tier_results:
                continue

            total_tasks = len(tier_results)
            passed_tasks = sum(1 for r in tier_results if task_passed(r.get("task", ""), r))

            total_tests = 0
            passed_tests = 0
            total_cost = 0.0
            total_time_ms = 0
            total_loc = 0
            total_actions = 0
            tasks_with_actions = 0

            for r in tier_results:
                task_id = r.get("task", "")
                t_total = total_tests_for_task(task_id, r)
                t_passed = passed_tests_for_task(task_id, r)
                total_tests += t_total
                passed_tests += t_passed

                cost = get_cost_for_model(model_id, r)
                if cost:
                    total_cost += cost
                if r.get("elapsed_ms"):
                    total_time_ms += r["elapsed_ms"]
                if r.get("code_loc"):
                    total_loc += r["code_loc"]
                actions = r.get("actions")
                if isinstance(actions, (int, float)):
                    total_actions += actions
                    tasks_with_actions += 1

            pass_rate = average_task_pass_rate(tier_results)
            avg_time_ms = total_time_ms / total_tasks if total_tasks > 0 else 0
            avg_loc = total_loc / total_tasks if total_tasks > 0 else 0
            avg_actions = (total_actions / tasks_with_actions) if tasks_with_actions > 0 else None

            summaries["by_difficulty"].append({
                "difficulty": difficulty,
                "model_id": model_id,
                "tasks_passed": passed_tasks,
                "tasks_total": total_tasks,
                "tests_passed": passed_tests,
                "tests_total": total_tests,
                "pass_rate": round(pass_rate, 2),
                "total_cost_usd": round(total_cost, 2) if total_cost > 0 else None,
                "avg_time_ms": round(avg_time_ms),
                "avg_code_loc": round(avg_loc),
                "avg_actions": round(avg_actions, 2) if avg_actions is not None else None,
            })

    return {
        "generated_at": datetime.now().isoformat(),
        "metadata": {
            "difficulty_tiers": DIFFICULTY_TASKS,
            "total_tests_by_task": TOTAL_TESTS_BY_TASK,
            "actions_metric": "Avg Actions is the per-model mean of per-task total tool actions counted by report/behavior_stats.py.",
            "behavior_categories": BEHAVIOR_HEADERS,
        },
        "models": models_list,
        "tasks": tasks_list,
        "results": results_list,
        "summaries": summaries,
    }


def main():
    """Main entry point."""
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"
    data_dir.mkdir(exist_ok=True)

    output_file = data_dir / "leaderboards.json"

    eval_dir = get_eval_dir()
    print(f"Extracting data from: {eval_dir}")
    data = generate_leaderboards_json(eval_dir)

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Generated: {output_file}")
    print(f"  Models: {len(data['models'])}")
    print(f"  Tasks: {len(data['tasks'])}")
    print(f"  Results: {len(data['results'])}")


if __name__ == "__main__":
    main()
