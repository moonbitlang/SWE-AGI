#!/usr/bin/env python3
"""
Count the number of test cases in each spec-test directory.
Reports #pub and #priv test counts for verification.
"""

import argparse
import re
from pathlib import Path


# Directories to exclude from processing
EXCLUDED_DIRS = {
    # Hidden directories
    ".git",
    ".venv",
    ".claude",
    ".github",
    # Build directories
    "_build",
    "target",
    "worktrees",
    # Infrastructure
    "scripts",
    "docker",
    "tests",
    "autopsy",
    "moonbit-agent-guide",
}

# Pattern to match test declarations in MoonBit
# Matches: test "name" { ... }, test { ... }, async test "name" { ... }
TEST_PATTERN = re.compile(r"^\s*(?:async\s+)?test\s+(?:\"[^\"]*\"\s*)?\{", re.MULTILINE)


def find_spec_directories(root: Path) -> list[Path]:
    """Find all spec directories in the root, excluding infrastructure dirs."""
    spec_dirs = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if entry.name in EXCLUDED_DIRS:
            continue
        spec_dirs.append(entry)
    return spec_dirs


def count_tests_in_file(file_path: Path) -> int:
    """Count the number of test blocks in a file."""
    content = file_path.read_text()
    matches = TEST_PATTERN.findall(content)
    return len(matches)


def count_tests_in_directory(spec_dir: Path) -> tuple[int, int]:
    """
    Count tests in a spec directory.

    Returns:
        (pub_count, priv_count) - number of public and private tests
    """
    pub_count = 0
    priv_count = 0

    for entry in spec_dir.iterdir():
        if not entry.is_file():
            continue
        if not entry.name.endswith("_test.mbt"):
            continue

        count = count_tests_in_file(entry)

        if entry.name.endswith("_priv_test.mbt"):
            priv_count += count
        else:
            pub_count += count

    return pub_count, priv_count


def main():
    parser = argparse.ArgumentParser(
        description="Count test cases in spec directories"
    )
    parser.add_argument(
        "--spec",
        type=str,
        help="Count tests in a single spec directory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    args = parser.parse_args()

    # Find root directory (parent of scripts/)
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent

    results = {}

    if args.spec:
        spec_dir = root_dir / args.spec
        if not spec_dir.is_dir():
            print(f"Error: Spec directory not found: {args.spec}")
            return 1
        pub_count, priv_count = count_tests_in_directory(spec_dir)
        results[args.spec] = {"pub": pub_count, "priv": priv_count}
    else:
        spec_dirs = find_spec_directories(root_dir)
        for spec_dir in spec_dirs:
            pub_count, priv_count = count_tests_in_directory(spec_dir)
            results[spec_dir.name] = {"pub": pub_count, "priv": priv_count}

    if args.json:
        import json

        # Add ratio to JSON output
        for spec in results:
            pub = results[spec]["pub"]
            priv = results[spec]["priv"]
            total = pub + priv
            results[spec]["ratio"] = pub / total if total > 0 else 0.0

        print(json.dumps(results, indent=2))
    else:
        # Print table format
        total_pub = 0
        total_priv = 0

        print(f"{'Spec':<15} {'#pub':>8} {'#priv':>8} {'Total':>8} {'Ratio':>8}")
        print("-" * 50)

        for spec, counts in sorted(results.items()):
            pub = counts["pub"]
            priv = counts["priv"]
            total = pub + priv
            ratio = pub / total if total > 0 else 0.0
            total_pub += pub
            total_priv += priv
            print(f"{spec:<15} {pub:>8} {priv:>8} {total:>8} {ratio:>8.2f}")

        print("-" * 50)
        grand_total = total_pub + total_priv
        overall_ratio = total_pub / grand_total if grand_total > 0 else 0.0
        print(f"{'TOTAL':<15} {total_pub:>8} {total_priv:>8} {grand_total:>8} {overall_ratio:>8.2f}")

    return 0


if __name__ == "__main__":
    exit(main())
