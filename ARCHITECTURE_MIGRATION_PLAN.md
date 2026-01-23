# Plan d'Implémentation : Architecture Event-Driven Modular Monolith pour NovellaForge

## Statut d'Implémentation

| Phase | Statut | Notes |
|-------|--------|-------|
| **Phase 1** : Shared Kernel | ⬜ Non commencé | Fondations event-driven |
| **Phase 2** : DI Container | ⬜ Non commencé | Injection de dépendances |
| **Phase 3** : Bounded Contexts | ⬜ Non commencé | Modules domaine (Writing, Memory, Coherence, Project) |
| **Phase 4** : CQRS | ⬜ Non commencé | Séparation lecture/écriture |
| **Phase 5** : Event Bus | ⬜ Non commencé | Redis Streams |
| **Phase 6** : Résilience | ⬜ Non commencé | Circuit breakers, retry |
| **Phase 7** : Observabilité | ⬜ Non commencé | Prometheus, Structlog, OpenTelemetry |
| **Phase 8** : Async Neo4j | ⬜ Non commencé | Migration driver async |

### Légende
- ⬜ Non commencé
- 🟡 En cours
- ✅ Terminé

---

## Résumé Exécutif

Ce plan détaille la migration incrémentale de NovellaForge vers une architecture Event-Driven Modular Monolith. Chaque phase est indépendamment déployable avec une stratégie de rollback claire.

**Durée totale estimée** : 8 phases sur 17 semaines
**Risque global** : Modéré (atténué par l'approche incrémentale)

---

## État Actuel - Problèmes Identifiés

| Problème | Impact | Fichiers Concernés |
|----------|--------|-------------------|
| Pas d'injection de dépendances | Couplage fort, tests difficiles | `writing_pipeline.py`, tous les services |
| Neo4j synchrone dans code async | Blocage du thread pool | `memory_service.py` |
| Gestion d'erreurs silencieuse | Debugging difficile | `cache_service.py`, `memory_service.py` |
| Duplication d'instances | Mémoire gaspillée, incohérences | Tous les services coherence/ |
| Pas de coordination transactionnelle | Incohérences de données | DB + Neo4j + Cache |
| Pas d'Event-Driven | Couplage synchrone fort | Toute l'architecture |

---

## Phase 1 : Shared Kernel et Domain Events (Semaines 1-2)

### Objectif
Établir les fondations pour l'architecture event-driven sans modifier le comportement existant.

### Fichiers à Créer

```
backend/app/shared_kernel/
├── __init__.py
├── domain_events.py      # Classes de base pour les événements
├── value_objects.py      # ProjectId, ChapterId, WordCount, etc.
├── exceptions.py         # Hiérarchie d'exceptions domaine
└── result.py             # Pattern Result[T, E] pour erreurs explicites
```

### Implémentation Détaillée

#### 1.1 Domain Events (`shared_kernel/domain_events.py`)

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from abc import ABC

@dataclass(frozen=True)
class DomainEvent(ABC):
    """Classe de base pour tous les événements du domaine."""
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.__class__.__name__,
            "occurred_at": self.occurred_at.isoformat(),
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
            "payload": self._payload_dict()
        }

    def _payload_dict(self) -> Dict[str, Any]:
        """Override dans les sous-classes pour le payload spécifique."""
        return {}

