"""Text processing utilities for cleaning text, sentences, and vocabulary."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from kss import split_sentences

KOREAN_PATTERN = re.compile(r"[가-힣]+")
NOISE_PATTERN = re.compile(r"^[\W\d_]+$", re.UNICODE)
WHITESPACE_PATTERN = re.compile(r"\s+")
ESCAPED_QUOTE_PATTERN = re.compile(r'\\"')
DIGIT_ORPHAN_PATTERN = re.compile(r"\b\d{1,4}\b")
QUOTE_PATTERN = re.compile(r'(["\'])(.+?)\1')
SENTENCE_STRIP_CHARS = " :;-—\"'“”‘’·•()[]"
MIN_SENTENCE_LENGTH = 3


class TextProcessor:
    """Encapsulates text cleaning, sentence splitting, and vocabulary extraction."""

    def __init__(self) -> None:
        self._spacer = self._init_spacer()

    def clean_text(self, text: str) -> str:
        """Normalize whitespace, fix simple OCR artifacts, and trim."""
        normalized = (text or "").replace("\\n", " ")
        normalized = ESCAPED_QUOTE_PATTERN.sub('"', normalized)
        normalized = WHITESPACE_PATTERN.sub(" ", normalized)
        normalized = self._maybe_apply_spacing(normalized)
        normalized = WHITESPACE_PATTERN.sub(" ", normalized)
        return normalized.strip()

    def split_into_sentences(self, text: str) -> list[str]:
        """Split cleaned Korean text into sentences."""
        normalized = self.clean_text(text)
        if not normalized:
            return []
        raw_sentences = split_sentences(normalized)
        return self._post_process_sentences(raw_sentences)

    def extract_vocabulary(self, text: str, min_length: int = 1) -> list[str]:
        """Extract unique Korean words above a minimum length."""
        normalized = self.clean_text(text)
        words = KOREAN_PATTERN.findall(normalized)
        filtered = {word for word in words if len(word) >= max(1, min_length)}
        return sorted(filtered)

    # Internal helpers -------------------------------------------------

    def _post_process_sentences(self, sentences: Sequence[str]) -> list[str]:
        cleaned: list[str] = []
        for sentence in sentences:
            for segment in self._split_quoted_segments(sentence):
                normalized = self._normalize_sentence(segment)
                if normalized:
                    cleaned.append(normalized)
        return cleaned

    def _normalize_sentence(self, sentence: str) -> str | None:
        if not sentence:
            return None
        text = sentence.strip(SENTENCE_STRIP_CHARS)
        text = DIGIT_ORPHAN_PATTERN.sub("", text)
        text = WHITESPACE_PATTERN.sub(" ", text).strip(SENTENCE_STRIP_CHARS)
        if len(text) < MIN_SENTENCE_LENGTH:
            return None
        if NOISE_PATTERN.fullmatch(text):
            return None
        return text

    def _split_quoted_segments(self, sentence: str) -> list[str]:
        segments: list[str] = []
        last_index = 0

        for match in QUOTE_PATTERN.finditer(sentence):
            prefix = sentence[last_index : match.start()].strip()
            if prefix:
                segments.append(prefix)

            quoted = match.group(0).strip()
            if quoted:
                segments.append(quoted)

            last_index = match.end()

        suffix = sentence[last_index:].strip()
        if suffix:
            segments.append(suffix)

        return segments

    def _maybe_apply_spacing(self, text: str) -> str:
        if not self._spacer:
            return text
        try:
            return self._spacer.spacing(text)
        except Exception:
            return text

    def _init_spacer(self) -> Any | None:
        try:
            from pecab import Pecab

            return Pecab()
        except Exception:
            return None
