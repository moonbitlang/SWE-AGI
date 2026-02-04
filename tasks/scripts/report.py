#!/usr/bin/env python3
"""Generate a metrics report from all branches with run-metrics.json."""

import json
import subprocess
import sys
from pathlib import Path


def get_branches():
    """Get all local and remote branch names."""
    result = subprocess.run(
        ["git", "branch", "-a", "--format=%(refname:short)"],
        capture_output=True,
        text=True,
        check=True,
    )
    branches = set()
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Skip HEAD pointer
        if line == "origin/HEAD":
            continue
        # Normalize remote branches
        if line.startswith("origin/"):
            branches.add(line[7:])  # Remove 'origin/' prefix
        else:
            branches.add(line)
    return sorted(branches)


def get_metrics_from_branch(branch):
    """Read run-metrics.json from a branch without checking out."""
    # Extract spec from branch name (format: <spec>/<rest>)
    if "/" not in branch:
        return None
    spec = branch.split("/")[0]

    result = subprocess.run(
        ["git", "show", f"{branch}:{spec}/run-metrics.json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def format_duration(ms):
    """Format milliseconds as human-readable duration."""
    seconds = ms // 1000
    minutes = seconds // 60
    hours = minutes // 60

    if hours > 0:
        return f"{hours}h {minutes % 60}m {seconds % 60}s"
    elif minutes > 0:
        return f"{minutes}m {seconds % 60}s"
    else:
        return f"{seconds}s"


def generate_report(metrics_by_branch):
    """Generate markdown report content."""
    lines = [
        "# Test Results Report",
        "",
    ]

    # Group branches by spec name
    specs = {}
    for branch, metrics in metrics_by_branch.items():
        spec = branch.split("/")[0]
        if spec not in specs:
            specs[spec] = []
        specs[spec].append((branch, metrics))

    # Sort specs alphabetically, and branches within each spec by start_time
    for spec in sorted(specs.keys()):
        deduped = {}
        unknown_entries = []
        for branch, metrics in specs[spec]:
            runner = metrics.get("runner", "unknown")
            if runner == "unknown":
                unknown_entries.append((branch, metrics))
                continue
            existing = deduped.get(runner)
            if existing is None:
                deduped[runner] = (branch, metrics)
                continue
            existing_metrics = existing[1]
            new_key = (
                metrics.get("start_time") or "",
                metrics.get("end_time") or "",
            )
            old_key = (
                existing_metrics.get("start_time") or "",
                existing_metrics.get("end_time") or "",
            )
            if new_key > old_key:
                deduped[runner] = (branch, metrics)

        branches = list(deduped.values()) + unknown_entries
        branches = sorted(branches, key=lambda x: x[1].get("start_time", ""))

        lines.append(f"## {spec}")
        lines.append("")
        lines.append("| Branch | Runner | Duration | Pass Rate | Tests (Pass/Fail/Total) |")
        lines.append("|--------|--------|----------|-----------|-------------------------|")

        for branch, metrics in branches:
            runner = metrics.get("runner", "unknown")
            elapsed_ms = metrics.get("elapsed_ms", 0)
            duration = format_duration(elapsed_ms)

            test_results = metrics.get("test_results") or {}
            total = test_results.get("total_tests", 0)
            passed = test_results.get("passed", 0)
            failed = test_results.get("failed", 0)

            if total > 0:
                pass_rate = f"{(passed / total) * 100:.1f}%"
            else:
                pass_rate = "N/A"

            tests_summary = f"{passed}/{failed}/{total}"

            lines.append(f"| {branch} | {runner} | {duration} | {pass_rate} | {tests_summary} |")

        lines.append("")

    return "\n".join(lines)


def main():
    repo_root = Path(__file__).parent.parent
    report_path = repo_root / "report.md"

    branches = get_branches()
    metrics_by_branch = {}

    for branch in branches:
        metrics = get_metrics_from_branch(branch)
        if metrics:
            metrics_by_branch[branch] = metrics

    if not metrics_by_branch:
        print("No branches with run-metrics.json found.", file=sys.stderr)
        sys.exit(1)

    report_content = generate_report(metrics_by_branch)
    report_path.write_text(report_content)
    print(f"Report generated: {report_path}")


if __name__ == "__main__":
    main()
