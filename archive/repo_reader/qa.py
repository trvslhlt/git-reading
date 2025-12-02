"""Simple question-answering over repository content."""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List

from .models import AnswerCandidate, CommitInfo, FileSnapshot, RepositorySnapshot

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass
class _Document:
    source: str
    location: str
    excerpt: str
    term_frequency: Dict[str, float]
    weights: Dict[str, float]
    norm: float


class RepositoryIndex:
    """Index that supports bare-bones retrieval over a repository snapshot."""

    def __init__(self, snapshot: RepositorySnapshot) -> None:
        documents = list(_iter_documents(snapshot))
        self._documents: List[_Document] = []
        if not documents:
            self._idf: Dict[str, float] = {}
            return
        doc_freq: Counter[str] = Counter()
        for doc in documents:
            doc_freq.update(doc.term_frequency)
        total_docs = len(documents)
        self._idf = {
            term: math.log((1 + total_docs) / (1 + df)) + 1.0 for term, df in doc_freq.items()
        }
        for doc in documents:
            weights = {
                term: freq * self._idf[term] for term, freq in doc.term_frequency.items()
            }
            norm = math.sqrt(sum(weight * weight for weight in weights.values())) or 1.0
            self._documents.append(
                _Document(
                    source=doc.source,
                    location=doc.location,
                    excerpt=doc.excerpt,
                    term_frequency=doc.term_frequency,
                    weights=weights,
                    norm=norm,
                )
            )

    def query(self, question: str, *, limit: int = 5) -> List[AnswerCandidate]:
        tokens = _tokenize(question)
        if not tokens or not self._documents:
            return []
        q_counter = Counter(tokens)
        q_freq = {term: count / len(tokens) for term, count in q_counter.items() if term in self._idf}
        if not q_freq:
            return []
        q_weights = {term: freq * self._idf[term] for term, freq in q_freq.items()}
        q_norm = math.sqrt(sum(weight * weight for weight in q_weights.values())) or 1.0

        scored: List[AnswerCandidate] = []
        for doc in self._documents:
            numerator = sum(doc.weights.get(term, 0.0) * weight for term, weight in q_weights.items())
            if numerator <= 0.0:
                continue
            score = numerator / (doc.norm * q_norm)
            scored.append(
                AnswerCandidate(
                    score=score,
                    source=doc.source,
                    location=doc.location,
                    excerpt=doc.excerpt,
                )
            )
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:limit]


@dataclass
class _RawDocument:
    source: str
    location: str
    excerpt: str
    term_frequency: Dict[str, float]


def _iter_documents(snapshot: RepositorySnapshot) -> Iterator[_RawDocument]:
    for file_snapshot in snapshot.files:
        yield from _file_documents(file_snapshot)
    for commit in snapshot.commits:
        yield from _commit_documents(commit)


def _file_documents(file_snapshot: FileSnapshot, *, chunk_size: int = 120) -> Iterator[_RawDocument]:
    lines = file_snapshot.lines()
    if not lines:
        return
    for start in range(0, len(lines), chunk_size):
        chunk_lines = lines[start : start + chunk_size]
        text = "\n".join(chunk_lines)
        tokens = _tokenize(text)
        if not tokens:
            continue
        freq = _normalize_term_frequency(tokens)
        location = f"{file_snapshot.path}:{start + 1}"
        excerpt = text[:400]
        yield _RawDocument(
            source="file",
            location=location,
            excerpt=excerpt,
            term_frequency=freq,
        )


def _commit_documents(commit: CommitInfo) -> Iterator[_RawDocument]:
    header = f"{commit.summary}\nAuthor: {commit.author_name} <{commit.author_email}>"
    tokens = _tokenize(header)
    if tokens:
        yield _RawDocument(
            source="commit",
            location=f"{commit.sha[:7]}",
            excerpt=header[:400],
            term_frequency=_normalize_term_frequency(tokens),
        )
    for change in commit.changes:
        text = f"{commit.summary}\nFile: {change.file_path}\n{change.patch}"
        tokens = _tokenize(text)
        if not tokens:
            continue
        yield _RawDocument(
            source="change",
            location=f"{commit.sha[:7]} {change.file_path}",
            excerpt=text[:400],
            term_frequency=_normalize_term_frequency(tokens),
        )


def _tokenize(text: str) -> List[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]


def _normalize_term_frequency(tokens: Iterable[str]) -> Dict[str, float]:
    counter = Counter(tokens)
    total = float(len(tokens)) or 1.0
    return {term: count / total for term, count in counter.items()}
