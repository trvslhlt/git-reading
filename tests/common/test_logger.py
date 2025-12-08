"""Tests for logging utilities."""

import logging

import pytest

from common.logger import get_logger


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger_instance(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)

    def test_logger_name(self):
        """Test that logger has correct name."""
        logger = get_logger("test.module")
        assert logger.name == "test.module"

    def test_default_level_is_info(self):
        """Test that default logging level is INFO."""
        logger = get_logger("test.default")
        assert logger.level == logging.INFO

    def test_custom_level(self):
        """Test that custom logging level can be set."""
        logger = get_logger("test.custom", level="DEBUG")
        assert logger.level == logging.DEBUG

    def test_logger_has_handler(self):
        """Test that logger is configured with a handler."""
        logger = get_logger("test.handler")
        assert len(logger.handlers) > 0

    def test_reuses_existing_logger(self):
        """Test that get_logger reuses existing logger instance."""
        logger1 = get_logger("test.reuse")
        logger2 = get_logger("test.reuse")
        assert logger1 is logger2
        # Should not add duplicate handlers
        assert len(logger1.handlers) == len(logger2.handlers)

    def test_logging_output(self, caplog):
        """Test that logging actually produces output."""
        logger = get_logger("test.output")

        with caplog.at_level(logging.INFO):
            logger.info("Test message")

        assert "Test message" in caplog.text

    def test_log_levels(self, caplog):
        """Test different log levels."""
        logger = get_logger("test.levels", level="DEBUG")

        with caplog.at_level(logging.DEBUG):
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

        assert "Debug message" in caplog.text
        assert "Info message" in caplog.text
        assert "Warning message" in caplog.text
        assert "Error message" in caplog.text

    def test_info_level_filters_debug(self, caplog):
        """Test that INFO level filters out DEBUG messages."""
        logger = get_logger("test.filter", level="INFO")

        with caplog.at_level(logging.DEBUG):
            logger.debug("This should not appear")
            logger.info("This should appear")

        assert "This should not appear" not in caplog.text
        assert "This should appear" in caplog.text
