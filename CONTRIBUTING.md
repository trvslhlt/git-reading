# Contributing to git-reading

Thanks for your interest in contributing! This document provides guidelines and setup instructions.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/git-reading.git
cd git-reading

# Install development dependencies
make dev-install

# Install pre-commit hooks
uv run pre-commit install

# Make your changes
# ...

# Run checks locally
make format
make lint
make test

# Commit and push
git add .
git commit -m "feat: your feature description"
git push origin your-branch

# Open a pull request
```

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- Git

### Installation

```bash
# Install all development dependencies
make dev-install

# Or manually:
uv sync --extra dev --extra test
uv pip install .
```

### Optional Dependencies

```bash
# For visualization features
make streamlit-install

# For semantic search features
make search-install
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow the project structure:

- `src/extract/` - Data extraction from markdown
- `src/normalize_source/` - Validation and normalization
- `src/query/` - Search and query functionality
- `tests/` - Test files

### 3. Run Checks

```bash
# Format code (auto-fixes issues)
make format

# Check linting
make lint

# Run tests
make test
```

Or run all at once:

```bash
make format && make lint && make test
```

### 4. Commit Changes

With pre-commit hooks installed, formatting happens automatically:

```bash
git add .
git commit -m "type: description"

# Pre-commit will auto-format and fix issues
# If changes were made, add and commit again:
git add .
git commit -m "type: description"
```

### Commit Message Format

Use conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:

```bash
git commit -m "feat: add vector search pre-filtering"
git commit -m "fix: correct author name parsing"
git commit -m "docs: update README with search examples"
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then open a pull request on GitHub.

## Code Quality Standards

### Formatting

- Use [Ruff](https://docs.astral.sh/ruff/) for formatting
- Line length: 100 characters
- Follow Black-compatible style

### Linting

- No unused imports
- No undefined variables
- Follow Python style guide (PEP 8)
- Use type hints where appropriate

### Testing

- Write tests for new features
- Maintain or improve code coverage
- Tests should be fast and isolated
- Use pytest for testing

### Documentation

- Update README for user-facing changes
- Add docstrings to new functions/classes
- Update CHANGELOG for notable changes
- Include code examples when helpful

## Project Structure

```
git-reading/
├── src/
│   ├── extract/            # Extract data from markdown
│   ├── normalize_source/   # Validate and normalize
│   ├── query/              # Search functionality
│   ├── enrich/             # Data enrichment (stub)
│   ├── transform/          # Data transformation (stub)
│   └── load/               # Data loading (stub)
├── tests/                  # Test files
├── streamlit_app/          # Visualization dashboard
├── examples/               # Usage examples
├── docs/                   # Additional documentation
└── .github/workflows/      # CI/CD pipelines
```

## Running Tests

```bash
# Run all tests
make test

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_integration.py

# Run specific test
uv run pytest tests/test_integration.py::test_basic_indexing
```

## CI/CD

### GitHub Actions

Every pull request runs:

1. **Lint and Format Check** - Ensures code is properly formatted
2. **Tests** - Runs the full test suite
3. **Build** - Verifies package builds correctly

See [docs/CI_SETUP.md](docs/CI_SETUP.md) for details.

### Pre-commit Hooks

Automatically run before each commit:

- Format code with ruff
- Fix linting issues
- Check for common problems
- Prevent committing large files

Install with:

```bash
uv run pre-commit install
```

## Adding New Features

### Example: Adding a New Search Filter

1. **Update data model** (`src/query/vector_store.py`)
2. **Add lookup table** (in `VectorStore.__init__` and `add()`)
3. **Update search method** (add filter parameter)
4. **Update CLI** (`src/query/cli.py`)
5. **Add tests** (`tests/`)
6. **Update documentation** (README, docs/SEMANTIC_SEARCH.md)
7. **Run checks** (`make format && make lint && make test`)
8. **Commit and PR**

### Example: Adding a New Validation Rule

1. **Create rule class** (`src/normalize_source/rules/`)
2. **Add to validator** (`src/normalize_source/validator.py`)
3. **Add tests** (`tests/`)
4. **Update constants** if needed (`src/normalize_source/constants.py`)
5. **Run checks** and commit

## Getting Help

- **Documentation**: Check README and docs/ directory
- **Issues**: Search existing issues or create a new one
- **Discussions**: Use GitHub Discussions for questions

## Code Review Process

PRs require:

1. ✅ All CI checks passing
2. ✅ Code review approval (if branch protection enabled)
3. ✅ Up-to-date with main branch
4. ✅ Meaningful commit messages
5. ✅ Tests for new features

## Release Process

(For maintainers)

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Commit: `git commit -m "chore: bump version to X.Y.Z"`
4. Tag: `git tag vX.Y.Z`
5. Push: `git push && git push --tags`
6. GitHub Actions will build and publish (if configured)

## Questions?

Open an issue or start a discussion on GitHub!
