.PHONY: help install test lint format clean run run-extract run-query run-transform dev-install

help:
	@echo "Available commands:"
	@echo "  make install          - Install the package"
	@echo "  make dev-install      - Install dev dependencies"
	@echo "  make test             - Run tests"
	@echo "  make lint             - Run linter"
	@echo "  make format           - Format code"
	@echo "  make clean            - Clean build artifacts"
	@echo ""
	@echo "Run commands (use current source code, no install needed):"
	@echo "  make run              - Show available run commands"
	@echo "  make run-extract      - Run extract-readings command"
	@echo "  make run-query        - Run query command (when implemented)"
	@echo "  make run-transform    - Run transform command (when implemented)"
	@echo ""
	@echo "Usage examples:"
	@echo "  make run-extract ARGS='--notes-dir /path/to/notes --output index.json'"
	@echo "  make run-extract ARGS='--help'"

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

# Run commands with current source code without reinstalling
# These use PYTHONPATH=src to run code directly from source

# Extract command - index reading notes
run-extract:
	PYTHONPATH=src uv run extract-readings $(ARGS)

# Query command (placeholder for future implementation)
run-query:
	@echo "Query command not yet implemented"
	@echo "When ready, will run: PYTHONPATH=src uv run query-readings $(ARGS)"

# Transform command (placeholder for future implementation)
run-transform:
	@echo "Transform command not yet implemented"
	@echo "When ready, will run: PYTHONPATH=src uv run transform-readings $(ARGS)"

# Show available run commands when 'make run' is called without a specific target
run:
	@echo "Available run commands:"
	@echo ""
	@echo "  make run-extract ARGS='...'    - Run extract-readings command"
	@echo "  make run-query ARGS='...'      - Run query command (not yet implemented)"
	@echo "  make run-transform ARGS='...'  - Run transform command (not yet implemented)"
	@echo ""
	@echo "Examples:"
	@echo "  make run-extract ARGS='--notes-dir /path/to/notes --output index.json'"
	@echo "  make run-extract ARGS='--help'"
	@echo ""
	@echo "Tip: These commands run your current source code without reinstalling."
