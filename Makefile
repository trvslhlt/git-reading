# Git Reading - Makefile
# Index and query reading notes from markdown files using git history

.PHONY: help install test test-cov test-cov-report lint format clean \
	run-extract run-migrate run-validate run-fix run-learn-patterns \
	run-search-build run-search-query run-search-stats run-streamlit \
	dev-install streamlit-install search-install \
	streamlit search dev

#
# Help
#

help:
	@echo "Git Reading - Index and query reading notes"
	@echo ""
	@echo "Quick Start Workflows (auto-install dependencies):"
	@echo "  make streamlit    - Install Streamlit deps and launch visualization app"
	@echo "  make search       - Install search deps and build semantic search index"
	@echo "  make dev          - Install dev deps and run tests"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install             - Install the package and core dependencies"
	@echo "  make dev-install         - Install with dev dependencies (testing, linting)"
	@echo "  make streamlit-install   - Install with Streamlit visualization dependencies"
	@echo "  make search-install      - Install with semantic search dependencies"
	@echo ""
	@echo "Development Commands:"
	@echo "  make test                - Run all tests with pytest"
	@echo "  make test-cov            - Run tests with coverage report"
	@echo "  make test-cov-report     - Generate and open HTML coverage report"
	@echo "  make lint                - Check code with ruff linter"
	@echo "  make format              - Format code with ruff"
	@echo "  make clean               - Remove build artifacts and caches"
	@echo ""
	@echo "Data Pipeline Commands:"
	@echo "  make run-extract         - Extract reading notes from markdown files"
	@echo "  make run-migrate         - Migrate JSON index to SQLite database"
	@echo "  make run-validate        - Validate markdown files against rules"
	@echo "  make run-fix             - Interactively fix validation issues"
	@echo "  make run-learn-patterns  - Learn validation patterns from corpus"
	@echo ""
	@echo "Search Commands:"
	@echo "  make run-search-build    - Build semantic search vector index (requires: make search-install)"
	@echo "  make run-search-query    - Query the semantic search index (requires: make search-install)"
	@echo "  make run-search-stats    - Show search index statistics (requires: make search-install)"
	@echo ""
	@echo "Visualization:"
	@echo "  make run-streamlit       - Launch Streamlit app (requires: make streamlit-install)"
	@echo ""
	@echo "Common Workflows:"
	@echo "  # Extract notes (incremental) and build search index"
	@echo "  make run-extract ARGS='--notes-dir readings --index-dir index'"
	@echo "  make search              # Or use this to auto-install and build"
	@echo "  make run-search-query ARGS='\"meaning of life\"'"
	@echo ""
	@echo "  # Validate and fix notes"
	@echo "  make run-validate ARGS='--notes-dir readings --format json --output issues.json'"
	@echo "  make run-fix ARGS='--validation issues.json --notes-dir readings'"
	@echo ""
	@echo "  # Launch visualization"
	@echo "  make streamlit           # Auto-installs and launches"
	@echo ""
	@echo "Note: Commands that read/write files (run-extract, run-migrate, run-validate,"
	@echo "      run-learn-patterns) REQUIRE explicit ARGS to prevent accidents."
	@echo "      Individual run-* commands require manual dependency installation."
	@echo "      Use Quick Start Workflows above for automatic setup."
	@echo ""
	@echo "For detailed command options, run: make <command> ARGS='--help'"

#
# Installation
#

install:
	@echo "Installing git-reading package..."
	uv pip install .

dev-install:
	@echo "Installing with dev dependencies..."
	uv sync --extra dev --extra test
	uv pip install .

streamlit-install:
	@echo "Installing with Streamlit dependencies..."
	uv pip install -e ".[streamlit]"

search-install:
	@echo "Installing with semantic search dependencies..."
	uv pip install -e ".[search]"

#
# Quick Start Workflows (auto-install dependencies)
#

# Install Streamlit dependencies and launch visualization app
streamlit: streamlit-install
	@$(MAKE) run-streamlit

# Install search dependencies and build semantic search index
search: search-install
	@$(MAKE) run-search-build

# Install dev dependencies and run tests
dev: dev-install
	@$(MAKE) test

#
# Development
#

test:
	@echo "Running tests..."
	uv pip install .
	uv run pytest -v

test-cov:
	@echo "Running tests with coverage..."
	uv pip install .
	uv run pytest --cov --cov-report=term-missing --cov-report=html

test-cov-report:
	@echo "Opening coverage report..."
	@if [ ! -d "htmlcov" ]; then \
		echo "Coverage report not found. Run 'make test-cov' first."; \
		exit 1; \
	fi
	@if command -v open > /dev/null; then \
		open htmlcov/index.html; \
	elif command -v xdg-open > /dev/null; then \
		xdg-open htmlcov/index.html; \
	else \
		echo "Coverage report generated at htmlcov/index.html"; \
	fi

lint:
	@echo "Running linter..."
	uv run ruff check .

format:
	@echo "Formatting code..."
	uv run ruff format .
	uv run ruff check --fix .

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

#
# Data Pipeline
#

