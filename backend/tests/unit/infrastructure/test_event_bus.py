import pytest
from uuid import uuid4

from app.infrastructure.event_bus import InMemoryEventBus
from app.shared_kernel.domain_events import ChapterGeneratedEvent


@pytest.mark.asyncio
async def test_in_memory_event_bus_dispatches():
    bus = InMemoryEventBus()
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(ChapterGeneratedEvent, handler)
    event = ChapterGeneratedEvent(
        project_id=uuid4(),
        chapter_id=uuid4(),
        chapter_index=1,
        word_count=1000,
        content_hash="hash",
    )
    await bus.publish(event)

    assert received == [event]
