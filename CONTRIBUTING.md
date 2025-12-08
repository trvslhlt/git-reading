# Contributing to git-reading

Thanks for your interest in contributing!

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/git-reading.git
cd git-reading
make dev-install

# Make your changes, then run checks
make format && make lint && make test

# Commit and push
git commit -m "feat: your feature description"
git push origin your-branch
```

## Prerequisites

- Python 3.10+
- Git
- [Make](https://www.gnu.org/software/make/)
- [uv](https://github.com/astral-sh/uv) package manager

## Development Setup

```bash
# Install all development dependencies
make dev-install

# Optional: Install pre-commit hooks for automatic formatting
uv run pre-commit install
```

### Optional Features

```bash
make streamlit-install  # For visualization features
make search-install     # For semantic search features
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
make format  # Auto-fixes formatting
make lint    # Check for issues
make test    # Run test suite
```

Or run all at once:

```bash
make format && make lint && make test
```

### 4. Commit and Push

Use [conventional commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:

```bash
git commit -m "feat: add vector search pre-filtering"
git commit -m "fix: correct author name parsing"
git commit -m "docs: update search examples"
```

Then push and open a pull request:

```bash
git push origin feature/your-feature-name
```

## Code Standards

### Testing
- Write tests for new features
- Maintain or improve coverage
- Tests should be fast and isolated
- Use pytest conventions

### Documentation
- Update README for user-facing changes
- Add docstrings to new functions/classes
- Include code examples when helpful

### Code Quality
- Ruff enforces formatting (Black-compatible, 100 char line length)
- Type hints preferred where appropriate
- No unused imports or undefined variables

## Architecture

The codebase follows an ETL pattern:
- `extract/` - Parse markdown files and extract structured data
- `normalize_source/` - Validate and normalize source data
- `query/` - Semantic search and querying
- `enrich/`, `transform/`, `load/` - Future pipeline stages (stubs)

## CI/CD

Pull requests automatically run:
1. Lint and format checks
2. Full test suite
3. Package build verification

PRs require:
- ✅ All CI checks passing
- ✅ Up-to-date with main branch
- ✅ Meaningful commit messages
- ✅ Tests for new features

## Getting Help

- **Documentation**: Check README and `docs/` directory
- **Issues**: Search existing issues or create a new one
- **Discussions**: Use GitHub Discussions for questions

## Release Process

(For maintainers)

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Commit: `git commit -m "chore: bump version to X.Y.Z"`
4. Tag: `git tag vX.Y.Z`
5. Push: `git push && git push --tags`
