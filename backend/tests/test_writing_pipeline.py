from app.services.writing_pipeline import WritingPipeline


def test_quality_gate_accepts_good_chapter():
    pipeline = WritingPipeline.__new__(WritingPipeline)
    state = {
        "critique_score": 8.5,
        "chapter_text": "one two three four",
        "min_word_count": 1,
        "max_word_count": 10,
        "revision_count": 0,
    }

    assert pipeline._quality_gate(state) == "done"


def test_quality_gate_requests_revision():
    pipeline = WritingPipeline.__new__(WritingPipeline)
    state = {
        "critique_score": 6.0,
        "chapter_text": "one two three four",
        "min_word_count": 1,
        "max_word_count": 10,
        "revision_count": 1,
    }

    assert pipeline._quality_gate(state) == "revise"


def test_quality_gate_stops_after_limit():
    pipeline = WritingPipeline.__new__(WritingPipeline)
    state = {
        "critique_score": 4.0,
        "chapter_text": "one two three four",
        "min_word_count": 1,
        "max_word_count": 10,
        "revision_count": 3,
    }

    assert pipeline._quality_gate(state) == "done"
