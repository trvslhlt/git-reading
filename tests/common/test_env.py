"""Tests for environment configuration interface."""

import os

import pytest

from common.env import Environment, env


class TestEnvironment:
    """Tests for Environment class."""

    def test_database_type_default(self, monkeypatch):
        """Test database_type returns default value."""
        monkeypatch.delenv("DATABASE_TYPE", raising=False)
        assert Environment.database_type() == "postgresql"

    def test_database_type_from_env(self, monkeypatch):
        """Test database_type reads from environment."""
        monkeypatch.setenv("DATABASE_TYPE", "sqlite")
        assert Environment.database_type() == "sqlite"

    def test_database_path_default(self, monkeypatch):
        """Test database_path returns default value."""
        monkeypatch.delenv("DATABASE_PATH", raising=False)
        result = Environment.database_path()
        assert str(result) == "data/readings.db"

    def test_database_path_from_env(self, monkeypatch):
        """Test database_path reads from environment."""
        monkeypatch.setenv("DATABASE_PATH", "/tmp/test.db")
        result = Environment.database_path()
        assert str(result) == "/tmp/test.db"

    def test_postgres_host_default(self, monkeypatch):
        """Test postgres_host returns default value."""
        monkeypatch.delenv("POSTGRES_HOST", raising=False)
        assert Environment.postgres_host() == "localhost"

    def test_postgres_host_from_env(self, monkeypatch):
        """Test postgres_host reads from environment."""
        monkeypatch.setenv("POSTGRES_HOST", "db.example.com")
        assert Environment.postgres_host() == "db.example.com"

    def test_postgres_port_default(self, monkeypatch):
        """Test postgres_port returns default value."""
        monkeypatch.delenv("POSTGRES_PORT", raising=False)
        assert Environment.postgres_port() == 5432

    def test_postgres_port_from_env(self, monkeypatch):
        """Test postgres_port reads from environment."""
        monkeypatch.setenv("POSTGRES_PORT", "5433")
        assert Environment.postgres_port() == 5433

    def test_postgres_database_default(self, monkeypatch):
        """Test postgres_database returns default value."""
        monkeypatch.delenv("POSTGRES_DB", raising=False)
        assert Environment.postgres_database() == "git_reading"

    def test_postgres_database_from_env(self, monkeypatch):
        """Test postgres_database reads from environment."""
        monkeypatch.setenv("POSTGRES_DB", "custom_db")
        assert Environment.postgres_database() == "custom_db"

    def test_postgres_user_default(self, monkeypatch):
        """Test postgres_user returns default value."""
        monkeypatch.delenv("POSTGRES_USER", raising=False)
        assert Environment.postgres_user() == "git_reading_user"

    def test_postgres_user_from_env(self, monkeypatch):
        """Test postgres_user reads from environment."""
        monkeypatch.setenv("POSTGRES_USER", "custom_user")
        assert Environment.postgres_user() == "custom_user"

    def test_postgres_password_default(self, monkeypatch):
        """Test postgres_password returns default value."""
        monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
        assert Environment.postgres_password() == ""

    def test_postgres_password_from_env(self, monkeypatch):
        """Test postgres_password reads from environment."""
        monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
        assert Environment.postgres_password() == "secret"

    def test_postgres_pool_size_default(self, monkeypatch):
        """Test postgres_pool_size returns default value."""
        monkeypatch.delenv("POSTGRES_POOL_SIZE", raising=False)
        assert Environment.postgres_pool_size() == 5

    def test_postgres_pool_size_from_env(self, monkeypatch):
        """Test postgres_pool_size reads from environment."""
        monkeypatch.setenv("POSTGRES_POOL_SIZE", "10")
        assert Environment.postgres_pool_size() == 10

    def test_postgres_pool_max_overflow_default(self, monkeypatch):
        """Test postgres_pool_max_overflow returns default value."""
        monkeypatch.delenv("POSTGRES_POOL_MAX_OVERFLOW", raising=False)
        assert Environment.postgres_pool_max_overflow() == 10

    def test_postgres_pool_max_overflow_from_env(self, monkeypatch):
        """Test postgres_pool_max_overflow reads from environment."""
        monkeypatch.setenv("POSTGRES_POOL_MAX_OVERFLOW", "20")
        assert Environment.postgres_pool_max_overflow() == 20


class TestEnvSingleton:
    """Tests for env singleton instance."""

    def test_env_is_environment_instance(self):
        """Test that env is an instance of Environment."""
        assert isinstance(env, Environment)

    def test_env_singleton_methods_work(self, monkeypatch):
        """Test that env singleton methods work."""
        monkeypatch.setenv("DATABASE_TYPE", "sqlite")
        assert env.database_type() == "sqlite"
