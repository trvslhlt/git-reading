"""Tests for author name parsing from filenames."""

import pytest

from extract.main import author_from_filename


def test_double_underscore_simple_names():
    """Test parsing with double underscore and simple names."""
    assert author_from_filename("barth__john.md") == "John Barth"
    assert author_from_filename("asimov__isaac.md") == "Isaac Asimov"


def test_double_underscore_multipart_last_name():
    """Test parsing with double underscore and multi-part last name."""
    assert author_from_filename("le_guin__ursula_k.md") == "Ursula K Le Guin"
    assert author_from_filename("von_neumann__john.md") == "John Von Neumann"


def test_double_underscore_multipart_first_name():
    """Test parsing with double underscore and multi-part first name."""
    assert author_from_filename("smith__mary_anne.md") == "Mary Anne Smith"
    assert author_from_filename("jones__jean_paul.md") == "Jean Paul Jones"


def test_double_underscore_both_multipart():
    """Test parsing with multi-part first and last names."""
    assert author_from_filename("de_la_cruz__maria_isabel.md") == "Maria Isabel De La Cruz"


def test_fallback_single_underscore():
    """Test fallback behavior for old single underscore format."""
    # Should still work reasonably with old format
    assert author_from_filename("barth_john.md") == "Barth John"
    assert author_from_filename("simple.md") == "Simple"


def test_capitalization():
    """Test that capitalization is applied correctly."""
    assert author_from_filename("le_guin__ursula_k.md") == "Ursula K Le Guin"
    assert author_from_filename("SMITH__JOHN.md") == "John Smith"
