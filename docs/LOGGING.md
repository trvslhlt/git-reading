# Logging Guide

This project uses Python's standard `logging` module with [rich](https://rich.readthedocs.io/) for beautiful CLI output.

## Quick Start

```python
from common.logger import get_logger

logger = get_logger(__name__)

logger.info("Processing complete")       # Normal user-facing messages
logger.debug("Reading file config.json")  # Detailed debugging info
logger.warning("File not found, using default")  # Warnings
logger.error("Failed to connect to database")    # Errors
```

## When to Use Each Log Level

### INFO
Use for **important user-facing progress updates**.

**Examples:**
- "Found 10 markdown files"
- "✓ Wrote index with 49 books"
- "Starting migration..."

**When NOT to use:**
- File-by-file processing details (use DEBUG)
- Internal function calls (use DEBUG)

### DEBUG
Use for **detailed information useful during development/debugging**.

**Examples:**
- "Parsing barth__john.md..."
- "Found 27 books in file"
- "Connecting to database at path/to/db"

**When to use:**
- Should only appear when user explicitly requests verbose output (`LOG_LEVEL=DEBUG`)
- Internal processing details
- Step-by-step execution flow

### WARNING
Use for **recoverable issues or deprecated features**.

**Examples:**
- "No git repository found, dates will be unavailable"
- "File not found, skipping..."
- "Using deprecated format, please migrate"

**When to use:**
- Something unexpected but not fatal
- Falling back to defaults
- User should be aware but operation continues

### ERROR
Use for **failures that prevent an operation from completing**.

**Examples:**
- "Failed to parse markdown file"
- "Database connection failed"
- "Invalid configuration"

**When to use:**
- Operation failed
- Data is corrupt
- Cannot proceed with current task

## Rich Markup

You can use rich markup for beautiful output:

```python
logger.info(f"Found [bold]{count}[/bold] files")
logger.info("[green]✓[/green] Migration complete")
logger.warning("[yellow]⚠[/yellow] Deprecated feature")
logger.error("[red]✗[/red] Operation failed")
```

## Controlling Log Levels

### Via Environment Variable
```bash
# Show everything (including DEBUG)
LOG_LEVEL=DEBUG python -m extract.cli

# Only warnings and errors
LOG_LEVEL=WARNING python -m extract.cli
```

### Via make Commands
```bash
# With debug output
LOG_LEVEL=DEBUG make run-extract

# Normal output
make run-extract
```

## Testing with Logging

Pytest's `caplog` fixture automatically captures log output:

```python
def test_my_function(caplog):
    logger = get_logger("test")

    with caplog.at_level(logging.INFO):
        logger.info("Test message")

    assert "Test message" in caplog.text
```

## Migration Guide

### Before (print statements)
```python
def process_files(files):
    print(f"Found {len(files)} files")

    for file in files:
        print(f"  Processing {file}...")
        result = do_something(file)
        print(f"    Result: {result}")

    print(f"\nComplete! Processed {len(files)} files")
```

### After (logging)
```python
from common.logger import get_logger

logger = get_logger(__name__)

def process_files(files):
    logger.info(f"Found [bold]{len(files)}[/bold] files")

    for file in files:
        logger.debug(f"Processing {file}...")
        result = do_something(file)
        logger.debug(f"  Result: {result}")

    logger.info(f"[green]✓[/green] Processed {len(files)} files")
```

**Key changes:**
1. Import logger at module level
2. `print()` → `logger.info()` for user messages
3. Detailed output → `logger.debug()`
4. Add rich markup for visual clarity
5. Use appropriate log levels

## Best Practices

### ✅ DO
- Use `logger.info()` for high-level progress users care about
- Use `logger.debug()` for implementation details
- Use rich markup for better visual hierarchy
- Include context in log messages (file names, counts, etc.)
- One logger per module: `logger = get_logger(__name__)`

### ❌ DON'T
- Don't use `print()` for logging (except in utility functions that return formatted output)
- Don't log sensitive information (passwords, tokens, PII)
- Don't log in tight loops without checking level first
- Don't use bare exceptions: always use `exc_info=True` for stack traces
  ```python
  try:
      risky_operation()
  except Exception as e:
      logger.error(f"Operation failed: {e}", exc_info=True)
  ```

## Comparison with Print Statements

| Aspect | Print Statements | Logging Framework |
|--------|------------------|-------------------|
| Verbosity control | ❌ None | ✅ DEBUG/INFO/WARNING/ERROR |
| Beautiful output | ❌ Plain text | ✅ Colors, formatting, emojis |
| Testing | ❌ Hard to capture | ✅ pytest caplog fixture |
| Timestamps | ❌ Manual | ✅ Automatic (if enabled) |
| File output | ❌ Redirection only | ✅ Built-in file handlers |
| Production ready | ❌ No | ✅ Yes |
| Complexity | ✅ Very simple | ⚠️ Moderate |

## Examples from the Codebase

See [src/extract/main.py](../src/extract/main.py) for a real-world example of migrated code.

**Key patterns:**
- User-facing counts use `logger.info()` with bold markup
- File-by-file processing uses `logger.debug()`
- Warnings for missing git repo use `logger.warning()`
- Success messages use green checkmark with `logger.info()`

## Further Reading

- [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html)
- [Rich Documentation](https://rich.readthedocs.io/)
- [Rich Markup Guide](https://rich.readthedocs.io/en/stable/markup.html)
