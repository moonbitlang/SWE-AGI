#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable


def copy_tree(
    src: Path,
    dst: Path,
    exclude_file: Callable[[Path], bool] = lambda _: False,
    exclude_dir: Callable[[Path], bool] = lambda _: False,
) -> None:
    for root, dirs, files in os.walk(src):
        rel_root = Path(root).relative_to(src)

        # Prune excluded directories so they are neither walked nor created.
        dirs[:] = [d for d in dirs if not exclude_dir(rel_root / d)]

        dest_root = dst / rel_root
        dest_root.mkdir(parents=True, exist_ok=True)
        for name in files:
            rel_path = rel_root / name
            if exclude_file(rel_path):
                continue
            src_path = Path(root) / name
            dst_path = dest_root / name
            shutil.copy2(src_path, dst_path)


def find_repo_root(start: Path) -> Path:
    cur = start
    while True:
        if (cur / "docker").is_dir() and (cur / "scripts").is_dir():
            return cur
        if (cur / "README.md").is_file() and (cur / "LICENSE").is_file():
            return cur
        if cur.parent == cur:
            return start
        cur = cur.parent


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    root_dir = find_repo_root(script_dir)

    print(f"Found repository root: {root_dir}")
    print(f"Script directory: {script_dir}")

    server_data = root_dir / script_dir.relative_to(root_dir) / "server_data"
    client_data = root_dir / script_dir.relative_to(root_dir) / "client_data"

    if server_data.exists() or client_data.exists():
        print(
            f"Error: {server_data} or {client_data} already exists. Please remove them first."
        )
        return 1

    server_data.mkdir(parents=True, exist_ok=True)
    client_data.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["git", "submodule", "update", "--init", "--recursive"],
        cwd=root_dir,
        check=True,
    )

    tasks_dir = root_dir / "tasks"
    if not tasks_dir.is_dir():
        print(f"Error: tasks directory not found at {tasks_dir}")
        return 1

    for agent_dir in (".codex", ".claude", ".gemini"):
        src_skills = root_dir / agent_dir / "skills" / "moonbit-agent-guide"
        if src_skills.is_dir():
            dst_skills = client_data / agent_dir / "skills" / "moonbit-agent-guide"
            copy_tree(src_skills, dst_skills)

    for spec_dir in tasks_dir.iterdir():
        task_file = spec_dir / "TASK.md"
        if not spec_dir.is_dir() or not task_file.is_file():
            continue

        spec_name = spec_dir.name
        server_spec = server_data / spec_name
        client_spec = client_data / spec_name
        server_spec.mkdir(parents=True, exist_ok=True)
        client_spec.mkdir(parents=True, exist_ok=True)

        copy_tree(
            spec_dir,
            server_spec,
            exclude_file=lambda p: p.name == "TASK.pub.md",
        )
        subprocess.run(["moon", "clean"], cwd=server_spec, check=False)

        # Exclude private tests and private fixture directories from client_data.
        # Note: `p` is a *relative path* (see copy_tree()).
        def exclude_client_file(p: Path) -> bool:
            return str(p.name).endswith("_priv_test.mbt") or p.name == "TASK.pub.md"

        def exclude_client_dir(p: Path) -> bool:
            # Exclude directories like `reference_priv_test/`, `fixtures_priv_test/`.
            return any(part.endswith("_priv_test") for part in p.parts)

        copy_tree(
            server_spec,
            client_spec,
            exclude_file=exclude_client_file,
            exclude_dir=exclude_client_dir,
        )
        subprocess.run(["moon", "clean"], cwd=client_spec, check=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
