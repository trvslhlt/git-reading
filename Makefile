# Git Reading - Makefile
# Index and query reading notes from markdown files using git history

.PHONY: help install test lint format clean \
	run-extract run-migrate run-validate run-fix run-learn-patterns \
	run-search-build run-search-query run-search-stats run-streamlit \
	dev-install streamlit-install search-install

#
# Help
#

help:
	@echo "Git Reading - Index and query reading notes"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install             - Install the package and core dependencies"
	@echo "  make dev-install         - Install with dev dependencies (testing, linting)"
	@echo "  make streamlit-install   - Install with Streamlit visualization dependencies"
	@echo "  make search-install      - Install with semantic search dependencies"
	@echo ""
	@echo "Development Commands:"
	@echo "  make test                - Run all tests with pytest"
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
	@echo "  make run-search-build    - Build semantic search vector index"
	@echo "  make run-search-query    - Query the semantic search index"
	@echo "  make run-search-stats    - Show search index statistics"
	@echo ""
	@echo "Visualization:"
	@echo "  make run-streamlit       - Launch Streamlit visualization app"
	@echo ""
	@echo "Common Workflows:"
	@echo "  # Extract notes and build search index"
	@echo "  make run-extract"
	@echo "  make run-search-build"
	@echo "  make run-search-query ARGS='\"meaning of life\"'"
	@echo ""
	@echo "  # Validate and fix notes"
	@echo "  make run-validate ARGS='--notes-dir readings --format json --output issues.json'"
	@echo "  make run-fix ARGS='--validation issues.json --notes-dir readings'"
	@echo ""
	@echo "  # Migrate to database"
	@echo "  make run-migrate ARGS='book_index.json readings.db'"
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
# Development
#

test:
	@echo "Running tests..."
	uv pip install .
	uv run pytest -v

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
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

#
# Data Pipeline
#

# Extract reading notes from markdown files into JSON index
# Default: reads from 'readings/' directory, writes to 'book_index.json'
# Usage: make run-extract
#        make run-extract ARGS='--notes-dir /path/to/notes --output index.json'
#        make run-extract ARGS='--help'
run-extract:
	@echo "Extracting reading notes..."
	PYTHONPATH=src uv run extract readings $(ARGS)

# Migrate JSON index to SQLite database
# Usage: make run-migrate ARGS='input.json output.db'
#        make run-migrate ARGS='--help'
run-migrate:
	@echo "Migrating to database..."
	PYTHONPATH=src uv run load-db migrate $(ARGS)

# Validate markdown files against normalization rules
# Usage: make run-validate ARGS='--notes-dir readings'
#        make run-validate ARGS='--notes-dir readings --format json --output issues.json'
#        make run-validate ARGS='--help'
run-validate:
	@echo "Validating markdown files..."
	PYTHONPATH=src uv run normalize validate $(ARGS)

# Interactively apply fixes from validation JSON
# Usage: make run-fix ARGS='--validation issues.json --notes-dir readings'
#        make run-fix ARGS='--validation issues.json --notes-dir readings -y'  # Auto-apply
#        make run-fix ARGS='--help'
run-fix:
	@echo "Applying fixes..."
	PYTHONPATH=src uv run normalize fix $(ARGS)

# Learn validation patterns from markdown corpus
# Usage: make run-learn-patterns ARGS='--notes-dir readings --output patterns.json'
#        make run-learn-patterns ARGS='--help'
run-learn-patterns:
	@echo "Learning patterns..."
	PYTHONPATH=src uv run python -m normalize_source.main learn $(ARGS)

#
# Semantic Search
#

# Build semantic search vector index from JSON index
# Default: reads from 'book_index.json', writes to '.faiss/' directory
# Usage: make run-search-build
#        make run-search-build ARGS='--index custom_index.json'
#        make run-search-build ARGS='--help'
run-search-build:
	@echo "Building search index..."
	PYTHONPATH=src uv run search build $(ARGS)

# Query the semantic search index
# Usage: make run-search-query ARGS='"meaning of life"'
#        make run-search-query ARGS='"philosophy" --top-k 10'
#        make run-search-query ARGS='--help'
run-search-query:
	@echo "Querying search index..."
	PYTHONPATH=src uv run search query $(ARGS)

# Show search index statistics
# Usage: make run-search-stats
#        make run-search-stats ARGS='--help'
run-search-stats:
	@echo "Search index statistics:"
	PYTHONPATH=src uv run search stats $(ARGS)

#
# Visualization
#

# Launch Streamlit visualization app
# Opens in browser at http://localhost:8501
# Usage: make run-streamlit
run-streamlit:
	@echo "Launching Streamlit app at http://localhost:8501..."
	uv run streamlit run streamlit_app/app.py
