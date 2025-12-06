# CI/CD Setup Guide

This guide explains how to set up automated checks for your pull requests.

## What's Included

The project includes:

1. **GitHub Actions CI** - Automated checks on every PR
2. **Pre-commit hooks** - Local checks before committing
3. **Makefile targets** - Manual check commands

## GitHub Actions (Automatic)

### What It Does

On every pull request and push to main, GitHub Actions automatically:

1. ✅ Checks code formatting (`ruff format --check`)
2. ✅ Runs linting (`ruff check`)
3. ✅ Runs all tests (`pytest`)
4. ✅ Verifies package builds

### Setup

1. **Push the `.github/workflows/ci.yml` file to your repository**

   ```bash
   git add .github/
   git commit -m "ci: add GitHub Actions workflow"
   git push
   ```

2. **View workflow runs**

   Go to your repository on GitHub → **Actions** tab

3. **Add status badge to README (optional)**

   Add to the top of `README.md`:

   ```markdown
   [![CI](https://github.com/YOUR_USERNAME/git-reading/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/git-reading/actions/workflows/ci.yml)
   ```

### Branch Protection (Recommended)

Require checks to pass before merging:

1. Go to **Settings** → **Branches**
2. Click **Add rule**
3. Branch name pattern: `main`
4. Enable:
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass before merging
     - Select all CI jobs
   - ✅ Require branches to be up to date

Now PRs can't be merged unless all checks pass!

## Pre-commit Hooks (Local)

### What It Does

Before you commit, automatically:

1. Formats code with ruff
2. Fixes linting issues
3. Checks for common problems
4. Prevents committing large files

### Setup

```bash
# Install pre-commit (included in dev dependencies)
make dev-install

# Install the git hooks
uv run pre-commit install

# Test it (optional)
uv run pre-commit run --all-files
```

### Usage

Now when you `git commit`, pre-commit automatically runs checks:

```bash
git add src/query/search.py
git commit -m "feat: add new search feature"

# Pre-commit runs automatically:
# - Formats your code
# - Fixes linting issues
# - Checks for problems

# If changes were made, you'll need to add and commit again:
git add src/query/search.py
git commit -m "feat: add new search feature"
```

### Skip Hooks (When Needed)

Sometimes you need to commit without running hooks:

```bash
git commit --no-verify -m "wip: work in progress"
```

**Use sparingly!** CI will still catch issues.

## Manual Checks (Makefile)

Run the same checks locally before pushing:

```bash
# Check formatting (and fix)
make format

# Run linting
make lint

# Run tests
make test

# Run all checks
make format && make lint && make test
```

## Workflow Comparison

| Check | Pre-commit | Makefile | GitHub Actions |
|-------|-----------|----------|----------------|
| **When** | Before commit | Manual | On PR/push |
| **Speed** | Fast | Fast | Slower (CI server) |
| **Automatic** | Yes | No | Yes |
| **Can skip** | Yes (`--no-verify`) | Yes | No |
| **Blocks merge** | No | No | Yes (with branch protection) |

**Recommended workflow:**

1. **Pre-commit** - Catches issues early, auto-fixes
2. **Makefile** - Manual checks when needed
3. **GitHub Actions** - Final gatekeeper before merge

## Troubleshooting

### Pre-commit hook fails

```bash
# See what failed
git commit -m "message"

# Fix manually
make format
make lint

# Try again
git commit -m "message"
```

### Skip a specific hook

Edit `.pre-commit-config.yaml` and comment out the hook.

### Update pre-commit hooks

```bash
uv run pre-commit autoupdate
```

### CI fails but passes locally

1. Check you've committed all files
2. Ensure dependencies in `pyproject.toml` are correct
3. Check CI logs for specific errors
4. Try running in a clean environment:

   ```bash
   # Create fresh virtual environment
   rm -rf .venv
   uv sync --extra dev --extra test
   make test
   ```

## Advanced Configuration

### Run tests in pre-commit

Uncomment in `.pre-commit-config.yaml`:

```yaml
- id: pytest
  name: Run pytest
  entry: uv run pytest
  language: system
  pass_filenames: false
  always_run: true
```

**Warning:** This will slow down commits significantly.

### Add type checking

Install mypy and add to `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.8.0
  hooks:
    - id: mypy
      additional_dependencies: [types-all]
```

### Only run CI on certain paths

Edit `.github/workflows/ci.yml`:

```yaml
on:
  pull_request:
    branches: [main]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
```

### Matrix testing (multiple Python versions)

Edit `.github/workflows/ci.yml`:

```yaml
test:
  strategy:
    matrix:
      python-version: ["3.10", "3.11", "3.12"]
  steps:
    - run: uv python install ${{ matrix.python-version }}
```

## Best Practices

1. **Always run checks before pushing**
   ```bash
   make format && make lint && make test && git push
   ```

2. **Fix issues locally, not in CI**
   - Faster iteration
   - Less noise in CI logs
   - Better commit history

3. **Use descriptive commit messages**
   - Pre-commit will auto-fix formatting
   - Focus on what changed and why

4. **Keep CI fast**
   - Run heavy tests only on main branch
   - Use caching for dependencies
   - Parallelize jobs when possible

5. **Review CI failures carefully**
   - Don't bypass CI just to merge faster
   - Understand what broke and why
   - Fix the root cause, not just the symptom

## Resources

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Pre-commit Docs](https://pre-commit.com/)
- [Ruff Docs](https://docs.astral.sh/ruff/)
- [pytest Docs](https://docs.pytest.org/)
