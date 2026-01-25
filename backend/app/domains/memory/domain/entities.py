"""Memory domain entities."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ContinuityFact:
    name: str
    description: str
    chapter_index: Optional[int] = None


@dataclass(frozen=True)
class CharacterState:
    name: str
    status: str
    last_seen_chapter: Optional[int] = None
