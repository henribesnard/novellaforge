"""Service registration for the DI container."""
from __future__ import annotations

from app.infrastructure.di.container import Container
from app.infrastructure.di.scopes import Scope
from app.core.config import settings
from app.services.llm_client import DeepSeekClient
from app.services.memory_service import MemoryService
from app.services.rag_service import RagService
from app.services.cache_service import CacheService
from app.services.coherence.chekhov_tracker import ChekhovTracker
from app.services.coherence.character_drift import CharacterDriftDetector
from app.services.coherence.voice_analyzer import VoiceConsistencyAnalyzer
from app.services.coherence.pov_validator import POVValidator
from app.infrastructure.event_bus import EventBus, InMemoryEventBus, RedisStreamsEventBus


def configure_container(container: Container) -> None:
    """Configure application dependencies."""

    # Infrastructure services
    container.register(DeepSeekClient, lambda c: DeepSeekClient(), Scope.SINGLETON)
    container.register(CacheService, lambda c: CacheService(), Scope.SINGLETON)
    container.register(RagService, lambda c: RagService(), Scope.SINGLETON)

    # Domain services
    container.register(
        MemoryService,
        lambda c: MemoryService(llm_client=c.resolve(DeepSeekClient)),
        Scope.SINGLETON,
    )

    # Event bus (optional)
    if settings.EVENT_BUS_ENABLED:
        if settings.EVENT_BUS_BACKEND.lower() == "redis":
            container.register(
                EventBus,
                lambda c: RedisStreamsEventBus(settings.REDIS_URL, settings.EVENT_BUS_STREAM_PREFIX),
                Scope.SINGLETON,
            )
        else:
            container.register(
                EventBus,
                lambda c: InMemoryEventBus(),
                Scope.SINGLETON,
            )

    # Coherence services
    container.register(
        ChekhovTracker,
        lambda c: ChekhovTracker(
            llm_client=c.resolve(DeepSeekClient),
            memory_service=c.resolve(MemoryService),
        ),
        Scope.SINGLETON,
    )
    container.register(
        CharacterDriftDetector,
        lambda c: CharacterDriftDetector(
            llm_client=c.resolve(DeepSeekClient),
            memory_service=c.resolve(MemoryService),
        ),
        Scope.SINGLETON,
    )
    container.register(
        VoiceConsistencyAnalyzer,
        lambda c: VoiceConsistencyAnalyzer(
            memory_service=c.resolve(MemoryService)
        ),
        Scope.SINGLETON,
    )
    container.register(
        POVValidator,
        lambda c: POVValidator(llm_client=c.resolve(DeepSeekClient)),
        Scope.SINGLETON,
    )


def get_configured_container() -> Container:
    """Return a configured container instance."""
    container = Container.get_instance()
    if not container.is_registered(DeepSeekClient):
        configure_container(container)
    return container
