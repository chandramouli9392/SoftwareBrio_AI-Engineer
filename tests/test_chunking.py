from __future__ import annotations

from dave.extractors.chunking import chunk_text


def test_empty_text_returns_single_empty_chunk():
    assert chunk_text("", max_chars=100, max_chunks=8) == [""]


def test_text_under_limit_is_one_chunk():
    text = "Alpha one. Bravo two."
    assert chunk_text(text, max_chars=100, max_chunks=8) == [text]


def test_no_chunk_exceeds_max_chars():
    text = ". ".join(f"Sentence number {n} has some words" for n in range(50)) + "."
    chunks = chunk_text(text, max_chars=120, max_chunks=50)
    assert len(chunks) > 1
    assert all(len(chunk) <= 120 for chunk in chunks)


def test_sentences_are_not_split_mid_sentence():
    sentences = [f"Fact {n} is fully intact here" for n in range(20)]
    text = ". ".join(sentences) + "."
    chunks = chunk_text(text, max_chars=90, max_chunks=50)
    # every original sentence should appear whole inside exactly one chunk
    joined = " || ".join(chunks)
    for sentence in sentences:
        assert sentence in joined


def test_respects_max_chunks():
    text = ". ".join(f"Sentence {n} with content" for n in range(500)) + "."
    chunks = chunk_text(text, max_chars=80, max_chunks=3)
    assert len(chunks) == 3


def test_paragraph_boundaries_are_preferred():
    text = "First paragraph stays together.\n\nSecond paragraph also stays together."
    chunks = chunk_text(text, max_chars=40, max_chunks=8)
    assert "First paragraph stays together." in chunks[0]
    assert any("Second paragraph also stays together." in chunk for chunk in chunks)


def test_oversized_single_token_is_hard_split():
    giant = "x" * 250
    chunks = chunk_text(giant, max_chars=100, max_chunks=8)
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert "".join(chunks) == giant


def test_overlap_carries_context_between_chunks():
    sentences = [f"Sentence {n} carries meaning" for n in range(12)]
    text = ". ".join(sentences) + "."
    chunks = chunk_text(text, max_chars=90, max_chunks=50, overlap=25)
    assert len(chunks) > 1
    # the tail of chunk 0 should reappear at the start of chunk 1
    tail = chunks[0][-25:]
    assert tail.split(" ", 1)[-1][:10] in chunks[1]
