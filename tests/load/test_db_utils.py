"""Unit tests for db_utils module."""

import pytest

from load.db_utils import (
    _generate_id,
    generate_author,
    generate_author_id,
    generate_book_id,
)


class TestGenerateAuthor:
    """Tests for generate_author function."""

    def test_both_names_provided(self):
        """Test with both first and last names."""
        assert generate_author("John", "Doe") == "John Doe"
        assert generate_author("Jane", "Smith") == "Jane Smith"

    def test_only_last_name(self):
        """Test with only last name provided."""
        assert generate_author("", "Smith") == "Smith"
        assert generate_author(None, "Doe") == "Doe"

    def test_only_first_name(self):
        """Test with only first name provided."""
        assert generate_author("Jane", "") == "Jane"
        assert generate_author("John", None) == "John"

    def test_both_empty(self):
        """Test with both names empty."""
        assert generate_author("", "") == "Unknown"

    def test_both_none(self):
        """Test with both names None."""
        assert generate_author(None, None) == "Unknown"

    def test_mixed_none_and_empty(self):
        """Test with mix of None and empty strings."""
        assert generate_author(None, "Doe") == "Doe"
        assert generate_author("John", None) == "John"
        assert generate_author("", None) == "Unknown"
        assert generate_author(None, "") == "Unknown"

    def test_whitespace_names(self):
        """Test names with surrounding whitespace."""
        # Current implementation doesn't strip whitespace
        # This test documents the current behavior
        assert generate_author(" John ", " Doe ") == " John   Doe "

    def test_multi_word_names(self):
        """Test with multi-word first or last names."""
        assert generate_author("Mary Anne", "Smith") == "Mary Anne Smith"
        assert generate_author("John", "von Neumann") == "John von Neumann"
        assert generate_author("Jean Paul", "Sartre") == "Jean Paul Sartre"


class TestGenerateId:
    """Tests for _generate_id helper function."""

    def test_lowercase_conversion(self):
        """Test that uppercase is converted to lowercase."""
        assert _generate_id("ABC") == "abc"
        assert _generate_id("JoHn DoE") == "john-doe"

    def test_space_to_hyphen(self):
        """Test that spaces are converted to hyphens."""
        assert _generate_id("a b c") == "a-b-c"
        assert _generate_id("John Doe") == "john-doe"

    def test_multiple_spaces_normalized(self):
        """Test that multiple consecutive spaces become single hyphen."""
        assert _generate_id("a  b   c") == "a-b-c"
        assert _generate_id("John    Doe") == "john-doe"

    def test_special_characters_removed(self):
        """Test that special characters are removed."""
        assert _generate_id("a!@#$b") == "ab"
        assert _generate_id("O'Brien") == "obrien"
        assert _generate_id("José García") == "josé-garcía"  # Accents preserved
        assert _generate_id("Book: Subtitle!") == "book-subtitle"

    def test_preserve_allowed_characters(self):
        """Test that hyphens, underscores, and alphanumerics are allowed."""
        assert _generate_id("a-b_c") == "a-b_c"
        assert _generate_id("test_123-abc") == "test_123-abc"

    def test_numbers_preserved(self):
        """Test that numbers are preserved."""
        assert _generate_id("2001 A Space Odyssey") == "2001-a-space-odyssey"
        assert _generate_id("Room 237") == "room-237"

    def test_length_limit(self):
        """Test that strings longer than 100 chars are truncated."""
        long_name = "a" * 150
        result = _generate_id(long_name)
        assert len(result) == 100

        # Test with spaces that become hyphens
        long_with_spaces = " ".join(["word"] * 30)  # Much longer than 100
        result = _generate_id(long_with_spaces)
        assert len(result) == 100

    def test_empty_string(self):
        """Test with empty string."""
        assert _generate_id("") == ""

    def test_single_character(self):
        """Test with single character."""
        assert _generate_id("a") == "a"
        assert _generate_id("A") == "a"

    def test_only_special_characters(self):
        """Test string with only special characters."""
        assert _generate_id("!@#$%") == ""
        assert _generate_id("   ") == ""

    def test_leading_trailing_whitespace(self):
        """Test handling of leading/trailing whitespace."""
        assert _generate_id("  abc  ") == "abc"
        assert _generate_id("  a  b  ") == "a-b"


