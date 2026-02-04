#!/usr/bin/env python3
"""
Refactors test files from easy/mid/hard to valid/invalid grouping.
Usage: python3 refactor_tests.py <spec_dir> <spec_name>
Example: python3 refactor_tests.py toml toml
"""

import re
import sys
from pathlib import Path


def parse_tests(content: str) -> list[tuple[str, str]]:
    """Parse a test file and return list of (test_name, test_block) tuples."""
    tests = []
    # Split by ///| marker
    parts = re.split(r'(?=///\|)', content)

    for part in parts:
        part = part.strip()
        if not part or not part.startswith('///|'):
            continue

        # Extract test name
        match = re.search(r'test\s+"([^"]+)"', part)
        if match:
            test_name = match.group(1)
            tests.append((test_name, part))

    return tests


def categorize_test(test_name: str, test_content: str) -> str:
    """Categorize test as valid or invalid based on name or content."""
    # Name-based categorization (invalid takes precedence)
    if any(test_name.startswith(p) for p in ['invalid/', 'invalid_']):
        return 'invalid'
    # w3c/not-wf tests are invalid (not well-formed XML)
    if 'w3c/not-wf' in test_name or 'not_wf' in test_name:
        return 'invalid'
    # "parse failure" tests are invalid
    if 'parse failure' in test_name.lower():
        return 'invalid'

    # Valid includes: valid/, edge/, mid/, hard/ prefixes (all are valid inputs)
    if any(test_name.startswith(p) for p in ['valid/', 'valid_', 'edge/', 'edge_', 'mid/', 'mid_', 'hard/', 'hard_']):
        return 'valid'
    # w3c/valid tests are valid
    if 'w3c/valid' in test_name:
        return 'valid'

    # Content-based categorization (for tests without standard prefixes)
    # Invalid tests: expect Err and succeed silently
    if 'Err(_) => ()' in test_content or 'Err(_e) => ()' in test_content or 'Err(e) => ()' in test_content:
        return 'invalid'

    # Invalid tests: assert error occurred
    # Patterns: (try? ...) is Err(_), assert_true(has_error), assert_true(... is None)
    if '(try?' in test_content and 'is Err' in test_content:
        return 'invalid'
    if 'assert_true(has_error)' in test_content:
        return 'invalid'
    if 'assert_true(' in test_content and 'is None)' in test_content:
        return 'invalid'

    # Invalid tests: expect failure and call fail() in Ok branch
    # Pattern: Ok(...) => { ... fail(...) ... }
    if 'Ok(' in test_content:
        # Check if there's a fail() call before the Err branch
        ok_section = test_content.split('Ok(')[1] if 'Ok(' in test_content else ''
        err_pos = ok_section.find('Err')
        if err_pos > 0:
            ok_section = ok_section[:err_pos]
        if 'fail(' in ok_section:
            return 'invalid'
        # Valid tests: expect Ok and process the result
        return 'valid'

    # Tests using inspect() or assert_eq() are valid (expect success)
    if 'inspect(' in test_content or 'assert_eq(' in test_content:
        return 'valid'

    # Tests using assert_true with positive conditions are valid
    if 'assert_true(' in test_content:
        # Check if it's checking for success (events.length() > 0, etc.)
        if 'length()' in test_content or 'is Some' in test_content:
            return 'valid'

    # guard ... else { fail(...) } pattern with assertion after is valid
    if 'guard' in test_content and 'else' in test_content and 'fail(' in test_content:
        return 'valid'

    # Tests using ignore() to just check parsing completes are valid
    if 'ignore(' in test_content:
        return 'valid'

    return 'uncategorized'


def refactor_spec(spec_dir: Path, spec_name: str) -> dict[str, int]:
    """Refactor a spec's test files from easy/mid/hard to valid/invalid."""
    # Find all easy/mid/hard test files
    easy_file = spec_dir / f"{spec_name}_easy_test.mbt"
    mid_file = spec_dir / f"{spec_name}_mid_test.mbt"
    hard_file = spec_dir / f"{spec_name}_hard_test.mbt"

    input_files = [f for f in [easy_file, mid_file, hard_file] if f.exists()]

    if not input_files:
        print(f"No easy/mid/hard test files found in {spec_dir}")
        return {}

    # Collect all tests, removing duplicates
    seen_tests = set()
    all_tests = []
    duplicates = 0
    for file in input_files:
        content = file.read_text()
        tests = parse_tests(content)
        for test_name, test_block in tests:
            if test_name in seen_tests:
                duplicates += 1
                print(f"  Skipping duplicate: {test_name}")
            else:
                seen_tests.add(test_name)
                all_tests.append((test_name, test_block))
        print(f"  Parsed {len(tests)} tests from {file.name}")

    if duplicates:
        print(f"  Removed {duplicates} duplicate test(s)")

    # Categorize tests (only valid/invalid, no edge)
    categorized = {'valid': [], 'invalid': [], 'uncategorized': []}
    for test_name, test_block in all_tests:
        category = categorize_test(test_name, test_block)
        categorized[category].append(test_block)

    # Report counts
    stats = {k: len(v) for k, v in categorized.items()}
    print(f"  Categorized: valid={stats['valid']}, invalid={stats['invalid']}, "
          f"uncategorized={stats['uncategorized']}")

    # Write output files (only valid and invalid)
    for category in ['valid', 'invalid']:
        if categorized[category]:
            output_file = spec_dir / f"{spec_name}_{category}_test.mbt"
            content = '\n\n'.join(categorized[category])
            output_file.write_text(content + '\n')
            print(f"  Wrote {len(categorized[category])} tests to {output_file.name}")

    # Handle uncategorized
    if categorized['uncategorized']:
        output_file = spec_dir / f"{spec_name}_uncategorized_test.mbt"
        content = '\n\n'.join(categorized['uncategorized'])
        output_file.write_text(content + '\n')
        print(f"  Wrote {len(categorized['uncategorized'])} uncategorized tests to {output_file.name}")

    return stats


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 refactor_tests.py <spec_dir> <spec_name>")
        print("Example: python3 refactor_tests.py toml toml")
        sys.exit(1)

    spec_dir = Path(sys.argv[1])
    spec_name = sys.argv[2]

    if not spec_dir.is_dir():
        print(f"Error: {spec_dir} is not a directory")
        sys.exit(1)

    print(f"Refactoring {spec_name} tests in {spec_dir}...")
    stats = refactor_spec(spec_dir, spec_name)

    if stats:
        total = sum(stats.values())
        print(f"\nTotal: {total} tests processed")
        print("\nTo delete old files after verification, run:")
        print(f"  rm {spec_dir}/{spec_name}_easy_test.mbt {spec_dir}/{spec_name}_mid_test.mbt {spec_dir}/{spec_name}_hard_test.mbt")


if __name__ == '__main__':
    main()
