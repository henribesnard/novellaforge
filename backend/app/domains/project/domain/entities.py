"""Project domain entities."""
from dataclasses import dataclass, field
from typing import Dict, Any
from uuid import UUID


@dataclass
class StoryBible:
    rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Project:
    id: UUID
    title: str
    metadata: Dict[str, Any] = field(default_factory=dict)
