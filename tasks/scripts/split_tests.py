#!/usr/bin/env python3
"""
Script to split MoonBit test files into pub/priv variants.
~10% of tests go to pub file, rest to priv file.
If total tests < 10, all go to pub file (no priv file created).
"""

import re
import sys
from pathlib import Path


def count_braces_outside_strings(line: str) -> int:
    """Count net braces ({-}) in a line, ignoring braces inside string literals.

    This handles:
    - Double-quoted strings "..."
    - Char literals '...'
    - Escape sequences like \\", \\'
    - Raw strings (lines starting with #|)
    """
    # Skip raw string lines entirely - they can contain any characters
    stripped = line.strip()
    if stripped.startswith('#|'):
        return 0

    count = 0
    in_string = False
    in_char = False
    i = 0
    while i < len(line):
        c = line[i]
        if in_string:
            if c == '\\' and i + 1 < len(line):
                i += 2  # Skip escape sequence
                continue
            elif c == '"':
                in_string = False
        elif in_char:
            if c == '\\' and i + 1 < len(line):
                i += 2  # Skip escape sequence
                continue
            elif c == "'":
                in_char = False
        else:
            if c == '"':
                in_string = True
            elif c == "'":
                in_char = True
            elif c == '{':
                count += 1
            elif c == '}':
                count -= 1
        i += 1
    return count


def parse_content(content: str) -> tuple[list[str], list[str]]:
    """Parse file content into helper functions and test blocks.

    Returns:
        A tuple of (helpers, tests) where:
        - helpers: List of non-test code blocks (functions, etc.) that should be included in both files
        - tests: List of test blocks to be split between pub and priv
    """
    lines = content.split('\n')
    helpers = []
    tests = []
    current_block = []
    block_type = None  # 'test', 'helper', or None
    brace_count = 0

    for line in lines:
        if line.strip() == '///|':
            # Start of a new block
            if current_block:
                block_content = '\n'.join(current_block)
                if block_type == 'test':
                    tests.append(block_content)
                elif block_type == 'helper':
                    helpers.append(block_content)
            current_block = [line]
            block_type = None
            brace_count = 0
        elif current_block:
            current_block.append(line)
            # Determine block type if not set yet
            if block_type is None:
                if re.match(r'^(async\s+)?test\s+"', line.strip()):
                    block_type = 'test'
                elif re.match(r'^(async\s+)?(pub\s+)?(priv\s+)?fn\s+', line.strip()):
                    block_type = 'helper'
                elif re.match(r'^(pub\s+)?(priv\s+)?struct\s+', line.strip()):
                    block_type = 'helper'
                elif re.match(r'^(pub\s+)?(priv\s+)?enum\s+', line.strip()):
                    block_type = 'helper'
                elif re.match(r'^(pub\s+)?(priv\s+)?type\s+', line.strip()):
                    block_type = 'helper'
                elif re.match(r'^(pub\s+)?(priv\s+)?typealias\s+', line.strip()):
                    block_type = 'helper'
                elif re.match(r'^(pub\s+)?(priv\s+)?impl\s+', line.strip()):
                    block_type = 'helper'
                elif re.match(r'^(pub\s+)?(priv\s+)?let\s+', line.strip()):
                    block_type = 'helper'
            # Count braces (outside strings) to detect end of block
            if block_type in ('test', 'helper'):
                brace_count += count_braces_outside_strings(line)
                if brace_count == 0 and '{' in ''.join(current_block):
                    block_content = '\n'.join(current_block)
                    if block_type == 'test':
                        tests.append(block_content)
                    else:
                        helpers.append(block_content)
                    current_block = []
                    block_type = None

    # Don't forget the last block
    if current_block:
        block_content = '\n'.join(current_block)
        if block_type == 'test':
            tests.append(block_content)
        elif block_type == 'helper':
            helpers.append(block_content)

    return helpers, tests


def parse_test_blocks(content: str) -> list[str]:
    """Parse test blocks from file content (legacy interface).

    Each test block consists of:
    - An optional ///| doc comment line
    - The test declaration and body
    """
    _, tests = parse_content(content)
    return tests


def split_tests(blocks: list[str], pub_count: int) -> tuple[list[str], list[str]]:
    """Split test blocks into pub and priv lists."""
    return blocks[:pub_count], blocks[pub_count:]


def write_test_file(path: Path, blocks: list[str], helpers: list[str] | None = None):
    """Write test blocks to a file, optionally with helper functions.

    Args:
        path: Output file path
        blocks: List of test blocks
        helpers: Optional list of helper function blocks to include at the start
    """
    all_blocks = (helpers or []) + blocks
    content = '\n\n'.join(all_blocks) + '\n'
    path.write_text(content)
    helper_count = len(helpers) if helpers else 0
    if helper_count > 0:
        print(f"  Wrote {len(blocks)} tests + {helper_count} helpers to {path.name}")
    else:
        print(f"  Wrote {len(blocks)} tests to {path.name}")


