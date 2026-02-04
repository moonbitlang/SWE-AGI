#!/usr/bin/env python3
"""
Rebalance existing pub/priv test files to achieve ~10% pub / ~90% priv ratio.
"""

import argparse
from pathlib import Path
from split_tests import parse_content, write_test_file


def rebalance_spec(spec_name: str, dry_run: bool = False) -> bool:
    """Rebalance a single spec's test files."""
    spec_dir = Path(spec_name)
    pub_file = spec_dir / f"{spec_name}_pub_test.mbt"
    priv_file = spec_dir / f"{spec_name}_priv_test.mbt"

    if not pub_file.exists():
        print(f"Error: {pub_file} not found")
        return False

    # Parse both files
    pub_helpers, pub_tests = parse_content(pub_file.read_text())

    priv_helpers, priv_tests = [], []
    if priv_file.exists():
        priv_helpers, priv_tests = parse_content(priv_file.read_text())

    # Combine all tests and helpers
    all_tests = pub_tests + priv_tests
    all_helpers = pub_helpers + priv_helpers  # Helpers go to priv

    total = len(all_tests)
    if total < 10:
        pub_count = total  # If < 10 tests, all go to pub
    else:
        pub_count = max(1, round(total * 0.1))

    # Check if already balanced
    if len(pub_tests) == pub_count:
        print(f"{spec_name}: Already balanced ({pub_count} pub, {len(priv_tests)} priv)")
        return True

    # Split
    new_pub_tests = all_tests[:pub_count]
    new_priv_tests = all_tests[pub_count:]

    print(f"{spec_name}: {total} total tests")
    print(f"  Before: {len(pub_tests)} pub, {len(priv_tests)} priv (ratio {len(pub_tests)/total:.2f})")
    print(f"  After:  {pub_count} pub, {len(new_priv_tests)} priv (ratio {pub_count/total:.2f})")

    if not dry_run:
        # Helpers go to pub file so client_data can compile without priv tests
        write_test_file(pub_file, new_pub_tests, all_helpers)
        write_test_file(priv_file, new_priv_tests)
        print(f"  Updated {pub_file.name} and {priv_file.name}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Rebalance pub/priv test files")
    parser.add_argument("specs", nargs="+", help="Spec names to rebalance")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change")
    args = parser.parse_args()

    for spec in args.specs:
        rebalance_spec(spec, args.dry_run)


if __name__ == "__main__":
    main()
