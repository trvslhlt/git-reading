# Code Coverage

## Overview

This project uses [pytest-cov](https://pytest-cov.readthedocs.io/) for test coverage tracking. Coverage is informational and helps identify untested code paths.

## Running Coverage

```bash
# Run tests with coverage report in terminal
make test-cov

# Generate and open HTML coverage report
make test-cov-report
```

## Coverage Targets

### High Priority (aim for 90%+)
- `src/extract/main.py` - Core parsing logic
- `src/normalize_source/rules/*.py` - Validation rules
- `src/load/db_utils.py` - Database operations
- `src/query/vector_store.py` - Search functionality

### Medium Priority (aim for 70-80%)
- CLI modules (`*/cli.py`) - Main code paths
- `src/normalize_source/validator.py` - Orchestration
- `src/query/embeddings.py` - Model wrapper

### Lower Priority (50-60% or skip)
- `streamlit_app/` - Manual UI testing is sufficient
- Stub modules (`enrich/`, `transform/`) - Coverage when implemented
- Simple data classes and constants

## Configuration

Coverage settings are in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/__init__.py",
    "*/streamlit_app/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
    # ... more exclusions
]
```

## Current Status

As of the last run:
- **Overall Coverage**: 43.3%
- **Validation Rules**: 100% (excellent!)
- **Database Utils**: 100% (excellent!)
- **Core Extraction**: 88.1% (good)
- **Search/Query**: 0% (needs tests)
- **CLI Modules**: 0-40% (expected, focus on logic not arg parsing)

## Guidelines

- **Don't chase 100%**: Diminishing returns on trivial code
- **Test behavior, not lines**: Focus on important code paths
- **Use `# pragma: no cover`**: For truly untestable code (defensive assertions, debug code)
- **Update this doc**: When coverage targets change

## CI Integration

Coverage runs automatically with every PR and push to main:
- Generates terminal output in the CI logs
- Creates `coverage.xml` for potential upload to coverage services
- **Informational only** - no enforcement thresholds or blocking

### Optional: Codecov Integration

To enable Codecov uploads:
1. Sign up at [codecov.io](https://codecov.io) and connect your repository
2. In `.github/workflows/ci.yml`, change `if: false` to `if: true` in the Codecov upload step
3. Add `CODECOV_TOKEN` to your repository secrets (if private repo)

This gives you PR comments with coverage diffs and trend tracking. **Not required** - local `make test-cov` is sufficient for most workflows.
