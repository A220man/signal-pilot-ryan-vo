"""Tests for the deterministic tokenizer."""
from __future__ import annotations

import pytest

from app.services.tokenizer import (
    build_inverted_index,
    document_length,
    term_frequencies,
    tokenize,
    validate_tokens,
)


class TestTokenize:
    def test_lowercase_extraction(self):
        """Tokens are lowercased."""
        result = tokenize("Hello World")
        assert result == ["hello", "world"]

    def test_alphanumeric_only(self):
        """Non-alphanumeric characters are stripped."""
        result = tokenize("hello, world! 123")
        assert result == ["hello", "world", "123"]

    def test_stop_word_filtering(self):
        """Common stop words are removed by default."""
        result = tokenize("the quick brown fox jumps over the lazy dog")
        assert "the" not in result
        assert "over" not in result
        assert "brown" in result

    def test_stop_word_filtering_disabled(self):
        """When skip_stopwords=False, stop words are kept."""
        result = tokenize("the quick brown fox", skip_stopwords=False)
        assert "the" in result

    def test_empty_string(self):
        """Empty input yields empty token list."""
        assert tokenize("") == []

    def test_only_stop_words(self):
        """Input consisting solely of stop words yields empty list after filtering."""
        assert tokenize("the a an") == []

    def test_punctuation_boundaries(self):
        """Tokens are split on non-alphanumeric boundaries."""
        result = tokenize("foo.bar,baz")
        assert result == ["foo", "bar", "baz"]

    def test_unicode_lowercased(self):
        """ASCII letters are lowercased; non-ASCII alphanumeric is stripped."""
        result = tokenize("HELLO Café WORLD")
        assert "hello" in result
        assert "world" in result


class TestTermFrequencies:
    def test_basic_frequency(self):
        freqs = term_frequencies(["a", "b", "a", "c", "a"])
        assert freqs == {"a": 3, "b": 1, "c": 1}

    def test_empty_list(self):
        assert term_frequencies([]) == {}


class TestDocumentLength:
    def test_token_count(self):
        assert document_length(["a", "b", "c"]) == 3

    def test_empty(self):
        assert document_length([]) == 0


class TestBuildInvertedIndex:
    def test_same_as_frequencies(self):
        tokens = ["alpha", "beta", "alpha", "gamma"]
        assert build_inverted_index(tokens) == {"alpha": 2, "beta": 1, "gamma": 1}


class TestValidateTokens:
    def test_valid_tokens(self):
        validate_tokens(["hello", "world", "123"])

    def test_empty_token_raises(self):
        with pytest.raises(ValueError, match="Empty token"):
            validate_tokens(["hello", ""])

    def test_uppercase_raises(self):
        with pytest.raises(ValueError, match="not lowercase"):
            validate_tokens(["Hello"])

    def test_non_alphanumeric_raises(self):
        with pytest.raises(ValueError, match="not alphanumeric"):
            validate_tokens(["hello!"])