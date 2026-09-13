"""Semantic text chunking.

Naive fixed-width slicing (``text[i:i+n]``) cuts entities, sentences, and words
in half, which quietly degrades extraction quality at every chunk boundary. This
splits on natural boundaries instead — paragraphs, then sentences, then words —
and greedily packs them up to a character budget without crossing those
boundaries. Optional overlap carries trailing context into the next chunk so
facts that straddle a boundary are still recoverable.

Pure functions, no dependencies, fully unit-testable.
"""

from __future__ import annotations

import re

_PARAGRAPH = re.compile(r"\n\s*\n")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE = re.compile(r"\s+")


def _hard_split(token: str, max_chars: int) -> list[str]:
    """Last-resort split for a single token longer than the budget."""
    return [token[index : index + max_chars] for index in range(0, len(token), max_chars)]


def _split_words(text: str, max_chars: int) -> list[str]:
    """Pack words up to the budget; hard-split any single oversized word."""
    units: list[str] = []
    current = ""
    for word in text.split(" "):
        if len(word) > max_chars:
            if current:
                units.append(current)
                current = ""
            units.extend(_hard_split(word, max_chars))
            continue
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= max_chars:
            current = f"{current} {word}"
        else:
            units.append(current)
            current = word
    if current:
        units.append(current)
    return units


def _semantic_units(text: str, max_chars: int) -> list[str]:
    """Break text into units no larger than ``max_chars``, on natural boundaries."""
    units: list[str] = []
    for paragraph in _PARAGRAPH.split(text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= max_chars:
            units.append(paragraph)
            continue
        for sentence in _SENTENCE.split(paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) <= max_chars:
                units.append(sentence)
            else:
                units.extend(_split_words(sentence, max_chars))
    return units


def chunk_text(text: str, *, max_chars: int, max_chunks: int, overlap: int = 0) -> list[str]:
    """Split text into up to ``max_chunks`` semantic chunks of at most ``max_chars``.

    Args:
        text: Source text to chunk.
        max_chars: Maximum characters per chunk.
        max_chunks: Hard cap on the number of chunks returned.
        overlap: Characters of trailing context to repeat at the start of the
            next chunk. Clamped so it never consumes the whole budget.
    """
    text = text.strip()
    if not text:
        return [""]
    if len(text) <= max_chars:
        return [text]

    overlap = max(0, min(overlap, max_chars // 2))
    units = _semantic_units(text, max_chars)

    chunks: list[str] = []
    current = ""
    for unit in units:
        if not current:
            current = unit
        elif len(current) + 1 + len(unit) <= max_chars:
            current = f"{current} {unit}"
        else:
            chunks.append(current)
            if len(chunks) >= max_chunks:
                current = ""
                break
            if overlap and len(unit) < max_chars:
                tail = current[-overlap:].lstrip()
                current = f"{tail} {unit}" if len(tail) + 1 + len(unit) <= max_chars else unit
            else:
                current = unit
    if current and len(chunks) < max_chunks:
        chunks.append(current)

    return chunks[:max_chunks] or [""]