# Événements du domaine Writing
@dataclass(frozen=True)
class ChapterGenerationStartedEvent(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    chapter_index: int = 0
    user_id: UUID = field(default_factory=uuid4)

@dataclass(frozen=True)
class ChapterGeneratedEvent(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    chapter_id: UUID = field(default_factory=uuid4)
    chapter_index: int = 0
    word_count: int = 0
    content_hash: str = ""

@dataclass(frozen=True)
class ChapterApprovedEvent(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    chapter_id: UUID = field(default_factory=uuid4)
    chapter_index: int = 0
    summary: str = ""

# Événements du domaine Coherence
@dataclass(frozen=True)
class CoherenceValidatedEvent(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    chapter_id: UUID = field(default_factory=uuid4)
    score: float = 0.0
    issues_count: int = 0
    blocking_issues: bool = False

@dataclass(frozen=True)
class ContradictionDetectedEvent(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    chapter_id: UUID = field(default_factory=uuid4)
    contradiction_type: str = ""
    severity: str = "warning"  # "blocking", "warning", "info"
    description: str = ""

# Événements du domaine Memory
@dataclass(frozen=True)
class FactsExtractedEvent(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    chapter_index: int = 0
    characters_count: int = 0
    locations_count: int = 0
    events_count: int = 0

@dataclass(frozen=True)
class MemoryUpdatedEvent(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    memory_type: str = ""  # "neo4j", "chromadb", "recursive"
    entities_updated: int = 0
```

#### 1.2 Value Objects (`shared_kernel/value_objects.py`)

```python
from dataclasses import dataclass
from uuid import UUID
from typing import Optional

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

@dataclass(frozen=True)
class WordCount:
    value: int

    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Word count cannot be negative")

    def is_within_range(self, min_words: int, max_words: int) -> bool:
        return min_words <= self.value <= max_words

@dataclass(frozen=True)
class CoherenceScore:
    value: float

    def __post_init__(self):
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
```

#### 1.3 Exceptions Domaine (`shared_kernel/exceptions.py`)

```python
from typing import Optional, Dict, Any

class DomainException(Exception):
    """Exception de base pour toutes les erreurs du domaine."""
    def __init__(self, message: str, code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}

class ValidationError(DomainException):
    """Erreur de validation des données."""
    pass

class EntityNotFoundError(DomainException):
    """Entité non trouvée."""
    pass

class CoherenceError(DomainException):
    """Erreur de cohérence narrative."""
    pass

class ExternalServiceError(DomainException):
    """Erreur d'un service externe (LLM, Neo4j, etc.)."""
    pass

class CircuitOpenError(ExternalServiceError):
    """Circuit breaker ouvert."""
    pass

class ConcurrencyError(DomainException):
    """Erreur de concurrence (modification simultanée)."""
    pass
```

#### 1.4 Result Pattern (`shared_kernel/result.py`)

```python
from dataclasses import dataclass
from typing import Generic, TypeVar, Optional, Callable

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

@dataclass
class Result(Generic[T, E]):
    """Conteneur pour résultat ou erreur explicite."""
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
        return self._value

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
```

### Tests Phase 1

```python
# backend/tests/unit/shared_kernel/test_domain_events.py
import pytest
from app.shared_kernel.domain_events import ChapterGeneratedEvent
from uuid import uuid4

def test_chapter_generated_event_creation():
    event = ChapterGeneratedEvent(
        project_id=uuid4(),
        chapter_id=uuid4(),
        chapter_index=1,
        word_count=2500,
        content_hash="abc123"
    )
    assert event.event_id is not None
    assert event.occurred_at is not None

def test_event_to_dict():
    event = ChapterGeneratedEvent(
        project_id=uuid4(),
        chapter_id=uuid4(),
        chapter_index=1,
        word_count=2500,
        content_hash="abc123"
    )
    data = event.to_dict()
    assert "event_type" in data
    assert data["event_type"] == "ChapterGeneratedEvent"
```

### Vérification Phase 1
- [ ] Tous les tests existants passent (aucune modification du code existant)
- [ ] Nouveaux tests du shared_kernel passent
- [ ] Import possible depuis `app.shared_kernel`

### Rollback Phase 1
Supprimer le dossier `backend/app/shared_kernel/`. Aucun code existant n'est modifié.

---

## Phase 2 : Conteneur d'Injection de Dépendances (Semaines 3-4)

### Objectif
Introduire un conteneur DI pour découpler les services sans casser le code existant.

### Fichiers à Créer

```
backend/app/infrastructure/
├── __init__.py
└── di/
    ├── __init__.py
    ├── container.py      # Conteneur principal
    ├── providers.py      # Factories pour les services
    └── scopes.py         # Singleton, Scoped, Transient
```

### Fichiers à Modifier

| Fichier | Modification |
|---------|--------------|
| `backend/app/main.py` | Initialiser le conteneur dans le lifespan |
| `backend/app/services/memory_service.py` | Accepter les dépendances en paramètres (optionnel) |
| `backend/app/services/llm_client.py` | Accepter les dépendances en paramètres (optionnel) |
| `backend/app/services/coherence/*.py` | Pattern dual (DI ou auto-instanciation) |

### Implémentation Détaillée

#### 2.1 Conteneur DI (`infrastructure/di/container.py`)

```python
from typing import TypeVar, Type, Dict, Callable, Any, Optional
from enum import Enum
import threading
from contextlib import contextmanager

T = TypeVar('T')

class Scope(Enum):
    SINGLETON = "singleton"
    SCOPED = "scoped"
    TRANSIENT = "transient"

class Registration:
    def __init__(self, factory: Callable[..., Any], scope: Scope):
        self.factory = factory
        self.scope = scope

class Container:
    _instance: Optional["Container"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._registrations: Dict[Type, Registration] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_instances: Dict[Type, Any] = {}
        self._in_scope = False

    @classmethod
    def get_instance(cls) -> "Container":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Pour les tests uniquement."""
        cls._instance = None

    def register(
        self,
        interface: Type[T],
        factory: Callable[..., T],
        scope: Scope = Scope.SINGLETON
    ) -> None:
        self._registrations[interface] = Registration(factory, scope)

    def resolve(self, interface: Type[T]) -> T:
        if interface not in self._registrations:
            raise KeyError(f"No registration found for {interface.__name__}")

        registration = self._registrations[interface]

        if registration.scope == Scope.SINGLETON:
            if interface not in self._singletons:
                self._singletons[interface] = registration.factory(self)
            return self._singletons[interface]

        elif registration.scope == Scope.SCOPED:
            if not self._in_scope:
                raise RuntimeError("Cannot resolve scoped service outside of scope")
            if interface not in self._scoped_instances:
                self._scoped_instances[interface] = registration.factory(self)
            return self._scoped_instances[interface]

        else:  # TRANSIENT
            return registration.factory(self)

    @contextmanager
    def create_scope(self):
        """Crée un scope pour les services scoped (par requête)."""
        self._in_scope = True
        self._scoped_instances = {}
        try:
            yield self
        finally:
            self._scoped_instances = {}
            self._in_scope = False

    def is_registered(self, interface: Type) -> bool:
        return interface in self._registrations
```

#### 2.2 Providers (`infrastructure/di/providers.py`)

```python
from app.infrastructure.di.container import Container, Scope
from app.services.llm_client import DeepSeekClient
from app.services.memory_service import MemoryService
from app.services.rag_service import RagService
from app.services.cache_service import CacheService
from app.services.coherence.consistency_analyst import ConsistencyAnalyst
from app.services.coherence.chekhov_tracker import ChekhovTracker
from app.services.coherence.character_drift import CharacterDriftDetector
from app.services.coherence.voice_analyzer import VoiceConsistencyAnalyzer

def configure_container(container: Container) -> None:
    """Configure toutes les dépendances de l'application."""

    # === Services Infrastructure (Singletons) ===
    container.register(DeepSeekClient, lambda c: DeepSeekClient(), Scope.SINGLETON)
    container.register(CacheService, lambda c: CacheService(), Scope.SINGLETON)
    container.register(RagService, lambda c: RagService(), Scope.SINGLETON)

    # === Services Domaine (Singletons avec dépendances) ===
    container.register(
        MemoryService,
        lambda c: MemoryService(llm_client=c.resolve(DeepSeekClient)),
        Scope.SINGLETON
    )

    # === Services Cohérence (Singletons) ===
    container.register(
        ConsistencyAnalyst,
        lambda c: ConsistencyAnalyst(memory_service=c.resolve(MemoryService)),
        Scope.SINGLETON
    )
    container.register(
        ChekhovTracker,
        lambda c: ChekhovTracker(
            llm_client=c.resolve(DeepSeekClient),
            memory_service=c.resolve(MemoryService)
        ),
        Scope.SINGLETON
    )
    container.register(
        CharacterDriftDetector,
        lambda c: CharacterDriftDetector(
            llm_client=c.resolve(DeepSeekClient),
            memory_service=c.resolve(MemoryService)
        ),
        Scope.SINGLETON
    )
    container.register(
        VoiceConsistencyAnalyzer,
        lambda c: VoiceConsistencyAnalyzer(memory_service=c.resolve(MemoryService)),
        Scope.SINGLETON
    )

def get_configured_container() -> Container:
    """Retourne le conteneur configuré."""
    container = Container.get_instance()
    if not container.is_registered(DeepSeekClient):
        configure_container(container)
    return container
```

#### 2.3 Modification Services - Pattern Dual

```python
# backend/app/services/memory_service.py (modifié)
from typing import Optional, Any

class MemoryService:
    def __init__(
        self,
        llm_client: Optional["DeepSeekClient"] = None,
        neo4j_driver: Optional[Any] = None,
        chroma_client: Optional[Any] = None,
    ) -> None:
        # Pattern dual : accepte DI ou auto-instancie
        if llm_client is not None:
            self.llm_client = llm_client
        else:
            from app.services.llm_client import DeepSeekClient
            self.llm_client = DeepSeekClient()

        self.neo4j_driver = neo4j_driver or self._init_neo4j()
        self.chroma_client = chroma_client or self._init_chroma()
        # ... reste du code inchangé
```

#### 2.4 Intégration FastAPI (`main.py`)

```python
# backend/app/main.py (modifié)
from contextlib import asynccontextmanager
from app.infrastructure.di.providers import get_configured_container, Container

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    container = get_configured_container()
    app.state.container = container

    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    Container.reset()

# Dependency pour les endpoints
def get_container() -> Container:
    return Container.get_instance()
```

### Tests Phase 2

```python
# backend/tests/unit/infrastructure/test_container.py
import pytest
from app.infrastructure.di.container import Container, Scope

class IService:
    pass

class ConcreteService(IService):
    pass

def test_singleton_returns_same_instance():
    container = Container()
    container.register(IService, lambda c: ConcreteService(), Scope.SINGLETON)
    instance1 = container.resolve(IService)
    instance2 = container.resolve(IService)
    assert instance1 is instance2

def test_transient_returns_new_instance():
    container = Container()
    container.register(IService, lambda c: ConcreteService(), Scope.TRANSIENT)
    instance1 = container.resolve(IService)
    instance2 = container.resolve(IService)
    assert instance1 is not instance2
```

### Vérification Phase 2
- [ ] Tous les tests existants passent
- [ ] Services fonctionnent avec et sans DI (backward compatible)
- [ ] Container correctement initialisé au démarrage
- [ ] `docker-compose up` fonctionne sans erreur

### Rollback Phase 2
1. Supprimer `backend/app/infrastructure/di/`
2. Retirer l'initialisation du container de `main.py`
3. Les services continuent de fonctionner avec auto-instanciation

---

## Phase 3 : Bounded Contexts - Modules Domaine (Semaines 5-7)

### Objectif
Organiser le code en contextes bornés avec des interfaces claires entre domaines.

### Structure Cible

```
backend/app/domains/
├── __init__.py
├── writing/
│   ├── __init__.py
│   ├── domain/
│   │   ├── entities.py       # Chapter, Beat, Scene
│   │   ├── value_objects.py  # WritingState, GenerationConfig
│   │   ├── events.py         # Réexporte depuis shared_kernel
│   │   └── services.py       # Services domaine (logique métier pure)
│   ├── application/
│   │   ├── commands/
│   │   │   ├── generate_chapter.py
│   │   │   └── approve_chapter.py
│   │   ├── queries/
│   │   │   └── get_chapter_status.py
│   │   └── handlers/
│   │       └── event_handlers.py
│   └── infrastructure/
│       └── repositories.py
│
├── memory/
│   ├── domain/
│   │   ├── entities.py       # ContinuityFact, CharacterState
│   │   └── services.py       # FactExtraction
│   ├── application/
│   │   └── commands/
│   └── infrastructure/
│       ├── neo4j_repository.py
│       └── chroma_repository.py
│
├── coherence/
│   ├── domain/
│   │   ├── entities.py       # ValidationResult, Contradiction
│   │   └── validators/       # Déplacé depuis services/coherence
│   ├── application/
│   │   └── commands/
│   └── infrastructure/
│
└── project/
    ├── domain/
    │   ├── entities.py       # Project, StoryBible
    │   └── events.py
    ├── application/
    └── infrastructure/
        └── repositories.py
```

### Implémentation Détaillée

#### 3.1 Writing Domain - Entities

```python
# backend/app/domains/writing/domain/entities.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from enum import Enum

from app.shared_kernel.domain_events import DomainEvent, ChapterGeneratedEvent, ChapterApprovedEvent

class ChapterStatus(Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"

@dataclass
class Chapter:
    """Aggregate Root pour un chapitre."""
    id: UUID
    project_id: UUID
    index: int
    title: str
    content: str
    status: ChapterStatus
    word_count: int
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    _events: List[DomainEvent] = field(default_factory=list, repr=False)

    @classmethod
    def create(cls, project_id: UUID, index: int, title: str, content: str) -> "Chapter":
        """Factory method pour créer un nouveau chapitre."""
        now = datetime.now(timezone.utc)
        chapter = cls(
            id=uuid4(),
            project_id=project_id,
            index=index,
            title=title,
            content=content,
            status=ChapterStatus.DRAFT,
            word_count=len(content.split()),
            created_at=now,
            updated_at=now,
        )
        chapter._events.append(
            ChapterGeneratedEvent(
                project_id=project_id,
                chapter_id=chapter.id,
                chapter_index=index,
                word_count=chapter.word_count,
                content_hash=str(hash(content)),
            )
        )
        return chapter

    def approve(self, summary: str) -> None:
        if self.status == ChapterStatus.APPROVED:
            raise ValueError("Chapter already approved")
        self.status = ChapterStatus.APPROVED
        self.metadata["summary"] = summary
        self.updated_at = datetime.now(timezone.utc)
        self._events.append(
            ChapterApprovedEvent(
                project_id=self.project_id,
                chapter_id=self.id,
                chapter_index=self.index,
                summary=summary,
            )
        )

    def collect_events(self) -> List[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events
```

#### 3.2 Writing Domain - Commands

```python
# backend/app/domains/writing/application/commands/generate_chapter.py
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

@dataclass(frozen=True)
class GenerateChapterCommand:
    project_id: UUID
    user_id: UUID
    chapter_index: Optional[int] = None
    instruction: Optional[str] = None
    target_word_count: Optional[int] = None
    use_rag: bool = True
    use_memory: bool = True

@dataclass(frozen=True)
class ApproveChapterCommand:
    chapter_id: UUID
    user_id: UUID
    summary: Optional[str] = None
```

#### 3.3 Migration Progressive avec Feature Flag

```python
# backend/app/api/v1/endpoints/writing.py (modifié)
# Feature flag pour migration progressive
USE_NEW_ARCHITECTURE = settings.FEATURE_FLAG_NEW_ARCHITECTURE

@router.post("/generate-chapter")
async def generate_chapter(request: ChapterGenerationRequest, ...):
    if USE_NEW_ARCHITECTURE:
        # Nouvelle architecture avec CQRS
        handler = container.resolve(GenerateChapterHandler)
        command = GenerateChapterCommand(...)
        result = await handler.handle(command)
        return ChapterGenerationResponse(**result)
    else:
        # Ancienne architecture - WritingPipeline direct
        pipeline = WritingPipeline(db)
        # ... code existant
```

### Vérification Phase 3
- [ ] Feature flag permet de basculer entre architectures
- [ ] API retourne les mêmes résultats dans les deux modes
- [ ] Tous les tests existants passent

### Rollback Phase 3
Désactiver le feature flag (`FEATURE_FLAG_NEW_ARCHITECTURE=false`)

---

## Phase 4 : CQRS - Séparation Lecture/Écriture (Semaines 8-9)

### Objectif
Séparer les chemins de lecture et d'écriture pour une meilleure scalabilité.

### Fichiers à Créer

```
backend/app/infrastructure/cqrs/
├── __init__.py
├── command_bus.py    # Dispatch des commandes
├── query_bus.py      # Dispatch des requêtes
├── mediator.py       # Interface unifiée
└── decorators.py     # @command_handler, @query_handler
```

### Implémentation

#### 4.1 Command Bus

```python
# backend/app/infrastructure/cqrs/command_bus.py
from typing import TypeVar, Generic, Dict, Type, Any
from abc import ABC, abstractmethod

TCommand = TypeVar('TCommand')
TResult = TypeVar('TResult')

class Command(ABC):
    """Marqueur pour les commandes."""
    pass

class CommandHandler(ABC, Generic[TCommand, TResult]):
    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        pass

class CommandBus:
    def __init__(self):
        self._handlers: Dict[Type[Command], CommandHandler] = {}

    def register(self, command_type: Type[TCommand], handler: CommandHandler) -> None:
        self._handlers[command_type] = handler

    async def dispatch(self, command: Command) -> Any:
        command_type = type(command)
        if command_type not in self._handlers:
            raise ValueError(f"No handler registered for {command_type.__name__}")
        return await self._handlers[command_type].handle(command)
```

#### 4.2 Mediator

```python
# backend/app/infrastructure/cqrs/mediator.py
from typing import Union, Any
from .command_bus import CommandBus, Command
from .query_bus import QueryBus, Query

class Mediator:
    def __init__(self, command_bus: CommandBus, query_bus: QueryBus):
        self._command_bus = command_bus
        self._query_bus = query_bus

    async def send(self, request: Union[Command, Query]) -> Any:
        if isinstance(request, Command):
            return await self._command_bus.dispatch(request)
        elif isinstance(request, Query):
            return await self._query_bus.dispatch(request)
        raise ValueError(f"Unknown request type: {type(request)}")
```

### Vérification Phase 4
- [ ] Mediator correctement injecté dans les endpoints
- [ ] Commandes et queries dispatched correctement

---

## Phase 5 : Event Bus avec Redis Streams (Semaines 10-11)

### Objectif
Implémenter la communication event-driven entre bounded contexts.

### Fichiers à Créer

```
backend/app/infrastructure/event_bus/
├── __init__.py
├── interfaces.py         # EventBus ABC
├── redis_streams.py      # Implémentation Redis Streams
├── in_memory.py          # Pour les tests
├── handlers.py           # Registry des handlers
└── consumer.py           # Worker de consommation
```

### Implémentation

```python
# backend/app/infrastructure/event_bus/redis_streams.py
import json
import asyncio
from typing import Dict, List, Type, Callable, Any
from datetime import datetime, timezone
import redis.asyncio as redis

from app.shared_kernel.domain_events import DomainEvent
from .interfaces import EventBus, EventHandler

class RedisStreamsEventBus(EventBus):
    def __init__(self, redis_url: str, stream_prefix: str = "novellaforge:events"):
        self._redis = redis.from_url(redis_url)
        self._stream_prefix = stream_prefix
        self._handlers: Dict[str, List[EventHandler]] = {}

    async def publish(self, event: DomainEvent) -> str:
        stream_name = f"{self._stream_prefix}:{type(event).__name__}"
        event_data = {
            "event_id": str(event.event_id),
            "event_type": type(event).__name__,
            "payload": json.dumps(event.to_dict(), default=str),
        }
        return await self._redis.xadd(stream_name, event_data)

    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        type_name = event_type.__name__
        if type_name not in self._handlers:
            self._handlers[type_name] = []
        self._handlers[type_name].append(handler)
```

### Vérification Phase 5
- [ ] Événements publiés dans Redis Streams
- [ ] Handlers exécutés correctement
- [ ] Pas de perte d'événements

---

## Phase 6 : Circuit Breakers et Résilience (Semaines 12-13)

### Objectif
Ajouter la tolérance aux pannes pour les appels aux services externes.

### Fichiers à Créer

```
backend/app/infrastructure/resilience/
├── __init__.py
├── circuit_breaker.py
├── retry.py
├── timeout.py
└── decorators.py
```

### Implémentation

```python
# backend/app/infrastructure/resilience/circuit_breaker.py
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, TypeVar, Optional
import asyncio

T = TypeVar('T')

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    recovery_timeout: timedelta = timedelta(seconds=30)

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: Optional[datetime] = field(default=None, init=False)

    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
            else:
                from app.shared_kernel.exceptions import CircuitOpenError
                raise CircuitOpenError(f"Circuit {self.name} is open", code="CIRCUIT_OPEN")

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = await asyncio.to_thread(func, *args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        if self._last_failure_time is None:
            return False
        return datetime.now(timezone.utc) - self._last_failure_time >= self.recovery_timeout

    def _on_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = datetime.now(timezone.utc)
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
```

### Vérification Phase 6
- [ ] Circuit breakers se déclenchent correctement
- [ ] Dégradation gracieuse fonctionne

---

## Phase 7 : Couche d'Observabilité (Semaines 14-15)

### Objectif
Ajouter logs structurés, métriques Prometheus, et tracing distribué.

### Fichiers à Créer

```
backend/app/infrastructure/observability/
├── __init__.py
├── metrics.py            # Métriques Prometheus
├── tracing.py            # OpenTelemetry
├── structured_logging.py # Structlog
└── middleware.py         # Middleware FastAPI
```

### Implémentation

```python
# backend/app/infrastructure/observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge

CHAPTER_GENERATION_TOTAL = Counter(
    "novellaforge_chapter_generation_total",
    "Total des générations de chapitres",
    ["project_id", "status"]
)

CHAPTER_GENERATION_DURATION = Histogram(
    "novellaforge_chapter_generation_duration_seconds",
    "Durée de génération de chapitre",
    ["stage"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

CIRCUIT_BREAKER_STATE = Gauge(
    "novellaforge_circuit_breaker_state",
    "État du circuit breaker",
    ["name"]
)
```

### Vérification Phase 7
- [ ] Endpoint `/metrics` accessible
- [ ] Logs en JSON structuré
- [ ] Métriques collectées

---

## Phase 8 : Async Neo4j et Intégration Finale (Semaines 16-17)

### Objectif
Convertir Neo4j en driver async et finaliser l'intégration.

### Fichiers à Modifier

| Fichier | Modification |
|---------|--------------|
| `backend/app/services/memory_service.py` | Migrer vers neo4j async |
| `backend/app/infrastructure/neo4j_client.py` | Nouveau client async |
| `requirements.txt` | Ajouter `neo4j>=5.0.0` |

### Implémentation

```python
# backend/app/infrastructure/neo4j_client.py
from neo4j import AsyncGraphDatabase
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager

class AsyncNeo4jClient:
    def __init__(self, uri: str, user: str, password: str, database: Optional[str] = None):
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self._database = database

    @asynccontextmanager
    async def session(self):
        session = self._driver.session(database=self._database)
        try:
            yield session
        finally:
            await session.close()

    async def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict]:
        async with self.session() as session:
            result = await session.run(query, parameters or {})
            return [record.data() async for record in result]

    async def close(self):
        await self._driver.close()
```

### Vérification Finale
- [ ] Tous les tests passent
- [ ] Performance améliorée (Neo4j async)
- [ ] Événements publiés et consommés correctement
- [ ] Circuit breakers fonctionnels
- [ ] Métriques collectées
- [ ] Logs structurés

---

## Résumé des Phases

| Phase | Durée | Fichiers Créés | Fichiers Modifiés | Risque |
|-------|-------|----------------|-------------------|--------|
| 1. Shared Kernel | 2 sem | 4 | 0 | Faible |
| 2. DI Container | 2 sem | 4 | 5 | Faible |
| 3. Bounded Contexts | 3 sem | ~20 | 3 | Moyen |
| 4. CQRS | 2 sem | 4 | 5 | Moyen |
| 5. Event Bus | 2 sem | 5 | 3 | Moyen |
| 6. Résilience | 2 sem | 4 | 4 | Faible |
| 7. Observabilité | 2 sem | 4 | 2 | Faible |
| 8. Async Neo4j | 2 sem | 1 | 3 | Moyen |

---

## Prérequis Techniques

### Dépendances à Ajouter (`requirements.txt`)

```
# Phase 5 - Event Bus
redis>=5.0.0

# Phase 7 - Observabilité
prometheus-client>=0.17.0
structlog>=23.0.0
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-instrumentation-fastapi>=0.41b0

# Phase 8 - Async Neo4j
neo4j>=5.0.0
```

---

## Vérification Globale

```bash
# À chaque phase
pytest backend/tests/ -v
docker-compose up -d
curl http://localhost:8002/health
curl http://localhost:8002/metrics  # Phase 7+
```