class TestGenerateAuthorId:
    """Tests for generate_author_id function."""

    def test_simple_name(self):
        """Test with simple author name."""
        assert generate_author_id("John Doe") == "john-doe"
        assert generate_author_id("Jane Smith") == "jane-smith"

    def test_multiple_words(self):
        """Test with multiple word names."""
        assert generate_author_id("John Paul Jones") == "john-paul-jones"
        assert generate_author_id("Mary Anne Smith") == "mary-anne-smith"

    def test_special_characters(self):
        """Test names with special characters."""
        assert generate_author_id("O'Brien") == "obrien"
        assert generate_author_id("Jean-Paul Sartre") == "jean-paul-sartre"

    def test_accents_unicode(self):
        """Test names with accents and unicode characters."""
        # Current implementation preserves accents
        assert generate_author_id("José García") == "josé-garcía"

    def test_extra_spaces(self):
        """Test names with extra spaces."""
        assert generate_author_id("John  Doe") == "john-doe"
        assert generate_author_id("  John Doe  ") == "john-doe"

    def test_long_name(self):
        """Test that long names are truncated to 100 characters."""
        long_name = "Very " * 30 + "Long Name"
        result = generate_author_id(long_name)
        assert len(result) <= 100

    def test_empty_string(self):
        """Test with empty string."""
        assert generate_author_id("") == ""

    def test_single_character(self):
        """Test with single character."""
        assert generate_author_id("A") == "a"

    def test_stability(self):
        """Test that same input produces same output."""
        name = "John Doe"
        id1 = generate_author_id(name)
        id2 = generate_author_id(name)
        assert id1 == id2


class TestGenerateBookId:
    """Tests for generate_book_id function."""

    def test_simple_case(self):
        """Test with simple title and author."""
        assert generate_book_id("The Book", "John Doe") == "the-book_john-doe"
        assert generate_book_id("My Story", "Jane Smith") == "my-story_jane-smith"

    def test_long_title(self):
        """Test that long titles are truncated."""
        long_title = "A Very " * 30 + "Long Title"
        result = generate_book_id(long_title, "Author")
        assert len(result) <= 100

    def test_special_characters(self):
        """Test that special characters are removed."""
        assert generate_book_id("Book: Subtitle!", "Author") == "book-subtitle_author"
        assert generate_book_id("Book?", "O'Brien") == "book_obrien"

    def test_numbers_preserved(self):
        """Test that numbers are preserved in title."""
        result = generate_book_id("2001: A Space Odyssey", "Arthur C Clarke")
        assert "2001" in result
        assert result == "2001-a-space-odyssey_arthur-c-clarke"

    def test_stability(self):
        """Test that same inputs produce same output."""
        id1 = generate_book_id("The Book", "John Doe")
        id2 = generate_book_id("The Book", "John Doe")
        assert id1 == id2

    def test_different_authors_same_title(self):
        """Test that same title with different authors produces different IDs."""
        id1 = generate_book_id("The Book", "John Doe")
        id2 = generate_book_id("The Book", "Jane Smith")
        assert id1 != id2

    def test_empty_title(self):
        """Test with empty title."""
        result = generate_book_id("", "John Doe")
        assert "john-doe" in result

    def test_empty_author(self):
        """Test with empty author."""
        result = generate_book_id("The Book", "")
        assert "the-book" in result

    def test_both_empty(self):
        """Test with both title and author empty."""
        result = generate_book_id("", "")
        assert result == "_"

    def test_unicode_in_title(self):
        """Test title with unicode characters."""
        result = generate_book_id("Café Life", "Author")
        # Current implementation removes or transforms unicode
        assert "caf" in result.lower()

    def test_punctuation_combinations(self):
        """Test various punctuation combinations."""
        result = generate_book_id("Book (2023): Edition #2!", "Author")
        assert result == "book-2023-edition-2_author"
