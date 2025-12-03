.PHONY: help install test lint format clean run dev-install

help:
	@echo "Available commands:"
	@echo "  make install      - Install the package"
	@echo "  make dev-install  - Install dev dependencies"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linter"
	@echo "  make format       - Format code"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make run          - Run with current source code (no install needed)"
	@echo ""
	@echo "Usage examples:"
	@echo "  make run ARGS='--notes-dir /path/to/notes --output index.json'"
	@echo "  make run ARGS='--help'"

install:
	uv pip install .

dev-install:
	uv sync --extra dev --extra test
	uv pip install .

test:
	uv pip install .
	uv run pytest -v

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run with current source code without reinstalling
# Usage: make run ARGS="--notes-dir /path/to/notes"
run:
	PYTHONPATH=src uv run python -m extract.main $(ARGS)
