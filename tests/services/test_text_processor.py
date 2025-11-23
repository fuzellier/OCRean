"""Unit tests for text processing utilities."""

from backend.api.app.services.text import TextProcessor


def test_split_into_sentences_removes_story_numbers_and_escapes():
    processor = TextProcessor()
    raw_text = (
        '정해진 일은 아무지게 끝내고 41 반성은 나중에 \\"오늘은 이 옷으로 정했어!\\" '
        "외출하기 전에 거울 앞에 서서 몇 번이고 입었다 벗었다 반복하여 입을 옷을 정한다"
    )

    sentences = processor.split_into_sentences(raw_text)

    assert len(sentences) >= 2
    assert "41" not in sentences[0]
    assert '\\"' not in sentences[0]
    assert sentences[0].startswith("정해진 일은 아무지게 끝내고")


def test_extract_vocabulary_honors_min_length():
    processor = TextProcessor()
    text = "옷 하나 옷 둘 마음 마음가짐"

    short_vocab = processor.extract_vocabulary(text, min_length=1)
    long_vocab = processor.extract_vocabulary(text, min_length=3)

    assert "옷" in short_vocab
    assert "옷" not in long_vocab
    assert "마음가짐" in long_vocab
