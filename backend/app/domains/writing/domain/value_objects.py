"""Writing domain value objects."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class WritingState:
    status: str


@dataclass(frozen=True)
class GenerationConfig:
    target_word_count: Optional[int] = None
    use_rag: bool = True
    use_memory: bool = True
