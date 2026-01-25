"""Coherence domain entities."""
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Contradiction:
    description: str
    severity: str


@dataclass(frozen=True)
class ValidationResult:
    coherence_score: float
    blocking: bool
    contradictions: List[Contradiction]