def process_file(input_path: Path, category: str, spec_name: str):
    """Process a single test file, splitting into pub/priv variants.

    Args:
        input_path: Path to the original test file
        category: 'valid', 'invalid', 'wpt', 'wpt_setters', 'generated', etc.
        spec_name: Name of the spec (e.g., 'csv', 'yaml')
    """
    content = input_path.read_text()
    helpers, tests = parse_content(content)
    total = len(tests)

    print(f"Processing {input_path.name}: {total} tests, {len(helpers)} helpers")

    if total == 0:
        print(f"  No tests found, skipping")
        return

    # Calculate ~10% for pub, with special rule: if < 10 tests, all go to pub
    if total < 10:
        pub_count = total
    else:
        pub_count = max(1, round(total * 0.1))

    pub_blocks, priv_blocks = split_tests(tests, pub_count)

    # Determine output file names
    parent = input_path.parent
    if category:
        pub_name = f"{spec_name}_{category}_pub_test.mbt"
        priv_name = f"{spec_name}_{category}_priv_test.mbt"
    else:
        pub_name = f"{spec_name}_pub_test.mbt"
        priv_name = f"{spec_name}_priv_test.mbt"

    # Write pub file (without helpers - they go in priv file which shares the same test package)
    write_test_file(parent / pub_name, pub_blocks)

    # Write priv file only if there are priv tests (with helpers included)
    # If no priv file, put helpers in pub file instead
    if priv_blocks:
        write_test_file(parent / priv_name, priv_blocks, helpers)
    else:
        # All tests are pub, so include helpers in pub file
        if helpers:
            write_test_file(parent / pub_name, pub_blocks, helpers)
        print(f"  No priv file needed (all tests are pub)")

    # Remove original file (if different from output files)
    if input_path.name != pub_name and input_path.name != priv_name:
        input_path.unlink()
        print(f"  Deleted original {input_path.name}")


def process_file_direct(input_path: Path, output_prefix: str, category: str):
    """Process a single test file with custom output naming.

    Args:
        input_path: Path to the original test file
        output_prefix: Prefix for output files (e.g., 'wasm_smith_reference')
        category: 'valid', 'invalid', etc.
    """
    content = input_path.read_text()
    helpers, tests = parse_content(content)
    total = len(tests)

    print(f"Processing {input_path.name}: {total} tests, {len(helpers)} helpers")

    if total == 0:
        print(f"  No tests found, skipping")
        return

    # Calculate ~10% for pub, with special rule: if < 10 tests, all go to pub
    if total < 10:
        pub_count = total
    else:
        pub_count = max(1, round(total * 0.1))

    pub_blocks, priv_blocks = split_tests(tests, pub_count)

    # Determine output file names
    parent = input_path.parent
    pub_name = f"{output_prefix}_{category}_pub_test.mbt"
    priv_name = f"{output_prefix}_{category}_priv_test.mbt"

    # Write pub file (without helpers - they go in priv file which shares the same test package)
    write_test_file(parent / pub_name, pub_blocks)

    # Write priv file only if there are priv tests (with helpers included)
    # If no priv file, put helpers in pub file instead
    if priv_blocks:
        write_test_file(parent / priv_name, priv_blocks, helpers)
    else:
        # All tests are pub, so include helpers in pub file
        if helpers:
            write_test_file(parent / pub_name, pub_blocks, helpers)
        print(f"  No priv file needed (all tests are pub)")

    # Remove original file (if different from output files)
    if input_path.name != pub_name and input_path.name != priv_name:
        input_path.unlink()
        print(f"  Deleted original {input_path.name}")


def main():
    if len(sys.argv) < 2:
        print("Usage: split_tests.py <spec_name> [file_pattern ...]")
        print("       split_tests.py --file <path> <output_prefix> <category>")
        print("Example: split_tests.py csv")
        print("         split_tests.py yaml valid invalid generated")
        print("         split_tests.py --file wasm/wasm_smith_reference_valid_test.mbt wasm_smith_reference valid")
        sys.exit(1)

    # Handle --file mode for custom file paths
    if sys.argv[1] == "--file":
        if len(sys.argv) != 5:
            print("Usage: split_tests.py --file <path> <output_prefix> <category>")
            sys.exit(1)
        input_path = Path(sys.argv[2])
        output_prefix = sys.argv[3]
        category = sys.argv[4]
        if not input_path.exists():
            print(f"Error: {input_path} does not exist")
            sys.exit(1)
        process_file_direct(input_path, output_prefix, category)
        return

    spec_name = sys.argv[1]
    spec_dir = Path(spec_name)

    if not spec_dir.is_dir():
        print(f"Error: {spec_dir} is not a directory")
        sys.exit(1)

    # Default patterns: valid and invalid
    patterns = sys.argv[2:] if len(sys.argv) > 2 else ['valid', 'invalid']

    for pattern in patterns:
        # Handle special patterns like "wpt", "wpt_setters", "generated"
        if pattern in ['valid', 'invalid']:
            test_file = spec_dir / f"{spec_name}_{pattern}_test.mbt"
        else:
            test_file = spec_dir / f"{spec_name}_{pattern}_test.mbt"

        if test_file.exists():
            process_file(test_file, pattern, spec_name)
        else:
            print(f"Skipping {test_file}: file not found")


if __name__ == "__main__":
    main()
