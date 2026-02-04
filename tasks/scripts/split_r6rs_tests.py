#!/usr/bin/env python3
"""
Split R6RS test files into public (~10%) and private (~90%) test files.
Uses deterministic random selection with seed 42 for reproducibility.
"""

import random
import re
from pathlib import Path

# Deterministic seed for reproducibility
RANDOM_SEED = 42

# Directory containing the test files
TEST_DIR = Path(__file__).parent.parent / "r6rs" / "racket-r6rs-test"


def parse_test_file(filepath: Path) -> tuple[str, list[str]]:
    """
    Parse a test file and extract header and individual test blocks.

    Returns:
        tuple: (header_comment, list_of_test_blocks)
    """
    content = filepath.read_text()

    # Split by ///| markers
    parts = re.split(r'\n(?=///\|)', content)

    # First part is the header (comments before first test)
    header = parts[0].rstrip()

    # Rest are test blocks
    tests = parts[1:] if len(parts) > 1 else []

    return header, tests


def split_tests(tests: list[str], pub_ratio: float = 0.1, seed: int = RANDOM_SEED) -> tuple[list[str], list[str]]:
    """
    Randomly split tests into public and private sets.

    Args:
        tests: List of test blocks
        pub_ratio: Ratio of tests to make public (default 10%)
        seed: Random seed for reproducibility

    Returns:
        tuple: (public_tests, private_tests)
    """
    # Create a local random instance with fixed seed for this file
    rng = random.Random(seed)

    # Shuffle indices
    indices = list(range(len(tests)))
    rng.shuffle(indices)

    # Calculate number of public tests (at least 1 if there are any tests)
    num_public = max(1, round(len(tests) * pub_ratio)) if tests else 0

    # Split indices
    pub_indices = set(indices[:num_public])

    # Separate tests maintaining original order
    public_tests = []
    private_tests = []

    for i, test in enumerate(tests):
        if i in pub_indices:
            public_tests.append(test)
        else:
            private_tests.append(test)

    return public_tests, private_tests


def write_test_file(filepath: Path, header: str, tests: list[str], test_type: str):
    """Write tests to a new file with appropriate header."""
    if not tests:
        return

    # Modify header to indicate pub/priv
    header_lines = header.split('\n')
    if header_lines:
        # Add annotation to first line
        header_lines[0] = header_lines[0].rstrip() + f" ({test_type})"

    modified_header = '\n'.join(header_lines)

    # Combine header and tests
    content = modified_header + '\n\n' + '\n'.join(tests)

    filepath.write_text(content)
    print(f"  Written: {filepath.name} ({len(tests)} tests)")


def process_file(filepath: Path) -> dict:
    """Process a single test file and create pub/priv versions."""
    print(f"\nProcessing: {filepath.name}")

    # Parse the file
    header, tests = parse_test_file(filepath)
    print(f"  Found {len(tests)} tests")

    if not tests:
        print("  No tests found, skipping")
        return {"original": 0, "public": 0, "private": 0}

    # Generate a unique seed for this file based on filename
    # This ensures each file gets different random selection but still reproducible
    file_seed = RANDOM_SEED + hash(filepath.name) % 10000

    # Split tests
    public_tests, private_tests = split_tests(tests, seed=file_seed)

    print(f"  Split: {len(public_tests)} public, {len(private_tests)} private")

    # Generate output filenames
    base_name = filepath.stem.replace('_test', '')
    pub_path = filepath.parent / f"{base_name}_pub_test.mbt"
    priv_path = filepath.parent / f"{base_name}_priv_test.mbt"

    # Write files
    write_test_file(pub_path, header, public_tests, "public")
    write_test_file(priv_path, header, private_tests, "private")

    return {
        "original": len(tests),
        "public": len(public_tests),
        "private": len(private_tests)
    }


def main():
    """Main entry point."""
    print("=" * 60)
    print("R6RS Test Splitter")
    print("=" * 60)
    print(f"Random seed: {RANDOM_SEED}")
    print(f"Test directory: {TEST_DIR}")

    # Find all test files (excluding already split ones)
    test_files = sorted(TEST_DIR.glob("r6rs_*_test.mbt"))
    test_files = [f for f in test_files if '_pub_test.mbt' not in f.name and '_priv_test.mbt' not in f.name]

    print(f"\nFound {len(test_files)} test files to process")

    # Track statistics
    total_stats = {"original": 0, "public": 0, "private": 0}

    # Process each file
    for filepath in test_files:
        stats = process_file(filepath)
        for key in total_stats:
            total_stats[key] += stats[key]

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total tests processed: {total_stats['original']}")
    print(f"Public tests: {total_stats['public']} ({total_stats['public']/total_stats['original']*100:.1f}%)")
    print(f"Private tests: {total_stats['private']} ({total_stats['private']/total_stats['original']*100:.1f}%)")
    print(f"Verification: {total_stats['public'] + total_stats['private']} = {total_stats['original']}")

    if total_stats['public'] + total_stats['private'] == total_stats['original']:
        print("\n✓ All tests accounted for!")
    else:
        print("\n✗ ERROR: Test count mismatch!")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
