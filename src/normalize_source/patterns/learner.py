"""Learn patterns from a corpus of markdown files."""

import re
from collections import Counter, defaultdict
from pathlib import Path

from ..models import Pattern
from .pattern_store import PatternStore


class PatternLearner:
    """Learn patterns from a corpus of markdown files."""

    def __init__(self):
        """Initialize the pattern learner."""
        self.section_names = Counter()
        self.section_capitalization: dict[str, Counter] = defaultdict(Counter)
        self.citation_formats = Counter()
        self.section_sequences: list[list[str]] = []

    def learn_from_directory(self, directory: Path) -> PatternStore:
        """Analyze all markdown files in directory and learn patterns.

        Args:
            directory: Directory containing markdown files

        Returns:
            PatternStore with learned patterns
        """
        md_files = sorted(directory.glob("*.md"))

        for md_file in md_files:
            self._analyze_file(md_file)

        return self._build_pattern_store()

    def _analyze_file(self, file_path: Path):
        """Analyze a single file for patterns.

        Args:
            file_path: Path to markdown file to analyze
        """
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        current_sections = []

        for line in lines:
            # Extract section names
            if line.startswith("## "):
                section_name = line[3:].strip()
                section_lower = section_name.lower()

                self.section_names[section_lower] += 1
                self.section_capitalization[section_lower][section_name] += 1
                current_sections.append(section_name)

            # Extract citation formats
            citations = re.findall(r"\([^)]*\d+[^)]*\)", line)
            for citation in citations:
                self.citation_formats[citation] += 1

        if current_sections:
            self.section_sequences.append(current_sections)

    def _build_pattern_store(self) -> PatternStore:
        """Convert learned statistics into a pattern store.

        Returns:
            PatternStore containing learned patterns
        """
        store = PatternStore()

        # Build section name patterns
        total_sections = sum(self.section_names.values())
        if total_sections > 0:
            for section_lower, count in self.section_names.most_common():
                # Find most common capitalization
                variants = self.section_capitalization[section_lower]
                most_common_variant, variant_count = variants.most_common(1)[0]

                pattern = Pattern(
                    pattern_type="section_name",
                    value=most_common_variant,
                    frequency=count,
                    confidence=count / total_sections,
                    examples=list(variants.keys())[:5],
                )
                store.add_pattern(pattern)

        # Build citation format patterns
        total_citations = sum(self.citation_formats.values())
        if total_citations > 0:
            for citation_format, count in self.citation_formats.most_common(10):
                pattern = Pattern(
                    pattern_type="citation_format",
                    value=citation_format,
                    frequency=count,
                    confidence=count / total_citations,
                    examples=[citation_format],
                )
                store.add_pattern(pattern)

        return store
