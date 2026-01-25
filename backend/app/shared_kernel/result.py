"""Result type to make errors explicit."""
from dataclasses import dataclass
from typing import Generic, TypeVar, Optional, Callable

T = TypeVar("T")
E = TypeVar("E", bound=Exception)


@dataclass
class Result(Generic[T, E]):
    """Container for a success value or failure error."""

    _value: Optional[T] = None
    _error: Optional[E] = None

    @property
    def is_success(self) -> bool:
        return self._error is None

    @property
    def is_failure(self) -> bool:
        return self._error is not None

    @property
    def value(self) -> T:
        if self._error:
            raise self._error
        return self._value  # type: ignore[return-value]

    @property
    def error(self) -> Optional[E]:
        return self._error

    @classmethod
    def success(cls, value: T) -> "Result[T, E]":
        return cls(_value=value)

    @classmethod
    def failure(cls, error: E) -> "Result[T, E]":
        return cls(_error=error)

    def map(self, func: Callable[[T], T]) -> "Result[T, E]":
        if self.is_success:
            return Result.success(func(self._value))
        return self
