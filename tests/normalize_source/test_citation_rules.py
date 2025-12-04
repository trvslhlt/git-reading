"""Tests for citation validation rules."""

from pathlib import Path

from normalize_source.models import IssueSeverity
from normalize_source.rules.citation_rules import CitationValidator


def test_missing_citation_allowed_at_end():
    """Test that missing citation is allowed if no subsequent citations."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p. 10) Note with citation",
        "- Note without citation",
        "- Another note without citation",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should not flag missing citations at the end
    assert len(issues) == 0


def test_missing_citation_flagged_in_middle():
    """Test that missing citation is flagged if there are subsequent citations."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p. 10) First note with citation",
        "- Note without citation",  # Should be flagged
        "- (p. 20) Another note with citation",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should flag the middle note without citation
    assert len(issues) == 1
    assert issues[0].line_number == 3
    assert issues[0].severity == IssueSeverity.WARNING


def test_multiple_missing_citations_at_end():
    """Test that multiple missing citations at end are all allowed."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p. 10) Note with citation",
        "- Note without citation",
        "- Another note without citation",
        "- Yet another note without citation",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should not flag any missing citations at the end
    assert len(issues) == 0


def test_alternating_citations():
    """Test alternating pattern of citations."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p. 10) First",
        "- No citation",  # Flagged (has subsequent citation)
        "- (p. 20) Second",
        "- No citation",  # Flagged (has subsequent citation)
        "- (p. 30) Third",
        "- No citation",  # Not flagged (no subsequent citations)
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should flag lines 3 and 5 only
    assert len(issues) == 2
    assert issues[0].line_number == 3
    assert issues[1].line_number == 5


def test_malformed_no_space_after_p():
    """Test detection of (p.10) without space after period."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p.10) Note with missing space",
    ]

    issues = validator.validate(lines, Path("test.md"))

    assert len(issues) == 1
    assert issues[0].rule_id == "CITATION_001"
    assert issues[0].severity == IssueSeverity.ERROR
    assert "Missing space after 'p.'" in issues[0].message
    assert issues[0].suggestion == "- (p. 10) Note with missing space"


def test_malformed_no_period_after_p():
    """Test detection of (p 10) without period after p."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p 10) Note with missing period",
    ]

    issues = validator.validate(lines, Path("test.md"))

    assert len(issues) == 1
    assert issues[0].rule_id == "CITATION_001"
    assert issues[0].severity == IssueSeverity.ERROR
    assert "Missing period after 'p'" in issues[0].message
    assert issues[0].suggestion == "- (p. 10) Note with missing period"


def test_malformed_pg_instead_of_p():
    """Test detection of (pg. 10) instead of (p. 10)."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (pg. 10) Note using pg with space",
        "- (pg.10) Note using pg without space",
    ]

    issues = validator.validate(lines, Path("test.md"))

    assert len(issues) == 2
    assert all(i.rule_id == "CITATION_001" for i in issues)
    assert all(i.severity == IssueSeverity.ERROR for i in issues)
    assert all("Use 'p.' instead of 'pg.'" in i.message for i in issues)
    assert issues[0].suggestion == "- (p. 10) Note using pg with space"
    assert issues[1].suggestion == "- (p. 10) Note using pg without space"


def test_malformed_page_instead_of_p():
    """Test detection of (page 10) instead of (p. 10)."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (page 10) Note using page",
        "- (page 42) Another note with page",
    ]

    issues = validator.validate(lines, Path("test.md"))

    assert len(issues) == 2
    assert all(i.rule_id == "CITATION_001" for i in issues)
    assert all(i.severity == IssueSeverity.ERROR for i in issues)
    assert all("Use 'p.' instead of 'page'" in i.message for i in issues)
    assert issues[0].suggestion == "- (p. 10) Note using page"
    assert issues[1].suggestion == "- (p. 42) Another note with page"


def test_malformed_comma_instead_of_period():
    """Test detection of (p, 10) with comma instead of period."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p, 10) Note with comma and space",
        "- (p,10) Note with comma no space",
    ]

    issues = validator.validate(lines, Path("test.md"))

    assert len(issues) == 2
    assert all(i.rule_id == "CITATION_001" for i in issues)
    assert all(i.severity == IssueSeverity.ERROR for i in issues)
    assert all("Use 'p.' instead of 'p,'" in i.message for i in issues)
    assert issues[0].suggestion == "- (p. 10) Note with comma and space"
    assert issues[1].suggestion == "- (p. 10) Note with comma no space"


def test_multiple_malformed_patterns():
    """Test that multiple different malformed patterns are all detected."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p.10) No space",
        "- (p 20) No period",
        "- (pg. 30) Using pg",
        "- (page 40) Using page",
        "- (p, 50) Using comma",
        "- (p. 60) Correct format",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should find 5 malformed citations (line 7 is correct)
    assert len(issues) == 5
    assert all(i.rule_id == "CITATION_001" for i in issues)
    assert all(i.severity == IssueSeverity.ERROR for i in issues)

    # Verify all suggestions use correct format
    for issue in issues:
        assert "(p. " in issue.suggestion


def test_correct_citations_not_flagged():
    """Test that correctly formatted citations are not flagged."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p. 1) Single digit page",
        "- (p. 42) Two digit page",
        "- (p. 100) Three digit page",
        "- (p. 1234) Four digit page",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should not flag any correctly formatted citations
    assert len(issues) == 0


def test_nested_list_items_ignored():
    """Test that nested list items are not checked for citations."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p. 10) Top level with citation",
        "    - Nested item without citation",
        "    - Another nested item",
        "- (p. 20) Another top level",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should not flag nested items or their lack of citations
    assert len(issues) == 0


def test_multiple_sections_independent():
    """Test that citation consistency is checked independently per section."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p. 10) Note in first section",
        "- Missing citation in middle",
        "- (p. 20) Another cited note",
        "## excerpts",
        "- (p. 30) Excerpt with citation",
        "- Excerpt without citation at end",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should only flag the missing citation in middle of notes section
    assert len(issues) == 1
    assert issues[0].rule_id == "CITATION_002"
    assert issues[0].line_number == 3
    assert "Missing citation in middle" in issues[0].context


def test_malformed_and_missing_citations():
    """Test that both malformed format and missing citations are detected."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p. 10) Correct citation",
        "- Missing citation in middle",
        "- (p.20) Malformed no space",
        "- (page 40) Malformed using page",
        "- (p. 50) Another correct citation",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should find 2 CITATION_001 (malformed) and 1 CITATION_002 (missing)
    citation_001_issues = [i for i in issues if i.rule_id == "CITATION_001"]
    citation_002_issues = [i for i in issues if i.rule_id == "CITATION_002"]

    assert len(citation_001_issues) == 2
    assert len(citation_002_issues) == 1
    assert citation_002_issues[0].line_number == 3


def test_range_citations_accepted():
    """Test that page range citations like (p. 10-20) are accepted."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p. 10-20) Note with page range",
        "- (p. 117-118) Another range",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Page ranges should be accepted (not currently validated)
    # Only check that no malformed pattern errors are raised
    malformed_issues = [i for i in issues if i.rule_id == "CITATION_001"]
    assert len(malformed_issues) == 0


def test_question_mark_page_numbers():
    """Test that question mark page numbers like (p. ???) don't cause errors."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p. ???) Note with unknown page",
        "- (p. 20) Known page",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should not crash or flag ??? as malformed
    # The ??? pattern won't match citation patterns, so it's treated as no citation
    assert all(i.rule_id != "CITATION_001" for i in issues)
