import pytest
from uuid import uuid4

from app.shared_kernel.domain_events import ChapterGeneratedEvent


def test_chapter_generated_event_creation():
    event = ChapterGeneratedEvent(
        project_id=uuid4(),
        chapter_id=uuid4(),
        chapter_index=1,
        word_count=2500,
        content_hash="abc123",
    )
    assert event.event_id is not None
    assert event.occurred_at is not None


def test_event_to_dict():
    event = ChapterGeneratedEvent(
        project_id=uuid4(),
        chapter_id=uuid4(),
        chapter_index=1,
        word_count=2500,
        content_hash="abc123",
    )
    data = event.to_dict()
    assert "event_type" in data
    assert data["event_type"] == "ChapterGeneratedEvent"
    assert "payload" in data
