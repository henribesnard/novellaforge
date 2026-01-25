"""Shared kernel value objects."""
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ProjectId:
    value: UUID

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def from_string(cls, value: str) -> "ProjectId":
        return cls(UUID(value))


@dataclass(frozen=True)
class ChapterId:
    value: UUID

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class UserId:
    value: UUID

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class WordCount:
    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("Word count cannot be negative")

    def is_within_range(self, min_words: int, max_words: int) -> bool:
        return min_words <= self.value <= max_words


@dataclass(frozen=True)
class CoherenceScore:
    value: float

    def __post_init__(self) -> None:
        if not 0 <= self.value <= 10:
            raise ValueError("Coherence score must be between 0 and 10")

    def is_acceptable(self, threshold: float = 7.0) -> bool:
        return self.value >= threshold


@dataclass(frozen=True)
class ChapterContent:
    text: str
    word_count: WordCount

    @classmethod
    def create(cls, text: str) -> "ChapterContent":
        words = len(text.split())
        return cls(text=text, word_count=WordCount(words))
