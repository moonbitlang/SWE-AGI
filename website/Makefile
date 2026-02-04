.PHONY: install build serve clean extract dev

# Create virtual environment and install dependencies
install:
	uv venv
	uv pip install jinja2

# Extract data from SWE-AGI-Eval
extract:
	uv run extract_data.py

# Build the static site
build: extract
	uv run build.py

# Serve locally for development
serve:
	cd dist && uv run python -m http.server 8000

# Clean generated files
clean:
	rm -rf dist
	rm -f data/leaderboards.json

# Development: extract, build, and serve
dev: build serve
