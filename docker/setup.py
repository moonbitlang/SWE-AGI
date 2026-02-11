#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin
from urllib.request import urlopen

SATLIB_BENCHMARK_PAGE = "https://www.cs.ubc.ca/~hoos/SATLIB/benchm.html"
SATLIB_TIMEOUT_SECONDS = 60

# SATLIB archive filename -> (target directory under dimacs, expected cnf count)
CDCL_DIMACS_ARCHIVES = {
    "bmc.tar.gz": ("bmc", 13),
    "flat50-115.tar.gz": ("flat50v115e", 999),
    "flat100-239.tar.gz": ("flat100v239e", 100),
    "flat200-479.tar.gz": ("flat200v479e", 100),
    "uf20-91.tar.gz": ("uf20v91c", 1000),
    "uf50-218.tar.gz": ("uf50v218c", 1000),
    "uuf50-218.tar.gz": ("uuf50v218c", 1000),
    "uf250-1065.tar.gz": ("uf250v1065c", 100),
}


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


def _find_satlib_dimacs_links() -> dict[str, str]:
    with urlopen(SATLIB_BENCHMARK_PAGE, timeout=SATLIB_TIMEOUT_SECONDS) as resp:
        html = resp.read().decode("utf-8", "replace")

    hrefs = re.findall(r"HREF\s*=\s*[\"']?([^\"'\s>]+)", html, flags=re.IGNORECASE)
    links: dict[str, str] = {}
    for href in hrefs:
        filename = Path(href).name
        if filename not in CDCL_DIMACS_ARCHIVES:
            continue
        links[filename] = urljoin(SATLIB_BENCHMARK_PAGE, href)

    missing = sorted(set(CDCL_DIMACS_ARCHIVES) - set(links))
    if missing:
        raise RuntimeError(
            "Could not find required SATLIB links on benchm.html: " + ", ".join(missing)
        )

    return links


def _download_file(url: str, dst: Path) -> None:
    with urlopen(url, timeout=SATLIB_TIMEOUT_SECONDS) as resp, dst.open("wb") as out:
        shutil.copyfileobj(resp, out)


def _extract_cnf_files_flat(archive_path: Path, dst_dir: Path) -> int:
    dst_dir.mkdir(parents=True, exist_ok=True)
    for old in dst_dir.glob("*.cnf"):
        old.unlink()

    extracted_names: set[str] = set()
    with tarfile.open(archive_path, mode="r:*") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            name = Path(member.name).name
            if not name.endswith(".cnf"):
                continue
            if name in extracted_names:
                raise RuntimeError(f"Duplicate CNF filename in archive: {name}")
            src = tar.extractfile(member)
            if src is None:
                raise RuntimeError(f"Could not extract member: {member.name}")
            with (dst_dir / name).open("wb") as out:
                shutil.copyfileobj(src, out)
            extracted_names.add(name)
    return len(extracted_names)


def download_cdcl_dimacs(dimacs_dir: Path) -> None:
    print(f"Downloading SATLIB DIMACS benchmarks into {dimacs_dir}")
    dimacs_dir.mkdir(parents=True, exist_ok=True)

    links = _find_satlib_dimacs_links()
    with tempfile.TemporaryDirectory(prefix="satlib-dimacs-") as tmp:
        tmp_dir = Path(tmp)
        for archive_name, (
            target_dir_name,
            expected_count,
        ) in CDCL_DIMACS_ARCHIVES.items():
            url = links[archive_name]
            archive_path = tmp_dir / archive_name

            print(f"  - fetching {archive_name} from {url}")
            _download_file(url, archive_path)

            target_dir = dimacs_dir / target_dir_name
            actual_count = _extract_cnf_files_flat(archive_path, target_dir)
            if actual_count != expected_count:
                raise RuntimeError(
                    f"Unexpected CNF count for {archive_name}: expected "
                    f"{expected_count}, got {actual_count}"
                )


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

        def exclude_server_dir(p: Path) -> bool:
            # Populate cdcl/dimacs from SATLIB in setup (instead of copying local files).
            return spec_name == "cdcl" and p.parts and p.parts[0] == "dimacs"

        copy_tree(
            spec_dir,
            server_spec,
            exclude_file=lambda p: p.name == "TASK.pub.md",
            exclude_dir=exclude_server_dir,
        )
        subprocess.run(["moon", "clean"], cwd=server_spec, check=False)

        if spec_name == "cdcl":
            download_cdcl_dimacs(server_spec / "dimacs")

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
