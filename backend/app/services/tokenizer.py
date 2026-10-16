"""Deterministic text tokenizer: lowercase, alphanumeric, stop-word filtering."""
from __future__ import annotations

import re
from typing import Dict, List

# Matches ASCII alphanumeric sequences; used for deterministic tokenization
# without external NLP dependencies.
_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Minimal stop-word set — enough to reduce noise without importing heavy NLP libs.
# These are common English words that carry little retrieval signal.
_STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "can", "this", "that",
    "these", "those", "as", "if", "then", "than", "so", "not", "no",
    "but", "all", "any", "each", "few", "more", "most", "other", "some",
    "such", "only", "own", "same", "too", "very", "just", "now", "over",
    "also", "into", "about",
})


def tokenize(text: str, *, skip_stopwords: bool = True) -> List[str]:
    """Tokenize *text* into a list of lowercase alphanumeric tokens.

    The tokenizer is fully deterministic: identical input always produces
    identical output, with no randomness or external model dependency.
    """
    tokens = _TOKEN_RE.findall(text.lower())
    if skip_stopwords:
        tokens = [t for t in tokens if t not in _STOP_WORDS]
    return tokens


def term_frequencies(tokens: List[str]) -> Dict[str, int]:
    """Compute term→frequency mapping for a token list."""
    freq: Dict[str, int] = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    return freq


def document_length(tokens: List[str]) -> int:
    """Return document length (token count)."""
    return len(tokens)


def build_inverted_index(tokens: List[str]) -> Dict[str, int]:
    """Build a term→frequency map from a token list (alias for term_frequencies)."""
    return term_frequencies(tokens)


def validate_tokens(tokens: List[str]) -> None:
    """Ensure tokens are valid (non-empty lowercase alphanumeric)."""
    for token in tokens:
        if not token:
            raise ValueError("Empty token encountered")
        if token != token.lower():
            raise ValueError(f"Token '{token}' is not lowercase")
        if not _TOKEN_RE.fullmatch(token):
            raise ValueError(f"Token '{token}' is not alphanumeric")