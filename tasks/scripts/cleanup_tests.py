#!/usr/bin/env python3
"""
Consolidate test files in each spec-test directory into two files:
- <spec>_pub_test.mbt: all public tests (files NOT ending with _priv_test.mbt)
- <spec>_priv_test.mbt: all private tests (files ending with _priv_test.mbt)
"""

import argparse
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


def categorize_test_files(
    spec_dir: Path, spec_name: str
) -> tuple[list[Path], list[Path], Path | None, Path | None]:
    """
    Categorize test files into public and private.

    Returns:
        (public_files, private_files, existing_pub_target, existing_priv_target)
        - public_files: list of public test files (excluding target)
        - private_files: list of private test files (excluding target)
        - existing_pub_target: Path to existing target pub file, or None
        - existing_priv_target: Path to existing target priv file, or None
    """
    public_files = []
    private_files = []
    existing_pub_target = None
    existing_priv_target = None

    # Target file names (these are the consolidated output files)
    target_pub = f"{spec_name}_pub_test.mbt"
    target_priv = f"{spec_name}_priv_test.mbt"

    for entry in spec_dir.iterdir():
        if not entry.is_file():
            continue
        if not entry.name.endswith("_test.mbt"):
            continue

        # Track existing target files separately
        if entry.name == target_pub:
            existing_pub_target = entry
            continue
        if entry.name == target_priv:
            existing_priv_target = entry
            continue

        if entry.name.endswith("_priv_test.mbt"):
            private_files.append(entry)
        else:
            public_files.append(entry)

    # Sort for deterministic order
    public_files.sort(key=lambda p: p.name)
    private_files.sort(key=lambda p: p.name)

    return public_files, private_files, existing_pub_target, existing_priv_target


def consolidate_files(
    files: list[Path],
    output_path: Path,
    existing_target: Path | None,
    dry_run: bool,
) -> bool:
    """
    Consolidate multiple files into one.

    Args:
        files: list of files to consolidate (excluding existing target)
        output_path: path to write consolidated file
        existing_target: existing target file to include, or None
        dry_run: if True, only preview changes

    Returns:
        True if consolidation was performed, False otherwise
    """
    if not files and not existing_target:
        return False

    # If only the target exists and no other files, nothing to do
    if not files and existing_target:
        return False

    contents = []

    # Include existing target content first
    if existing_target:
        contents.append(existing_target.read_text())

    for f in files:
        content = f.read_text()
        contents.append(content)

    combined = "\n".join(contents)

    total_files = len(files) + (1 if existing_target else 0)

    if dry_run:
        print(f"  Would write: {output_path.name} ({total_files} files)")
        if existing_target:
            print(f"    <- {existing_target.name} (existing target)")
        for f in files:
            print(f"    <- {f.name}")
    else:
        output_path.write_text(combined)
        # Delete original files (not the target, it gets overwritten)
        for f in files:
            f.unlink()

    return True


def process_spec_directory(
    spec_dir: Path, dry_run: bool = False, verbose: bool = False
) -> bool:
    """
    Process a single spec directory.

    Returns:
        True if any changes were made, False otherwise
    """
    spec_name = spec_dir.name
    public_files, private_files, existing_pub, existing_priv = categorize_test_files(
        spec_dir, spec_name
    )

    if not public_files and not private_files:
        if verbose:
            print(f"[{spec_name}] No test files to consolidate")
        return False

    changes_made = False

    if public_files:
        output_pub = spec_dir / f"{spec_name}_pub_test.mbt"
        total = len(public_files) + (1 if existing_pub else 0)
        if consolidate_files(public_files, output_pub, existing_pub, dry_run):
            changes_made = True
            if not dry_run:
                print(f"[{spec_name}] Consolidated {total} public test files")

    if private_files:
        output_priv = spec_dir / f"{spec_name}_priv_test.mbt"
        total = len(private_files) + (1 if existing_priv else 0)
        if consolidate_files(private_files, output_priv, existing_priv, dry_run):
            changes_made = True
            if not dry_run:
                print(f"[{spec_name}] Consolidated {total} private test files")

    if not changes_made and verbose:
        print(f"[{spec_name}] Already consolidated")

    return changes_made


def main():
    parser = argparse.ArgumentParser(
        description="Consolidate test files in spec directories"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--spec",
        type=str,
        help="Process a single spec directory",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output",
    )
    args = parser.parse_args()

    # Find root directory (parent of scripts/)
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent

    if args.spec:
        # Process single spec
        spec_dir = root_dir / args.spec
        if not spec_dir.is_dir():
            print(f"Error: Spec directory not found: {args.spec}")
            return 1

        if args.dry_run:
            print(f"[DRY RUN] Processing: {args.spec}")
        process_spec_directory(spec_dir, args.dry_run, args.verbose)
    else:
        # Process all spec directories
        spec_dirs = find_spec_directories(root_dir)

        if args.dry_run:
            print("[DRY RUN] Preview of changes:")
            print()

        for spec_dir in spec_dirs:
            if args.dry_run:
                print(f"Directory: {spec_dir.name}/")
                public_files, private_files, existing_pub, existing_priv = (
                    categorize_test_files(spec_dir, spec_dir.name)
                )
                if public_files or private_files:
                    consolidate_files(
                        public_files,
                        spec_dir / f"{spec_dir.name}_pub_test.mbt",
                        existing_pub,
                        dry_run=True,
                    )
                    consolidate_files(
                        private_files,
                        spec_dir / f"{spec_dir.name}_priv_test.mbt",
                        existing_priv,
                        dry_run=True,
                    )
                else:
                    print("  Already consolidated or no test files")
                print()
            else:
                process_spec_directory(spec_dir, args.dry_run, args.verbose)

    return 0


if __name__ == "__main__":
    exit(main())
