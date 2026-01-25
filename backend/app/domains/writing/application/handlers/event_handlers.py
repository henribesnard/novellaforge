"""Event handlers for the writing context."""
from __future__ import annotations

from typing import Any

from app.shared_kernel.domain_events import ChapterGeneratedEvent, ChapterApprovedEvent


async def handle_chapter_generated(event: ChapterGeneratedEvent) -> Any:
    return None


async def handle_chapter_approved(event: ChapterApprovedEvent) -> Any:
    return None
