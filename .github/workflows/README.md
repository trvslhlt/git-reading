# GitHub Actions CI/CD

This directory contains GitHub Actions workflows for automated testing and quality checks.

## Workflows

### CI (`ci.yml`)

Runs on every pull request and push to main/master branch.

**Jobs:**

1. **Lint and Format Check**
   - Checks code formatting with `ruff format --check`
   - Runs linting with `ruff check`
   - Fails if code is not properly formatted or has linting errors

2. **Test**
   - Runs the full test suite with `pytest`
   - Includes git history for git blame tests

3. **Build**
   - Verifies the package builds correctly
   - Checks package contents

## Setup

### 1. Enable GitHub Actions

GitHub Actions should be enabled by default for your repository. If not:

1. Go to your repository settings
2. Navigate to "Actions" → "General"
3. Ensure "Allow all actions and reusable workflows" is selected

### 2. Add Status Badge to README (Optional)

Add this to the top of your `README.md`:

```markdown
[![CI](https://github.com/trvslhlt/git-reading/actions/workflows/ci.yml/badge.svg)](https://github.com/trvslhlt/git-reading/actions/workflows/ci.yml)
```

Replace `trvslhlt/git-reading` with your actual GitHub username/repo.

### 3. Branch Protection Rules (Recommended)

Protect your main branch to require checks to pass before merging:

1. Go to **Settings** → **Branches** → **Branch protection rules**
2. Click **Add rule**
3. Branch name pattern: `main` (or `master`)
4. Enable:
   - ✅ **Require a pull request before merging**
   - ✅ **Require status checks to pass before merging**
     - Select: `Lint and Format Check`, `Run Tests`, `Build Package`
   - ✅ **Require branches to be up to date before merging**
   - ✅ **Do not allow bypassing the above settings**

### 4. Auto-fix on PR (Optional)

To automatically fix formatting issues, add this workflow:

**`.github/workflows/auto-fix.yml`:**

```yaml
name: Auto-fix

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: write
  pull-requests: write

jobs:
  auto-fix:
    name: Auto-fix formatting
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.head_ref }}

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Set up Python
        run: uv python install 3.10

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Auto-fix with ruff
        run: |
          uv run ruff format .
          uv run ruff check --fix .

      - name: Commit changes
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "style: auto-fix formatting and linting"
```

## Local Development

Before pushing, run the same checks locally:

```bash
# Check formatting
make format

# Run linting
make lint

# Run tests
make test
```

Or run all at once:

```bash
# Format, lint, and test
make format && make lint && make test
```

## Troubleshooting

### "uv: command not found"

The workflow installs `uv` automatically. If you see this error, the `setup-uv` action may need updating.

### Tests fail on GitHub but pass locally

- Ensure you've committed all necessary test files
- Check that dependencies are correctly specified in `pyproject.toml`
- Review the workflow logs for specific error messages

### Linting fails on GitHub but passes locally

- Make sure you've run `make format` before committing
- Check your local ruff version matches the CI version
- Review the specific ruff errors in the workflow logs

## Customization

### Running only on specific paths

To only run CI when certain files change:

```yaml
on:
  pull_request:
    branches: [main]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - '.github/workflows/**'
```

### Adding more Python versions

Test against multiple Python versions:

```yaml
test:
  strategy:
    matrix:
      python-version: ["3.10", "3.11", "3.12"]
  steps:
    - name: Set up Python
      run: uv python install ${{ matrix.python-version }}
```

### Adding search dependencies check

To verify search dependencies install correctly:

```yaml
test-search:
  name: Test Search Dependencies
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: astral-sh/setup-uv@v5
    - name: Set up Python
      run: uv python install 3.10
    - name: Install search dependencies
      run: uv pip install -e ".[search]"
    - name: Test imports
      run: |
        uv run python -c "import faiss; import sentence_transformers; print('Search deps OK')"
```

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pytest Documentation](https://docs.pytest.org/)
