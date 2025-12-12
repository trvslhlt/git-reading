"""Logging utilities with rich output for beautiful CLI experience.

This module provides a centralized logging configuration that combines
Python's standard logging with rich's beautiful console output.

Usage:
    from common.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Processing file...")
    logger.warning("File not found")
    logger.error("Failed to process", exc_info=True)
"""

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

# Global console instance for consistent output
console = Console()


def get_logger(
    name: str,
    level: str | None = None,
    show_time: bool = False,
    show_path: bool = False,
) -> logging.Logger:
    """Get a configured logger with rich output.

    Args:
        name: Logger name (typically __name__ of the module)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses environment variable LOG_LEVEL or defaults to INFO.
        show_time: Show timestamp in log output (default: False for clean CLI)
        show_path: Show file path in log output (default: False for clean CLI)

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing complete")
        Processing complete

        >>> logger = get_logger(__name__, level="DEBUG")
        >>> logger.debug("Detailed info")
        DEBUG    Detailed info
    """
    logger = logging.getLogger(name)

    # Avoid adding multiple handlers if logger already configured
    if logger.handlers:
        return logger

    # Determine log level
    if level is None:
        import os

        level = os.getenv("LOG_LEVEL", "INFO").upper()

    logger.setLevel(level)

    # Create rich handler for beautiful console output
    rich_handler = RichHandler(
        console=console,
        show_time=show_time,
        show_path=show_path,
        rich_tracebacks=True,  # Beautiful tracebacks
        tracebacks_show_locals=True,  # Show local variables in tracebacks
        markup=True,  # Allow rich markup in log messages
    )

    # Simple format for clean CLI output
    formatter = logging.Formatter(
        fmt="%(message)s",
        datefmt="[%X]",
    )
    rich_handler.setFormatter(formatter)

    logger.addHandler(rich_handler)

    # Allow propagation for test frameworks (pytest caplog)
    # Test frameworks can capture logs from propagation
    logger.propagate = True

    return logger


def setup_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """Setup logging configuration for the entire application.

    This should be called once at the application entry point (CLI).

    Args:
        level: Default logging level for all modules
        log_file: Optional file path to also log to a file

    Example:
        # In your CLI entry point (e.g., extract/cli.py)
        from common.logger import setup_logging

        def main():
            setup_logging(level="INFO")
            # ... rest of CLI logic
    """
    import os

    # Allow environment variable to override
    level = os.getenv("LOG_LEVEL", level).upper()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Add rich handler for console output
    rich_handler = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        markup=True,
    )
    rich_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(rich_handler)

    # Optionally add file handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


# Convenience functions for common logging patterns
def progress(message: str) -> None:
    """Log a progress message without the logger prefix.

    Use this for clean progress updates in CLI output.

    Example:
        >>> progress("Processing file 1/10...")
        Processing file 1/10...
    """
    console.print(message)


def success(message: str) -> None:
    """Log a success message with green checkmark.

    Example:
        >>> success("Load complete!")
        ✓ Load complete!
    """
    console.print(f"[green]✓[/green] {message}")


def warning(message: str) -> None:
    """Log a warning message with yellow warning icon.

    Example:
        >>> warning("File not found, skipping...")
        ⚠ File not found, skipping...
    """
    console.print(f"[yellow]⚠[/yellow] {message}")


def error(message: str) -> None:
    """Log an error message with red X icon.

    Example:
        >>> error("Failed to process file")
        ✗ Failed to process file
    """
    console.print(f"[red]✗[/red] {message}", file=sys.stderr)
