#!/usr/bin/env python3
"""Build the SWE-AGI leaderboard static website."""

import json
import pathlib
import shutil
import time
from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = pathlib.Path(__file__).parent
TEMPLATES = ROOT / "templates"
DIST = ROOT / "dist"


def get_pages():
    """Discover all page templates."""
    pages = {}
    pages_dir = TEMPLATES / "pages"
    for file in pages_dir.glob("*.html"):
        template_path = f"pages/{file.name}"
        output_file = file.name
        pages[template_path] = output_file
    return pages


def format_duration(ms):
    """Convert milliseconds to human-readable duration."""
    if ms is None:
        return "N/A"
    hours = ms / (1000 * 60 * 60)
    if hours < 1:
        return f"{hours:.2f}h"
    return f"{hours:.1f}h"


def format_cost(cost_usd):
    """Format cost in USD."""
    if cost_usd is None:
        return "N/A"
    if not isinstance(cost_usd, (int, float)):
        return "N/A"
    return f"${cost_usd:.2f}"


def format_tokens(tokens):
    """Format token count with K/M suffix."""
    if tokens is None:
        return "N/A"
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.2f}M"
    if tokens >= 1_000:
        return f"{tokens / 1_000:.1f}K"
    return str(tokens)


def main() -> None:
    # Set up Jinja environment
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html"])
    )

    # Add custom filters
    env.filters["format_duration"] = format_duration
    env.filters["format_cost"] = format_cost
    env.filters["format_tokens"] = format_tokens

    # Start fresh each run
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    # Copy static assets
    if (ROOT / "css").exists():
        shutil.copytree(ROOT / "css", DIST / "css")
    if (ROOT / "img").exists():
        shutil.copytree(ROOT / "img", DIST / "img")
    if (ROOT / "js").exists():
        shutil.copytree(ROOT / "js", DIST / "js")

    # Copy favicon if exists
    if (ROOT / "img" / "favicon.ico").exists():
        shutil.copy(ROOT / "img" / "favicon.ico", DIST / "favicon.ico")

    # Load data
    data_file = ROOT / "data" / "leaderboards.json"
    if not data_file.exists():
        print(f"Error: {data_file} not found. Run 'make extract' first.")
        return

    with open(data_file, "r") as f:
        leaderboards = json.load(f)

    # Get pages
    pages = get_pages()

    # Render all pages
    asset_version = int(time.time())
    for tpl_name, out_name in pages.items():
        tpl = env.get_template(tpl_name)
        html = tpl.render(
            title="SWE-AGI",
            base_path="",
            asset_version=asset_version,
            leaderboards=leaderboards,
            models=leaderboards.get("models", []),
            tasks=leaderboards.get("tasks", []),
            results=leaderboards.get("results", []),
            summaries=leaderboards.get("summaries", {}),
            metadata=leaderboards.get("metadata", {}),
        )
        (DIST / out_name).write_text(html)
        print(f"Built: {out_name}")

    # Copy leaderboards.json to dist for JS access
    (DIST / "data").mkdir(exist_ok=True)
    shutil.copy(data_file, DIST / "data" / "leaderboards.json")

    print("All pages generated successfully!")


if __name__ == "__main__":
    main()
