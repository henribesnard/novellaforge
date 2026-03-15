"""Simple dependency injection container."""
from __future__ import annotations

from typing import TypeVar, Type, Dict, Callable, Any, Optional
import contextvars
import threading
from contextlib import contextmanager

from .scopes import Scope

T = TypeVar("T")

# Per-task/request scope storage
_scoped_instances: contextvars.ContextVar[Optional[Dict[Type, Any]]] = contextvars.ContextVar(
    "_scoped_instances", default=None
)


class Registration:
    def __init__(self, factory: Callable[["Container"], Any], scope: Scope) -> None:
        self.factory = factory
        self.scope = scope


class Container:
    _instance: Optional["Container"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._registrations: Dict[Type, Registration] = {}
        self._singletons: Dict[Type, Any] = {}
        self._singleton_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "Container":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (tests only)."""
        cls._instance = None

    def register(
        self,
        interface: Type[T],
        factory: Callable[["Container"], T],
        scope: Scope = Scope.SINGLETON,
    ) -> None:
        self._registrations[interface] = Registration(factory, scope)

    def resolve(self, interface: Type[T]) -> T:
        if interface not in self._registrations:
            raise KeyError(f"No registration found for {interface.__name__}")

        registration = self._registrations[interface]

        if registration.scope == Scope.SINGLETON:
            if interface not in self._singletons:
                with self._singleton_lock:
                    if interface not in self._singletons:
                        self._singletons[interface] = registration.factory(self)
            return self._singletons[interface]

        if registration.scope == Scope.SCOPED:
            instances = _scoped_instances.get()
            if instances is None:
                raise RuntimeError("Cannot resolve scoped service outside of scope")
            if interface not in instances:
                instances[interface] = registration.factory(self)
            return instances[interface]

        return registration.factory(self)

    @contextmanager
    def create_scope(self):
        """Create a scope for scoped services (per request). Thread/task safe."""
        token = _scoped_instances.set({})
        try:
            yield self
        finally:
            _scoped_instances.reset(token)

    def is_registered(self, interface: Type) -> bool:
        return interface in self._registrations