# Extract reading notes from markdown files (incremental by default)
# REQUIRES ARGS to prevent accidental file operations
# CLI requires: --notes-dir (required at CLI level)
# Usage: make run-extract ARGS='--notes-dir readings --index-dir index'
#        make run-extract ARGS='--notes-dir readings --index-dir index --full'
#        make run-extract ARGS='--help'
run-extract:
	@if [ -z "$(ARGS)" ]; then \
		echo "❌ Error: ARGS required to prevent accidental file operations"; \
		echo ""; \
		echo "Usage:"; \
		echo "  make run-extract ARGS='--notes-dir readings --index-dir index'"; \
		echo "  make run-extract ARGS='--notes-dir readings --index-dir index --full'"; \
		echo "  make run-extract ARGS='--help'"; \
		exit 1; \
	fi
	@echo "Extracting reading notes..."
	PYTHONPATH=src uv run extract readings $(ARGS)

# Migrate JSON index to SQLite database
# REQUIRES ARGS to prevent accidental file operations
# CLI requires: --index, --database (both required at CLI level)
# Usage: make run-migrate ARGS='--index book_index.json --database readings.db'
#        make run-migrate ARGS='--help'
run-migrate:
	@if [ -z "$(ARGS)" ]; then \
		echo "❌ Error: ARGS required to prevent accidental file operations"; \
		echo ""; \
		echo "Usage:"; \
		echo "  make run-migrate ARGS='--index book_index.json --database readings.db'"; \
		echo "  make run-migrate ARGS='--help'"; \
		exit 1; \
	fi
	@echo "Migrating to database..."
	PYTHONPATH=src uv run load-db migrate $(ARGS)

# Validate markdown files against normalization rules
# REQUIRES ARGS to prevent accidental file operations
# CLI requires: --notes-dir (required at CLI level)
# Usage: make run-validate ARGS='--notes-dir readings'
#        make run-validate ARGS='--notes-dir readings --format json --output issues.json'
#        make run-validate ARGS='--help'
run-validate:
	@if [ -z "$(ARGS)" ]; then \
		echo "❌ Error: ARGS required to prevent accidental file operations"; \
		echo ""; \
		echo "Usage:"; \
		echo "  make run-validate ARGS='--notes-dir readings'"; \
		echo "  make run-validate ARGS='--notes-dir readings --format json --output issues.json'"; \
		echo "  make run-validate ARGS='--help'"; \
		exit 1; \
	fi
	@echo "Validating markdown files..."
	PYTHONPATH=src uv run normalize validate $(ARGS)

# Interactively apply fixes from validation JSON
# CLI requires: --validation, --notes-dir (both required at CLI level)
# Usage: make run-fix ARGS='--validation issues.json --notes-dir readings'
#        make run-fix ARGS='--validation issues.json --notes-dir readings -y'  # Auto-apply
#        make run-fix ARGS='--help'
run-fix:
	@echo "Applying fixes..."
	PYTHONPATH=src uv run normalize fix $(ARGS)

# Learn validation patterns from markdown corpus
# REQUIRES ARGS to prevent accidental file operations
# CLI requires: --notes-dir (required at CLI level)
# Usage: make run-learn-patterns ARGS='--notes-dir readings --output patterns.json'
#        make run-learn-patterns ARGS='--help'
run-learn-patterns:
	@if [ -z "$(ARGS)" ]; then \
		echo "❌ Error: ARGS required to prevent accidental file operations"; \
		echo ""; \
		echo "Usage:"; \
		echo "  make run-learn-patterns ARGS='--notes-dir readings --output patterns.json'"; \
		echo "  make run-learn-patterns ARGS='--help'"; \
		exit 1; \
	fi
	@echo "Learning patterns..."
	PYTHONPATH=src uv run python -m normalize_source.main learn $(ARGS)

#
# Semantic Search
#

# Build semantic search vector index from JSON index
# Requires: make search-install (or use: make search)
# Default: reads from 'book_index.json', writes to '.faiss/' directory
# Usage: make run-search-build
#        make run-search-build ARGS='--index custom_index.json'
#        make run-search-build ARGS='--help'
run-search-build:
	@echo "Building search index..."
	PYTHONPATH=src uv run search build $(ARGS)

# Query the semantic search index
# Requires: make search-install
# Usage: make run-search-query ARGS='"meaning of life"'
#        make run-search-query ARGS='"philosophy" --top-k 10'
#        make run-search-query ARGS='--help'
run-search-query:
	@echo "Querying search index..."
	PYTHONPATH=src uv run search query $(ARGS)

# Show search index statistics
# Requires: make search-install
# Usage: make run-search-stats
#        make run-search-stats ARGS='--help'
run-search-stats:
	@echo "Search index statistics:"
	PYTHONPATH=src uv run search stats $(ARGS)

#
# Visualization
#

# Launch Streamlit visualization app
# Requires: make streamlit-install (or use: make streamlit)
# Opens in browser at http://localhost:8501
# Usage: make run-streamlit
run-streamlit:
	@echo "Launching Streamlit app at http://localhost:8501..."
	uv run streamlit run streamlit_app/app.py
