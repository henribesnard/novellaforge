# Plan d'Implémentation - Cohérence Narrative NovellaForge

> **Document destiné aux agents IA pour l'implémentation autonome des améliorations de cohérence narrative.**

---

## 📋 Table des Matières

1. [Vue d'Ensemble](#1-vue-densemble)
2. [Prérequis et Conventions](#2-prérequis-et-conventions)
3. [Phase 1 : Fondations](#3-phase-1--fondations)
4. [Phase 2 : Mémoire Avancée](#4-phase-2--mémoire-avancée)
5. [Phase 3 : Qualité Narrative](#5-phase-3--qualité-narrative)
6. [Phase 4 : Features Avancées](#6-phase-4--features-avancées)
7. [Tests et Validation](#7-tests-et-validation)
8. [Migrations de Base de Données](#8-migrations-de-base-de-données)

---

## 1. Vue d'Ensemble

### 1.1 Architecture Existante

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│                    Next.js 15 + TypeScript                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND API                              │
│                    FastAPI + Python 3.11                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Agents    │  │  Pipeline   │  │       Services          │  │
│  │ - Narrative │  │  LangGraph  │  │ - MemoryService         │  │
│  │ - Consist.  │  │  - plan     │  │ - RagService            │  │
│  │ - Character │  │  - write    │  │ - ContextService        │  │
│  │ - Style     │  │  - critic   │  │ - CacheService          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
   PostgreSQL       Neo4j        ChromaDB        Qdrant
   (Projets)       (Graphe)      (Style)         (RAG)
                      │
                   Redis
                  (Cache)
```

### 1.2 Fichiers Clés à Modifier/Créer

| Fichier | Action | Description |
|---------|--------|-------------|
| `backend/app/services/memory_service.py` | MODIFIER | Ajouter méthodes pyramide, objets, localisation |
| `backend/app/services/writing_pipeline.py` | MODIFIER | Intégrer ConsistencyAnalyst, nouvelles validations |
| `backend/app/services/agents/consistency_analyst.py` | MODIFIER | Ajouter filtrage mystères intentionnels |
| `backend/app/services/coherence/` | CRÉER | Nouveau package pour modules spécialisés |
| `backend/app/services/coherence/recursive_memory.py` | CRÉER | Gestion mémoire pyramidale |
| `backend/app/services/coherence/chekhov_tracker.py` | CRÉER | Tracking des éléments narratifs |
| `backend/app/services/coherence/voice_analyzer.py` | CRÉER | Analyse constance de voix |
| `backend/app/services/coherence/character_drift.py` | CRÉER | Détection dérive personnages |
| `backend/app/services/coherence/pov_validator.py` | CRÉER | Validation point de vue |
| `backend/app/services/coherence/semantic_validator.py` | CRÉER | Validation par embeddings |
| `backend/app/tasks/coherence_tasks.py` | CRÉER | Tâches Celery de cohérence |
| `backend/app/schemas/coherence.py` | CRÉER | Schémas Pydantic cohérence |
| `backend/app/api/v1/endpoints/coherence.py` | CRÉER | Endpoints API cohérence |

---

## 2. Prérequis et Conventions

### 2.1 Conventions de Code

```python
# Style de documentation
"""
Module description.

This module handles X functionality for Y purpose.
"""

# Imports ordonnés
from __future__ import annotations  # Toujours en premier

# Standard library
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

# Third-party
from pydantic import BaseModel, Field

# Local
from app.core.config import settings
from app.services.llm_client import DeepSeekClient
from app.services.memory_service import MemoryService

# Logger
logger = logging.getLogger(__name__)
```

### 2.2 Structure des Services

```python
class NewService:
    """Service description."""
    
    def __init__(self) -> None:
        """Initialize dependencies."""
        self.llm_client = DeepSeekClient()
        self.memory_service = MemoryService()
    
    async def public_method(
        self, 
        required_param: str,
        optional_param: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Public method description.
        
        Args:
            required_param: Description of required param.
            optional_param: Description of optional param.
            
        Returns:
            Dictionary containing result keys.
            
        Raises:
            ValueError: If required_param is empty.
        """
        pass
    
    def _private_helper(self, data: str) -> str:
        """Private helper method."""
        pass
```

### 2.3 Variables d'Environnement à Ajouter

```env
# backend/.env.example - Ajouter ces variables

# Coherence Settings
RECURSIVE_MEMORY_ENABLED=true
RECURSIVE_MEMORY_RECENT_CHAPTERS=5
RECURSIVE_MEMORY_ARC_SUMMARY_WORDS=500
RECURSIVE_MEMORY_GLOBAL_SYNOPSIS_WORDS=1000

CHEKHOV_TRACKER_ENABLED=true
CHEKHOV_MAX_UNRESOLVED_CHAPTERS=15
CHEKHOV_URGENCY_THRESHOLD=7

VOICE_ANALYZER_ENABLED=true
VOICE_CONSISTENCY_THRESHOLD=0.75
VOICE_MIN_DIALOGUES_FOR_ANALYSIS=5

CHARACTER_DRIFT_ENABLED=true
CHARACTER_DRIFT_THRESHOLD=0.6

POV_VALIDATOR_ENABLED=true
POV_DEFAULT_TYPE=limited

SEMANTIC_VALIDATOR_ENABLED=true
SEMANTIC_CONFLICT_THRESHOLD=0.8

FACT_PROMOTION_THRESHOLD=3
FACT_PROMOTION_SCHEDULE_HOURS=24
```

---

## 3. Phase 1 : Fondations

### 3.1 TÂCHE 1.1 : Unification Pipeline/ConsistencyAnalyst

**Objectif** : Remplacer la validation inline du `WritingPipeline` par l'appel au `ConsistencyAnalyst`.

**Fichier** : `backend/app/services/writing_pipeline.py`

**Étapes** :

1. **Importer ConsistencyAnalyst** :
```python
# Ligne ~30, après les imports existants
from app.services.agents.consistency_analyst import ConsistencyAnalyst
```

2. **Ajouter attribut dans __init__** :
```python
# Dans WritingPipeline.__init__
def __init__(self, db: AsyncSession):
    self.db = db
    self.llm_client = DeepSeekClient()
    self.rag_service = RagService()
    self.memory_service = MemoryService()
    self.cache_service = CacheService()
    self.consistency_analyst = ConsistencyAnalyst()  # AJOUTER
```

3. **Refactorer validate_continuity** :
```python
async def validate_continuity(self, state: NovelState) -> Dict[str, Any]:
    """Validate continuity using ConsistencyAnalyst."""
    start = time.perf_counter()
    chapter_text = state.get("chapter_text", "")
    
    if not chapter_text:
        return {
            "continuity_validation": {
                "severe_issues": [{"type": "missing_content", "detail": "No chapter text."}],
                "minor_issues": [],
                "coherence_score": 0.0,
                "blocking": False,
            }
        }
    
    # Préparer les données pour ConsistencyAnalyst
    project_context = state.get("project_context") or {}
    project_metadata = project_context.get("metadata") or {}
    story_bible = project_metadata.get("story_bible") or {}
    
    # Récupérer les chapitres précédents
    previous_chapters = await self._get_previous_chapter_texts(
        state.get("project_id"),
        state.get("chapter_index"),
        limit=5
    )
    
    # Appeler ConsistencyAnalyst
    analyst_result = await self.consistency_analyst.execute(
        task_data={
            "action": "analyze_chapter",
            "chapter_text": chapter_text,
            "memory_context": state.get("memory_context", ""),
            "story_bible": story_bible,
            "previous_chapters": previous_chapters,
        },
        context=project_context,
    )
    
    # Transformer le résultat au format attendu par le pipeline
    analysis = analyst_result.get("analysis") or {}
    validation = self._transform_analyst_result(analysis, state)
    
    # Validation du graphe Neo4j (existante)
    graph_payload = await self._validate_graph_consistency(state)
    validation["graph_issues"] = graph_payload.get("graph_issues", [])
    
    # Validation des points d'intrigue (existante)
    plan_entry = state.get("current_plan") or {}
    plot_validation = self._validate_plot_points(chapter_text, plan_entry)
    validation["plot_point_validation"] = plot_validation
    
    self._log_duration("validate_continuity", start)
    return {"continuity_validation": validation, "continuity_alerts": self._build_continuity_alerts(validation)}

def _transform_analyst_result(
    self, analysis: Dict[str, Any], state: NovelState
) -> Dict[str, Any]:
    """Transform ConsistencyAnalyst output to pipeline format."""
    severe_issues = []
    minor_issues = []
    
    # Contradictions
    for contradiction in analysis.get("contradictions", []):
        severity = contradiction.get("severity", "medium").lower()
        issue = {
            "type": contradiction.get("type", "contradiction"),
            "detail": contradiction.get("description", ""),
            "severity": "blocking" if severity == "critical" else severity,
            "source": "consistency_analyst",
            "suggested_fix": contradiction.get("suggested_fix", ""),
        }
        if severity in ("critical", "high"):
            severe_issues.append(issue)
        else:
            minor_issues.append(issue)
    
    # Timeline issues
    for timeline_issue in analysis.get("timeline_issues", []):
        severity = timeline_issue.get("severity", "medium").lower()
        issue = {
            "type": "timeline",
            "detail": timeline_issue.get("issue", ""),
            "severity": "blocking" if severity == "critical" else severity,
            "source": "consistency_analyst",
            "suggested_fix": timeline_issue.get("suggested_fix", ""),
        }
        if severity in ("critical", "high"):
            severe_issues.append(issue)
        else:
            minor_issues.append(issue)
    
    # Character inconsistencies
    for char_issue in analysis.get("character_inconsistencies", []):
        severity = char_issue.get("severity", "medium").lower()
        issue = {
            "type": "character",
            "detail": f"{char_issue.get('character', 'Unknown')}: {char_issue.get('issue', '')}",
            "severity": "blocking" if severity == "critical" else severity,
            "source": "consistency_analyst",
            "suggested_fix": char_issue.get("suggested_fix", ""),
            "previous_state": char_issue.get("previous_state", ""),
            "current_state": char_issue.get("current_state", ""),
        }
        if severity in ("critical", "high"):
            severe_issues.append(issue)
        else:
            minor_issues.append(issue)
    
    # World rule violations
    for rule_violation in analysis.get("world_rule_violations", []):
        severity = rule_violation.get("severity", "medium").lower()
        issue = {
            "type": "world_rule",
            "detail": f"Règle violée: {rule_violation.get('rule', '')} - {rule_violation.get('violation', '')}",
            "severity": "blocking" if severity == "critical" else severity,
            "source": "consistency_analyst",
            "suggested_fix": rule_violation.get("suggested_fix", ""),
        }
        if severity in ("critical", "high"):
            severe_issues.append(issue)
        else:
            minor_issues.append(issue)
    
    blocking = any(i.get("severity") == "blocking" for i in severe_issues)
    
    return {
        "severe_issues": severe_issues,
        "minor_issues": minor_issues,
        "coherence_score": float(analysis.get("overall_coherence_score", 7.0)),
        "blocking": blocking,
        "blocking_issues": analysis.get("blocking_issues", []),
        "summary": analysis.get("summary", ""),
    }

async def _get_previous_chapter_texts(
    self, project_id: Optional[UUID], chapter_index: Optional[int], limit: int = 5
) -> List[str]:
    """Retrieve previous chapter texts for context."""
    if not project_id or not chapter_index or chapter_index <= 1:
        return []
    
    from app.services.document_service import DocumentService
    doc_service = DocumentService(self.db)
    
    chapters = []
    for idx in range(max(1, chapter_index - limit), chapter_index):
        doc = await doc_service.get_chapter_by_index(project_id, idx)
        if doc and doc.content:
            # Tronquer pour économiser les tokens
            content = doc.content[:2000] if len(doc.content) > 2000 else doc.content
            chapters.append(f"[Chapitre {idx}]\n{content}")
    
    return chapters
```

**Tests** :
```python
# backend/tests/test_pipeline_consistency_integration.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_validate_continuity_uses_consistency_analyst():
    """Test that validate_continuity delegates to ConsistencyAnalyst."""
    # Setup
    pipeline = WritingPipeline(db=AsyncMock())
    pipeline.consistency_analyst = MagicMock()
    pipeline.consistency_analyst.execute = AsyncMock(return_value={
        "success": True,
        "analysis": {
            "contradictions": [],
            "timeline_issues": [],
            "character_inconsistencies": [],
            "world_rule_violations": [],
            "overall_coherence_score": 8.5,
            "summary": "No issues found",
            "blocking_issues": [],
        }
    })
    
    state = {
        "chapter_text": "Sample chapter text...",
        "memory_context": "Context...",
        "project_context": {"metadata": {"story_bible": {}}},
    }
    
    # Execute
    result = await pipeline.validate_continuity(state)
    
    # Assert
    assert pipeline.consistency_analyst.execute.called
    assert "continuity_validation" in result
    assert result["continuity_validation"]["coherence_score"] == 8.5
```

---

### 3.2 TÂCHE 1.2 : Tracking des Objets et Localisation

**Objectif** : Étendre Neo4j pour tracker les objets narratifs et la localisation des personnages.

**Fichier** : `backend/app/services/memory_service.py`

**Étapes** :

1. **Ajouter constantes** :
```python
# Après les imports, ligne ~25
OBJECT_STATUSES = ["possessed", "lost", "destroyed", "hidden", "transferred"]
CHARACTER_LOCATIONS = ["known", "unknown", "traveling"]
```

2. **Modifier _build_extraction_prompt** :
```python
def _build_extraction_prompt(self, chapter_text: str) -> str:
    return (
        "Tu es un assistant de coherence narrative. Reponds en francais uniquement.\n"
        "Extrait les faits de continuite en JSON strict avec les cles: summary, characters, locations, "
        "relations, events, objects, character_locations.\n"
        "Utilise des cles snake_case ASCII. Si une info manque, laisse le champ vide.\n\n"
        "characters: liste de {name, role, status, current_state, motivations, traits, goals, arc_stage, "
        "last_seen_chapter, relationships}\n"
        "locations: liste de {name, description, rules, timeline_markers, atmosphere, last_mentioned_chapter}\n"
        "relations: liste de {from, to, type, detail, start_chapter, current_state, evolution}\n"
        "events: liste de {name, summary, chapter_index, time_reference, impact, unresolved_threads}\n"
        "objects: liste de {name, description, status, current_holder, location, "
        "lost_at_chapter, found_at_chapter, importance, magical_properties}\n"
        "character_locations: liste de {character_name, location, chapter_index, "
        "travel_from, travel_to, arrival_confirmed}\n\n"
        "status pour objects: possessed, lost, destroyed, hidden, transferred\n"
        "Retourne uniquement le JSON.\n\n"
        f"Chapitre:\n{chapter_text}"
    )
```

3. **Ajouter méthodes de tracking d'objets** :
```python
def update_neo4j_objects(
    self,
    facts: Dict[str, Any],
    project_id: Optional[str] = None,
    chapter_index: Optional[int] = None,
) -> None:
    """Update Neo4j with object tracking data."""
    if not self.neo4j_driver:
        return
    
    timestamp = datetime.utcnow().isoformat()
    database = settings.NEO4J_DATABASE or None
    base_chapter = self._resolve_chapter_index(chapter_index)
    
    with self.neo4j_driver.session(database=database) as session:
        for obj in facts.get("objects", []):
            name = obj.get("name")
            if not name:
                continue
            
            obj_chapter = self._resolve_chapter_index(
                obj.get("last_seen_chapter"), base_chapter
            )
            status = obj.get("status", "possessed")
            holder = obj.get("current_holder")
            location = obj.get("location")
            
            # Build status history entry
            status_entry = []
            if status and isinstance(obj_chapter, int):
                status_entry = [{
                    "status": status,
                    "chapter": obj_chapter,
                    "holder": holder,
                    "location": location,
                    "timestamp": timestamp,
                }]
            
            params = {
                "name": name,
                "description": obj.get("description"),
                "status": status,
                "current_holder": holder,
                "location": location,
                "importance": obj.get("importance", "normal"),
                "magical_properties": obj.get("magical_properties"),
                "chapter_index": obj_chapter,
                "timestamp": timestamp,
                "status_entry": status_entry,
            }
            
            if project_id:
                params["project_id"] = project_id
                session.run(
                    """
                    MERGE (o:Object {name: $name, project_id: $project_id})
                    ON CREATE SET 
                        o.created_chapter = $chapter_index,
                        o.first_appearance = $timestamp
                    SET 
                        o.description = $description,
                        o.status = $status,
                        o.current_holder = $current_holder,
                        o.location = $location,
                        o.importance = $importance,
                        o.magical_properties = $magical_properties,
                        o.last_seen_chapter = $chapter_index,
                        o.last_updated = $timestamp,
                        o.project_id = $project_id,
                        o.status_history = coalesce(o.status_history, []) + $status_entry
                    """,
                    **params,
                )
                
                # Create relationship to holder if exists
                if holder:
                    session.run(
                        """
                        MATCH (o:Object {name: $obj_name, project_id: $project_id})
                        MATCH (c:Character {name: $holder_name, project_id: $project_id})
                        MERGE (c)-[r:POSSESSES]->(o)
                        SET r.since_chapter = $chapter_index, r.updated = $timestamp
                        """,
                        obj_name=name,
                        holder_name=holder,
                        project_id=project_id,
                        chapter_index=obj_chapter,
                        timestamp=timestamp,
                    )
            else:
                session.run(
                    """
                    MERGE (o:Object {name: $name})
                    ON CREATE SET 
                        o.created_chapter = $chapter_index,
                        o.first_appearance = $timestamp
                    SET 
                        o.description = $description,
                        o.status = $status,
                        o.current_holder = $current_holder,
                        o.location = $location,
                        o.importance = $importance,
                        o.magical_properties = $magical_properties,
                        o.last_seen_chapter = $chapter_index,
                        o.last_updated = $timestamp,
                        o.status_history = coalesce(o.status_history, []) + $status_entry
                    """,
                    **params,
                )

def check_object_availability(
    self,
    object_name: str,
    chapter_index: int,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check if an object is available for use at a given chapter.
    
    Returns:
        Dict with keys: available, status, holder, location, issue
    """
    if not self.neo4j_driver:
        return {"available": True, "status": "unknown", "issue": None}
    
    database = settings.NEO4J_DATABASE or None
    
    query_base = "MATCH (o:Object {name: $name"
    if project_id:
        query_base += ", project_id: $project_id"
    query_base += "}) RETURN o"
    
    params = {"name": object_name}
    if project_id:
        params["project_id"] = project_id
    
    with self.neo4j_driver.session(database=database) as session:
        result = session.run(query_base, **params)
        record = result.single()
        
        if not record:
            return {"available": True, "status": "unknown", "issue": None}
        
        obj = dict(record["o"])
        status = obj.get("status", "possessed")
        holder = obj.get("current_holder")
        location = obj.get("location")
        lost_chapter = None
        
        # Check status history for lost status
        status_history = obj.get("status_history", [])
        for entry in status_history:
            if entry.get("status") == "lost" and entry.get("chapter", 0) < chapter_index:
                # Check if found after
                found_after = any(
                    e.get("status") in ("possessed", "found") 
                    and e.get("chapter", 0) > entry.get("chapter", 0)
                    and e.get("chapter", 0) <= chapter_index
                    for e in status_history
                )
                if not found_after:
                    lost_chapter = entry.get("chapter")
                    break
        
        if status == "destroyed":
            return {
                "available": False,
                "status": "destroyed",
                "holder": None,
                "location": None,
                "issue": f"L'objet '{object_name}' a été détruit et ne peut plus être utilisé.",
            }
        
        if lost_chapter:
            return {
                "available": False,
                "status": "lost",
                "holder": None,
                "location": location,
                "issue": f"L'objet '{object_name}' a été perdu au chapitre {lost_chapter} et n'a pas été retrouvé.",
            }
        
        return {
            "available": True,
            "status": status,
            "holder": holder,
            "location": location,
            "issue": None,
        }

def update_character_locations(
    self,
    facts: Dict[str, Any],
    project_id: Optional[str] = None,
    chapter_index: Optional[int] = None,
) -> None:
    """Update character location tracking in Neo4j."""
    if not self.neo4j_driver:
        return
    
    timestamp = datetime.utcnow().isoformat()
    database = settings.NEO4J_DATABASE or None
    base_chapter = self._resolve_chapter_index(chapter_index)
    
    with self.neo4j_driver.session(database=database) as session:
        for loc_entry in facts.get("character_locations", []):
            char_name = loc_entry.get("character_name")
            location = loc_entry.get("location")
            if not char_name or not location:
                continue
            
            entry_chapter = self._resolve_chapter_index(
                loc_entry.get("chapter_index"), base_chapter
            )
            
            location_entry = {
                "location": location,
                "chapter": entry_chapter,
                "timestamp": timestamp,
                "travel_from": loc_entry.get("travel_from"),
                "travel_to": loc_entry.get("travel_to"),
                "arrival_confirmed": loc_entry.get("arrival_confirmed", True),
            }
            
            params = {
                "name": char_name,
                "current_location": location,
                "chapter_index": entry_chapter,
                "timestamp": timestamp,
                "location_entry": [location_entry],
            }
            
            if project_id:
                params["project_id"] = project_id
                session.run(
                    """
                    MATCH (c:Character {name: $name, project_id: $project_id})
                    SET 
                        c.current_location = $current_location,
                        c.location_updated_chapter = $chapter_index,
                        c.location_history = coalesce(c.location_history, []) + $location_entry
                    """,
                    **params,
                )
            else:
                session.run(
                    """
                    MATCH (c:Character {name: $name})
                    SET 
                        c.current_location = $current_location,
                        c.location_updated_chapter = $chapter_index,
                        c.location_history = coalesce(c.location_history, []) + $location_entry
                    """,
                    **params,
                )

def check_character_location_consistency(
    self,
    character_name: str,
    required_location: str,
    chapter_index: int,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check if a character can plausibly be at a location.
    
    Returns:
        Dict with keys: consistent, current_location, last_known_chapter, issue
    """
    if not self.neo4j_driver:
        return {"consistent": True, "issue": None}
    
    database = settings.NEO4J_DATABASE or None
    
    query_base = "MATCH (c:Character {name: $name"
    if project_id:
        query_base += ", project_id: $project_id"
    query_base += "}) RETURN c"
    
    params = {"name": character_name}
    if project_id:
        params["project_id"] = project_id
    
    with self.neo4j_driver.session(database=database) as session:
        result = session.run(query_base, **params)
        record = result.single()
        
        if not record:
            return {"consistent": True, "issue": None}
        
        char = dict(record["c"])
        current_location = char.get("current_location")
        location_chapter = char.get("location_updated_chapter")
        
        if not current_location:
            return {"consistent": True, "issue": None}
        
        # If same location, all good
        if current_location.lower() == required_location.lower():
            return {
                "consistent": True,
                "current_location": current_location,
                "last_known_chapter": location_chapter,
                "issue": None,
            }
        
        # Check if there's a travel entry
        location_history = char.get("location_history", [])
        travel_found = any(
            entry.get("travel_to", "").lower() == required_location.lower()
            and entry.get("chapter", 0) <= chapter_index
            for entry in location_history
        )
        
        if travel_found:
            return {
                "consistent": True,
                "current_location": required_location,
                "last_known_chapter": chapter_index,
                "issue": None,
            }
        
        # Calculate chapter gap
        chapter_gap = chapter_index - (location_chapter or 0)
        
        # Allow some tolerance (1-2 chapters could include implicit travel)
        if chapter_gap <= 2:
            return {
                "consistent": True,
                "current_location": current_location,
                "last_known_chapter": location_chapter,
                "issue": None,
                "warning": f"Voyage implicite de {current_location} à {required_location}",
            }
        
        return {
            "consistent": False,
            "current_location": current_location,
            "last_known_chapter": location_chapter,
            "issue": (
                f"'{character_name}' était à '{current_location}' au chapitre {location_chapter}. "
                f"Aucun voyage vers '{required_location}' n'a été mentionné."
            ),
        }
```

4. **Modifier update_neo4j pour appeler les nouvelles méthodes** :
```python
def update_neo4j(
    self,
    facts: Dict[str, Any],
    project_id: Optional[str] = None,
    chapter_index: Optional[int] = None,
) -> None:
    """Update Neo4j graph nodes with temporal attributes."""
    if not self.neo4j_driver:
        return
    
    # Code existant pour characters, locations, relations, events...
    # (garder tout le code existant)
    
    # AJOUTER à la fin :
    # Update objects
    self.update_neo4j_objects(facts, project_id, chapter_index)
    
    # Update character locations
    self.update_character_locations(facts, project_id, chapter_index)
```

**Tests** :
```python
# backend/tests/test_object_tracking.py
import pytest

def test_check_object_availability_lost():
    """Test object availability when lost."""
    service = MemoryService()
    # Mock Neo4j driver...
    
    result = service.check_object_availability(
        object_name="Clé magique",
        chapter_index=7,
        project_id="test-project"
    )
    
    assert result["available"] == False
    assert "perdu" in result["issue"]

def test_check_character_location_inconsistent():
    """Test character location consistency check."""
    service = MemoryService()
    # Mock Neo4j driver...
    
    result = service.check_character_location_consistency(
        character_name="Alice",
        required_location="Tokyo",
        chapter_index=10,
        project_id="test-project"
    )
    
    # Should fail if Alice was in Paris with no travel
    assert result["consistent"] == False
```

---

### 3.3 TÂCHE 1.3 : Chekhov's Guns Tracker

**Objectif** : Tracker les éléments narratifs qui attendent une résolution.

**Fichier** : `backend/app/services/coherence/chekhov_tracker.py` (CRÉER)

```python
"""Chekhov's Gun Tracker - Track narrative elements awaiting resolution."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.config import settings
from app.services.llm_client import DeepSeekClient
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class ChekhovGun:
    """Represents a narrative element awaiting resolution."""
    
    def __init__(
        self,
        element: str,
        element_type: str,
        expectation: str,
        introduced_chapter: int,
        urgency: int = 5,
        resolved: bool = False,
        resolved_chapter: Optional[int] = None,
        hints_dropped: Optional[List[Dict[str, Any]]] = None,
    ):
        self.element = element
        self.element_type = element_type  # object, skill, threat, promise, foreshadowing
        self.expectation = expectation
        self.introduced_chapter = introduced_chapter
        self.urgency = urgency  # 1-10
        self.resolved = resolved
        self.resolved_chapter = resolved_chapter
        self.hints_dropped = hints_dropped or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "element": self.element,
            "element_type": self.element_type,
            "expectation": self.expectation,
            "introduced_chapter": self.introduced_chapter,
            "urgency": self.urgency,
            "resolved": self.resolved,
            "resolved_chapter": self.resolved_chapter,
            "hints_dropped": self.hints_dropped,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChekhovGun":
        return cls(
            element=data.get("element", ""),
            element_type=data.get("element_type", "object"),
            expectation=data.get("expectation", ""),
            introduced_chapter=data.get("introduced_chapter", 1),
            urgency=data.get("urgency", 5),
            resolved=data.get("resolved", False),
            resolved_chapter=data.get("resolved_chapter"),
            hints_dropped=data.get("hints_dropped", []),
        )


class ChekhovTracker:
    """Track and manage Chekhov's Guns in a narrative."""
    
    def __init__(self) -> None:
        self.llm_client = DeepSeekClient()
        self.memory_service = MemoryService()
    
    async def extract_guns(
        self,
        chapter_text: str,
        chapter_index: int,
        existing_guns: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Extract new Chekhov's Guns from chapter text.
        
        Args:
            chapter_text: The chapter content to analyze.
            chapter_index: Current chapter number.
            existing_guns: List of already tracked guns.
            
        Returns:
            Dict with new_guns and resolved_guns.
        """
        existing_guns = existing_guns or []
        existing_summary = self._summarize_existing_guns(existing_guns)
        
        prompt = f"""Tu es un analyste narratif expert. Analyse ce chapitre pour identifier :

1. NOUVEAUX ÉLÉMENTS (Chekhov's Guns) qui créent une attente chez le lecteur :
   - Objets significatifs (armes, clés, lettres, artefacts)
   - Compétences ou secrets révélés mais non utilisés
   - Menaces évoquées mais non concrétisées
   - Promesses faites par des personnages
   - Foreshadowing explicite ou implicite
   - Questions posées sans réponse

2. RÉSOLUTIONS d'éléments précédemment introduits :
   - Un objet utilisé
   - Une compétence mise en œuvre
   - Une menace concrétisée
   - Une promesse tenue ou brisée
   - Une question répondue

ÉLÉMENTS DÉJÀ TRACKÉS :
{existing_summary}

CHAPITRE {chapter_index} :
{chapter_text[:4000]}

Retourne un JSON strict :
{{
    "new_guns": [
        {{
            "element": "Description courte de l'élément",
            "element_type": "object|skill|threat|promise|foreshadowing|question",
            "expectation": "Ce que le lecteur attend comme résolution",
            "urgency": 1-10,
            "justification": "Pourquoi cet élément crée une attente"
        }}
    ],
    "resolved_guns": [
        {{
            "element": "L'élément résolu (doit matcher un élément existant)",
            "resolution_type": "fulfilled|subverted|abandoned",
            "resolution_detail": "Comment l'élément a été résolu"
        }}
    ],
    "hints_dropped": [
        {{
            "for_element": "L'élément concerné",
            "hint": "Description de l'indice",
            "chapter": {chapter_index}
        }}
    ]
}}
"""
        
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )
        
        return self._parse_extraction_response(response, chapter_index)
    
    async def check_unresolved(
        self,
        guns: List[Dict[str, Any]],
        current_chapter: int,
        max_chapters_unresolved: int = 15,
        urgency_threshold: int = 7,
    ) -> List[Dict[str, Any]]:
        """
        Check for guns that have been unresolved too long.
        
        Args:
            guns: List of tracked guns.
            current_chapter: Current chapter index.
            max_chapters_unresolved: Max chapters before alerting.
            urgency_threshold: Min urgency to trigger alert.
            
        Returns:
            List of overdue guns with alerts.
        """
        alerts = []
        
        for gun_data in guns:
            gun = ChekhovGun.from_dict(gun_data)
            
            if gun.resolved:
                continue
            
            chapters_waiting = current_chapter - gun.introduced_chapter
            
            # High urgency guns need faster resolution
            adjusted_max = max_chapters_unresolved
            if gun.urgency >= 8:
                adjusted_max = max(5, max_chapters_unresolved // 2)
            elif gun.urgency >= 6:
                adjusted_max = max(8, int(max_chapters_unresolved * 0.7))
            
            if chapters_waiting > adjusted_max and gun.urgency >= urgency_threshold:
                alerts.append({
                    "element": gun.element,
                    "element_type": gun.element_type,
                    "expectation": gun.expectation,
                    "introduced_chapter": gun.introduced_chapter,
                    "chapters_waiting": chapters_waiting,
                    "urgency": gun.urgency,
                    "severity": "high" if gun.urgency >= 8 else "medium",
                    "recommendation": self._generate_resolution_recommendation(gun),
                })
        
        return alerts
    
    async def suggest_resolutions(
        self,
        unresolved_guns: List[Dict[str, Any]],
        story_context: str,
        upcoming_chapters: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Suggest ways to resolve pending narrative elements.
        
        Args:
            unresolved_guns: List of unresolved guns.
            story_context: Current story context/summary.
            upcoming_chapters: How many chapters to plan for.
            
        Returns:
            List of resolution suggestions.
        """
        if not unresolved_guns:
            return []
        
        guns_summary = "\n".join([
            f"- {g['element']} ({g['element_type']}): {g['expectation']} "
            f"[Urgence: {g['urgency']}/10, Attente: {g.get('chapters_waiting', '?')} chapitres]"
            for g in unresolved_guns
        ])
        
        prompt = f"""Tu es un consultant en structure narrative.

ÉLÉMENTS NON RÉSOLUS :
{guns_summary}

CONTEXTE DE L'HISTOIRE :
{story_context[:2000]}

Pour chaque élément, propose une résolution créative pour les {upcoming_chapters} prochains chapitres.
Types de résolution possibles :
- fulfilled: L'attente est satisfaite comme prévu
- subverted: L'attente est détournée de manière intéressante
- escalated: L'élément devient plus important/urgent

Retourne JSON :
{{
    "suggestions": [
        {{
            "element": "...",
            "resolution_type": "fulfilled|subverted|escalated",
            "suggested_chapter": N,
            "resolution_idea": "Description de comment résoudre",
            "integration_hint": "Comment l'intégrer naturellement"
        }}
    ]
}}
"""
        
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        
        try:
            result = json.loads(response)
            return result.get("suggestions", [])
        except json.JSONDecodeError:
            logger.error("Failed to parse resolution suggestions")
            return []
    
    def update_gun_status(
        self,
        guns: List[Dict[str, Any]],
        resolved_guns: List[Dict[str, Any]],
        hints: List[Dict[str, Any]],
        chapter_index: int,
    ) -> List[Dict[str, Any]]:
        """
        Update gun statuses based on chapter analysis.
        
        Args:
            guns: Current list of guns.
            resolved_guns: Guns identified as resolved.
            hints: Hints dropped in this chapter.
            chapter_index: Current chapter.
            
        Returns:
            Updated list of guns.
        """
        updated_guns = []
        
        for gun_data in guns:
            gun = ChekhovGun.from_dict(gun_data)
            
            # Check if resolved
            for resolved in resolved_guns:
                if self._elements_match(gun.element, resolved.get("element", "")):
                    gun.resolved = True
                    gun.resolved_chapter = chapter_index
                    break
            
            # Add hints
            for hint in hints:
                if self._elements_match(gun.element, hint.get("for_element", "")):
                    gun.hints_dropped.append({
                        "hint": hint.get("hint", ""),
                        "chapter": hint.get("chapter", chapter_index),
                    })
            
            updated_guns.append(gun.to_dict())
        
        return updated_guns
    
    def _summarize_existing_guns(self, guns: List[Dict[str, Any]]) -> str:
        if not guns:
            return "Aucun élément tracké."
        
        lines = []
        for g in guns:
            status = "✅ Résolu" if g.get("resolved") else "⏳ En attente"
            lines.append(
                f"- [{status}] {g.get('element')} ({g.get('element_type')}): "
                f"{g.get('expectation')} [Ch.{g.get('introduced_chapter')}]"
            )
        return "\n".join(lines)
    
    def _parse_extraction_response(
        self, response: str, chapter_index: int
    ) -> Dict[str, Any]:
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            logger.error("Failed to parse Chekhov extraction response")
            return {"new_guns": [], "resolved_guns": [], "hints_dropped": []}
        
        new_guns = []
        for gun in data.get("new_guns", []):
            new_guns.append({
                "element": gun.get("element", ""),
                "element_type": gun.get("element_type", "object"),
                "expectation": gun.get("expectation", ""),
                "introduced_chapter": chapter_index,
                "urgency": min(10, max(1, gun.get("urgency", 5))),
                "resolved": False,
                "resolved_chapter": None,
                "hints_dropped": [],
            })
        
        return {
            "new_guns": new_guns,
            "resolved_guns": data.get("resolved_guns", []),
            "hints_dropped": data.get("hints_dropped", []),
        }
    
    def _elements_match(self, element1: str, element2: str) -> bool:
        """Check if two element descriptions refer to the same thing."""
        e1 = element1.lower().strip()
        e2 = element2.lower().strip()
        
        if e1 == e2:
            return True
        
        # Check for significant word overlap
        words1 = set(e1.split())
        words2 = set(e2.split())
        common = words1 & words2
        
        # If >50% words match, consider same element
        if len(common) >= min(len(words1), len(words2)) * 0.5:
            return True
        
        return False
    
    def _generate_resolution_recommendation(self, gun: ChekhovGun) -> str:
        """Generate a recommendation for resolving a gun."""
        recommendations = {
            "object": f"L'objet '{gun.element}' devrait être utilisé ou sa pertinence expliquée.",
            "skill": f"La compétence mentionnée devrait être mise en pratique.",
            "threat": f"La menace devrait se concrétiser ou être neutralisée.",
            "promise": f"La promesse devrait être tenue, brisée, ou son statut clarifié.",
            "foreshadowing": f"L'élément de préfiguration devrait se réaliser.",
            "question": f"La question soulevée mérite une réponse.",
        }
        return recommendations.get(gun.element_type, "Cet élément attend une résolution.")
```

**Fichier init** : `backend/app/services/coherence/__init__.py` (CRÉER)
```python
"""Coherence services for narrative consistency."""
from app.services.coherence.chekhov_tracker import ChekhovTracker, ChekhovGun

__all__ = ["ChekhovTracker", "ChekhovGun"]
```

**Intégration dans le Pipeline** : Modifier `backend/app/services/writing_pipeline.py`
```python
# Ajouter import
from app.services.coherence.chekhov_tracker import ChekhovTracker

# Dans __init__
self.chekhov_tracker = ChekhovTracker()

# Ajouter méthode
async def _update_chekhov_guns(self, state: NovelState, chapter_text: str) -> Dict[str, Any]:
    """Extract and update Chekhov's Guns after chapter generation."""
    if not settings.CHEKHOV_TRACKER_ENABLED:
        return {"chekhov_update": None}
    
    project_context = state.get("project_context") or {}
    project_metadata = project_context.get("metadata") or {}
    existing_guns = project_metadata.get("chekhov_guns", [])
    chapter_index = state.get("chapter_index", 1)
    
    # Extract new guns and resolutions
    extraction = await self.chekhov_tracker.extract_guns(
        chapter_text=chapter_text,
        chapter_index=chapter_index,
        existing_guns=existing_guns,
    )
    
    # Update gun statuses
    updated_guns = existing_guns + extraction.get("new_guns", [])
    updated_guns = self.chekhov_tracker.update_gun_status(
        guns=updated_guns,
        resolved_guns=extraction.get("resolved_guns", []),
        hints=extraction.get("hints_dropped", []),
        chapter_index=chapter_index,
    )
    
    # Check for overdue guns
    alerts = await self.chekhov_tracker.check_unresolved(
        guns=updated_guns,
        current_chapter=chapter_index,
        max_chapters_unresolved=settings.CHEKHOV_MAX_UNRESOLVED_CHAPTERS,
        urgency_threshold=settings.CHEKHOV_URGENCY_THRESHOLD,
    )
    
    return {
        "chekhov_update": {
            "guns": updated_guns,
            "new_count": len(extraction.get("new_guns", [])),
            "resolved_count": len(extraction.get("resolved_guns", [])),
            "alerts": alerts,
        }
    }

# Appeler dans approve_chapter
async def approve_chapter(self, state: NovelState) -> Dict[str, Any]:
    # ... code existant ...
    
    # AJOUTER avant la fin:
    chekhov_result = await self._update_chekhov_guns(state, chapter_text)
    if chekhov_result.get("chekhov_update"):
        # Store updated guns in project metadata
        # (À implémenter: sauvegarde dans project_metadata)
        pass
    
    # ... reste du code ...
```

**Tests** :
```python
# backend/tests/test_chekhov_tracker.py
import pytest
from app.services.coherence.chekhov_tracker import ChekhovTracker, ChekhovGun

@pytest.mark.asyncio
async def test_extract_guns():
    tracker = ChekhovTracker()
    
    chapter_text = """
    Marie trouva une clé ancienne dans le tiroir de son grand-père.
    Elle brillait d'un éclat étrange, comme si elle attendait quelque chose.
    "Je te promets de revenir," dit Jean avant de partir.
    """
    
    result = await tracker.extract_guns(
        chapter_text=chapter_text,
        chapter_index=1,
        existing_guns=[],
    )
    
    assert len(result["new_guns"]) >= 2  # Clé + promesse
    assert any("clé" in g["element"].lower() for g in result["new_guns"])

def test_check_unresolved():
    tracker = ChekhovTracker()
    
    guns = [
        {
            "element": "Clé mystérieuse",
            "element_type": "object",
            "expectation": "Ouvrira quelque chose",
            "introduced_chapter": 1,
            "urgency": 8,
            "resolved": False,
        }
    ]
    
    # Should alert after 15 chapters
    alerts = tracker.check_unresolved(
        guns=guns,
        current_chapter=20,
        max_chapters_unresolved=15,
        urgency_threshold=7,
    )
    
    assert len(alerts) == 1
    assert alerts[0]["element"] == "Clé mystérieuse"
```

---

## 4. Phase 2 : Mémoire Avancée

### 4.1 TÂCHE 2.1 : Mémoire Récursive (Pyramide de Résumés)

**Objectif** : Implémenter une structure pyramidale de résumés pour les romans longs.

**Fichier** : `backend/app/services/coherence/recursive_memory.py` (CRÉER)

```python
"""Recursive Memory - Pyramid summary structure for long novels."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, DocumentType
from app.services.llm_client import DeepSeekClient

logger = logging.getLogger(__name__)


class RecursiveMemory:
    """
    Manages a pyramid structure of summaries:
    
    Level 3: Global Synopsis (~1000 words)
        └── Level 2: Arc Summaries (~500 words each)
            └── Level 1: Chapter Summaries (detailed, last 5 chapters)
    """
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm_client = DeepSeekClient()
        
        # Configuration
        self.recent_chapters_count = settings.RECURSIVE_MEMORY_RECENT_CHAPTERS
        self.arc_summary_words = settings.RECURSIVE_MEMORY_ARC_SUMMARY_WORDS
        self.global_synopsis_words = settings.RECURSIVE_MEMORY_GLOBAL_SYNOPSIS_WORDS
    
    async def build_context(
        self,
        project_id: UUID,
        chapter_index: int,
        project_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build hierarchical context for chapter generation.
        
        Args:
            project_id: The project UUID.
            chapter_index: Current chapter being written.
            project_metadata: Project metadata (optional, will fetch if not provided).
            
        Returns:
            Formatted context string combining all levels.
        """
        # Level 3: Global synopsis
        global_synopsis = await self._get_global_synopsis(project_id, project_metadata)
        
        # Level 2: Current arc summary
        arc_summary = await self._get_current_arc_summary(
            project_id, chapter_index, project_metadata
        )
        
        # Level 1: Recent chapter summaries (detailed)
        recent_summaries = await self._get_recent_chapter_summaries(
            project_id, chapter_index
        )
        
        # Merge levels with clear structure
        context_parts = []
        
        if global_synopsis:
            context_parts.append(f"=== SYNOPSIS GLOBAL ===\n{global_synopsis}")
        
        if arc_summary:
            context_parts.append(f"=== ARC NARRATIF ACTUEL ===\n{arc_summary}")
        
        if recent_summaries:
            summaries_text = "\n\n".join([
                f"[Chapitre {s['index']}] {s['summary']}"
                for s in recent_summaries
            ])
            context_parts.append(f"=== CHAPITRES RÉCENTS ===\n{summaries_text}")
        
        return "\n\n".join(context_parts)
    
    async def update_after_chapter(
        self,
        project_id: UUID,
        chapter_index: int,
        chapter_text: str,
        chapter_summary: str,
    ) -> Dict[str, Any]:
        """
        Update memory structures after a chapter is approved.
        
        Args:
            project_id: The project UUID.
            chapter_index: The approved chapter index.
            chapter_text: Full chapter text.
            chapter_summary: Summary of the chapter.
            
        Returns:
            Dict with update status and any regenerated summaries.
        """
        updates = {
            "chapter_summary_stored": True,
            "arc_summary_updated": False,
            "global_synopsis_updated": False,
        }
        
        # Store chapter summary
        await self._store_chapter_summary(project_id, chapter_index, chapter_summary)
        
        # Check if arc summary needs update (every 5 chapters or end of arc)
        if await self._should_update_arc_summary(project_id, chapter_index):
            await self._update_arc_summary(project_id, chapter_index)
            updates["arc_summary_updated"] = True
        
        # Check if global synopsis needs update (every 10 chapters)
        if chapter_index % 10 == 0:
            await self._update_global_synopsis(project_id)
            updates["global_synopsis_updated"] = True
        
        return updates
    
    async def _get_global_synopsis(
        self,
        project_id: UUID,
        project_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Get or generate global synopsis."""
        if project_metadata is None:
            project_metadata = await self._fetch_project_metadata(project_id)
        
        recursive_memory = project_metadata.get("recursive_memory", {})
        return recursive_memory.get("global_synopsis", "")
    
    async def _get_current_arc_summary(
        self,
        project_id: UUID,
        chapter_index: int,
        project_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Get summary of the current narrative arc."""
        if project_metadata is None:
            project_metadata = await self._fetch_project_metadata(project_id)
        
        # Find current arc based on plan
        plan = project_metadata.get("plan", {})
        if isinstance(plan, dict):
            plan_data = plan.get("data", plan)
        else:
            plan_data = {}
        
        arcs = plan_data.get("arcs", [])
        current_arc = None
        
        for arc in arcs:
            start = arc.get("chapter_start", 0)
            end = arc.get("chapter_end", 999)
            if start <= chapter_index <= end:
                current_arc = arc
                break
        
        if not current_arc:
            return ""
        
        # Get arc summary from recursive memory
        recursive_memory = project_metadata.get("recursive_memory", {})
        arc_summaries = recursive_memory.get("arc_summaries", {})
        arc_id = current_arc.get("id", "")
        
        return arc_summaries.get(arc_id, current_arc.get("summary", ""))
    
    async def _get_recent_chapter_summaries(
        self,
        project_id: UUID,
        chapter_index: int,
    ) -> List[Dict[str, Any]]:
        """Get detailed summaries of recent chapters."""
        summaries = []
        
        # Query documents for recent chapters
        start_index = max(1, chapter_index - self.recent_chapters_count)
        
        result = await self.db.execute(
            select(Document).where(
                Document.project_id == project_id,
                Document.document_type == DocumentType.CHAPTER,
                Document.order_index >= start_index,
                Document.order_index < chapter_index,
            ).order_by(Document.order_index.asc())
        )
        documents = result.scalars().all()
        
        for doc in documents:
            metadata = doc.document_metadata or {}
            summary = metadata.get("summary", "")
            
            # If no summary, generate one
            if not summary and doc.content:
                summary = await self._generate_chapter_summary(doc.content)
            
            if summary:
                summaries.append({
                    "index": doc.order_index,
                    "title": doc.title,
                    "summary": summary,
                })
        
        return summaries
    
    async def _store_chapter_summary(
        self,
        project_id: UUID,
        chapter_index: int,
        summary: str,
    ) -> None:
        """Store chapter summary in document metadata."""
        result = await self.db.execute(
            select(Document).where(
                Document.project_id == project_id,
                Document.document_type == DocumentType.CHAPTER,
                Document.order_index == chapter_index,
            )
        )
        doc = result.scalar_one_or_none()
        
        if doc:
            metadata = doc.document_metadata or {}
            metadata["summary"] = summary
            doc.document_metadata = metadata
            await self.db.commit()
    
    async def _should_update_arc_summary(
        self,
        project_id: UUID,
        chapter_index: int,
    ) -> bool:
        """Determine if arc summary should be updated."""
        # Update every 5 chapters or at arc boundaries
        if chapter_index % 5 == 0:
            return True
        
        # Check if this is an arc boundary
        project_metadata = await self._fetch_project_metadata(project_id)
        plan = project_metadata.get("plan", {})
        if isinstance(plan, dict):
            plan_data = plan.get("data", plan)
        else:
            plan_data = {}
        
        arcs = plan_data.get("arcs", [])
        for arc in arcs:
            if arc.get("chapter_end") == chapter_index:
                return True
        
        return False
    
    async def _update_arc_summary(
        self,
        project_id: UUID,
        chapter_index: int,
    ) -> None:
        """Regenerate current arc summary."""
        project_metadata = await self._fetch_project_metadata(project_id)
        
        # Find current arc
        plan = project_metadata.get("plan", {})
        if isinstance(plan, dict):
            plan_data = plan.get("data", plan)
        else:
            plan_data = {}
        
        arcs = plan_data.get("arcs", [])
        current_arc = None
        
        for arc in arcs:
            start = arc.get("chapter_start", 0)
            end = arc.get("chapter_end", 999)
            if start <= chapter_index <= end:
                current_arc = arc
                break
        
        if not current_arc:
            return
        
        # Get all chapter summaries in this arc
        arc_start = current_arc.get("chapter_start", 1)
        arc_end = min(current_arc.get("chapter_end", chapter_index), chapter_index)
        
        result = await self.db.execute(
            select(Document).where(
                Document.project_id == project_id,
                Document.document_type == DocumentType.CHAPTER,
                Document.order_index >= arc_start,
                Document.order_index <= arc_end,
            ).order_by(Document.order_index.asc())
        )
        documents = result.scalars().all()
        
        chapter_summaries = []
        for doc in documents:
            metadata = doc.document_metadata or {}
            summary = metadata.get("summary", "")
            if summary:
                chapter_summaries.append(f"Ch.{doc.order_index}: {summary}")
        
        if not chapter_summaries:
            return
        
        # Generate arc summary
        arc_summary = await self._generate_arc_summary(
            arc_title=current_arc.get("title", "Arc"),
            arc_target_emotion=current_arc.get("target_emotion", ""),
            chapter_summaries=chapter_summaries,
        )
        
        # Store in project metadata
        await self._store_arc_summary(project_id, current_arc.get("id", ""), arc_summary)
    
    async def _update_global_synopsis(self, project_id: UUID) -> None:
        """Regenerate global synopsis from all arc summaries."""
        project_metadata = await self._fetch_project_metadata(project_id)
        
        recursive_memory = project_metadata.get("recursive_memory", {})
        arc_summaries = recursive_memory.get("arc_summaries", {})
        
        if not arc_summaries:
            return
        
        # Get concept for context
        concept = project_metadata.get("concept", {})
        if isinstance(concept, dict):
            concept_data = concept.get("data", concept)
        else:
            concept_data = {}
        
        premise = concept_data.get("premise", "")
        
        # Generate global synopsis
        synopsis = await self._generate_global_synopsis(
            premise=premise,
            arc_summaries=list(arc_summaries.values()),
        )
        
        # Store
        await self._store_global_synopsis(project_id, synopsis)
    
    async def _generate_chapter_summary(self, chapter_text: str) -> str:
        """Generate a summary for a chapter."""
        prompt = f"""Résume ce chapitre en 2-3 phrases, en capturant :
- Les événements principaux
- Les évolutions des personnages
- Les éléments importants pour la suite

Chapitre :
{chapter_text[:3000]}

Résumé (2-3 phrases) :"""
        
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        return response.strip()
    
    async def _generate_arc_summary(
        self,
        arc_title: str,
        arc_target_emotion: str,
        chapter_summaries: List[str],
    ) -> str:
        """Generate a summary for a narrative arc."""
        chapters_text = "\n".join(chapter_summaries)
        
        prompt = f"""Résume cet arc narratif en environ {self.arc_summary_words} mots.

Titre de l'arc : {arc_title}
Émotion cible : {arc_target_emotion}

Résumés des chapitres :
{chapters_text}

Résumé de l'arc (capture la progression narrative, les conflits, les résolutions partielles) :"""
        
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=800,
        )
        return response.strip()
    
    async def _generate_global_synopsis(
        self,
        premise: str,
        arc_summaries: List[str],
    ) -> str:
        """Generate global synopsis from arc summaries."""
        arcs_text = "\n\n".join([f"Arc {i+1}: {s}" for i, s in enumerate(arc_summaries)])
        
        prompt = f"""Génère un synopsis global du roman en environ {self.global_synopsis_words} mots.

Prémisse : {premise}

Résumés des arcs :
{arcs_text}

Synopsis global (couvre l'intrigue principale, les personnages clés, les thèmes) :"""
        
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1500,
        )
        return response.strip()
    
    async def _fetch_project_metadata(self, project_id: UUID) -> Dict[str, Any]:
        """Fetch project metadata from database."""
        from app.models.project import Project
        
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if project:
            return project.project_metadata or {}
        return {}
    
    async def _store_arc_summary(
        self,
        project_id: UUID,
        arc_id: str,
        summary: str,
    ) -> None:
        """Store arc summary in project metadata."""
        from app.models.project import Project
        
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if project:
            metadata = project.project_metadata or {}
            if "recursive_memory" not in metadata:
                metadata["recursive_memory"] = {}
            if "arc_summaries" not in metadata["recursive_memory"]:
                metadata["recursive_memory"]["arc_summaries"] = {}
            
            metadata["recursive_memory"]["arc_summaries"][arc_id] = summary
            project.project_metadata = metadata
            await self.db.commit()
    
    async def _store_global_synopsis(
        self,
        project_id: UUID,
        synopsis: str,
    ) -> None:
        """Store global synopsis in project metadata."""
        from app.models.project import Project
        
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if project:
            metadata = project.project_metadata or {}
            if "recursive_memory" not in metadata:
                metadata["recursive_memory"] = {}
            
            metadata["recursive_memory"]["global_synopsis"] = synopsis
            metadata["recursive_memory"]["synopsis_updated_at"] = (
                __import__("datetime").datetime.utcnow().isoformat()
            )
            project.project_metadata = metadata
            await self.db.commit()
```

**Intégration dans writing_pipeline.py** :
```python
# Ajouter import
from app.services.coherence.recursive_memory import RecursiveMemory

# Dans collect_context, remplacer la construction du memory_context
async def collect_context(self, state: NovelState) -> Dict[str, Any]:
    # ... code existant jusqu'à la construction du memory_context ...
    
    # REMPLACER la logique de memory_context par :
    if settings.RECURSIVE_MEMORY_ENABLED:
        recursive_memory = RecursiveMemory(self.db)
        memory_context = await recursive_memory.build_context(
            project_id=state.get("project_id"),
            chapter_index=state.get("chapter_index", 1),
            project_metadata=project_metadata,
        )
    else:
        # Fallback à l'ancienne logique
        memory_context = await self._build_legacy_memory_context(...)
    
    # ... reste du code ...
```

---

### 4.2 TÂCHE 2.2 : Validation Sémantique par Embeddings

**Fichier** : `backend/app/services/coherence/semantic_validator.py` (CRÉER)

```python
"""Semantic Validator - Detect subtle contradictions using embeddings."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not installed. Semantic validation disabled.")


class SemanticValidator:
    """
    Validates narrative consistency using semantic embeddings.
    
    Detects contradictions that are semantically related but logically
    incompatible, which LLM analysis might miss.
    """
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> None:
        """
        Initialize the semantic validator.
        
        Args:
            model_name: Name of the sentence-transformers model to use.
        """
        self.model = None
        self.model_name = model_name
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                logger.info(f"Loaded sentence transformer model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load sentence transformer: {e}")
    
    def extract_facts(self, text: str) -> List[str]:
        """
        Extract factual statements from text.
        
        Args:
            text: Text to extract facts from.
            
        Returns:
            List of factual statements.
        """
        # Split into sentences
        import re
        sentences = re.split(r'[.!?]+', text)
        
        facts = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            # Filter for likely factual statements
            # (contains names, descriptions, states, actions)
            if any([
                # Contains a proper noun (capitalized word not at start)
                re.search(r'(?<!^)\b[A-Z][a-z]+', sentence),
                # Contains "est" or "était" (being verbs)
                re.search(r'\b(est|était|sont|étaient|a|avait|possède|déteste|aime)\b', sentence, re.I),
                # Contains descriptive patterns
                re.search(r'\b(toujours|jamais|souvent|parfois)\b', sentence, re.I),
            ]):
                facts.append(sentence)
        
        return facts
    
    def embed(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of texts to embed.
            
        Returns:
            Numpy array of embeddings or None if model not available.
        """
        if not self.model or not texts:
            return None
        
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return None
    
    def find_similar_facts(
        self,
        new_fact: str,
        new_embedding: np.ndarray,
        established_facts: List[str],
        established_embeddings: np.ndarray,
        threshold: float = 0.7,
    ) -> List[Tuple[str, float]]:
        """
        Find established facts similar to a new fact.
        
        Args:
            new_fact: The new fact to compare.
            new_embedding: Embedding of the new fact.
            established_facts: List of established facts.
            established_embeddings: Embeddings of established facts.
            threshold: Minimum similarity threshold.
            
        Returns:
            List of (fact, similarity_score) tuples.
        """
        if established_embeddings is None or len(established_embeddings) == 0:
            return []
        
        # Compute cosine similarities
        similarities = self._cosine_similarity(new_embedding, established_embeddings)
        
        # Find facts above threshold
        similar = []
        for i, sim in enumerate(similarities):
            if sim >= threshold:
                similar.append((established_facts[i], float(sim)))
        
        # Sort by similarity descending
        similar.sort(key=lambda x: x[1], reverse=True)
        return similar
    
    def detect_contradictions(
        self,
        new_facts: List[str],
        established_facts: List[str],
        similarity_threshold: float = 0.7,
        contradiction_patterns: Optional[List[Tuple[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detect potential contradictions between new and established facts.
        
        Args:
            new_facts: Facts from the new content.
            established_facts: Previously established facts.
            similarity_threshold: Min similarity to consider related.
            contradiction_patterns: Pairs of contradictory patterns.
            
        Returns:
            List of potential contradictions with details.
        """
        if not self.model:
            return []
        
        if not new_facts or not established_facts:
            return []
        
        # Default contradiction patterns
        if contradiction_patterns is None:
            contradiction_patterns = [
                ("vivant", "mort"),
                ("aime", "déteste"),
                ("ami", "ennemi"),
                ("présent", "absent"),
                ("possède", "a perdu"),
                ("connaît", "ignore"),
                ("jeune", "vieux"),
                ("riche", "pauvre"),
                ("grand", "petit"),
                ("fort", "faible"),
            ]
        
        # Embed all facts
        new_embeddings = self.embed(new_facts)
        established_embeddings = self.embed(established_facts)
        
        if new_embeddings is None or established_embeddings is None:
            return []
        
        contradictions = []
        
        for i, new_fact in enumerate(new_facts):
            new_emb = new_embeddings[i:i+1]
            
            # Find similar established facts
            similar = self.find_similar_facts(
                new_fact, new_emb, established_facts, established_embeddings,
                threshold=similarity_threshold
            )
            
            for est_fact, similarity in similar:
                # Check for contradiction patterns
                is_contradiction, pattern = self._check_contradiction_patterns(
                    new_fact, est_fact, contradiction_patterns
                )
                
                if is_contradiction:
                    contradictions.append({
                        "new_fact": new_fact,
                        "established_fact": est_fact,
                        "similarity_score": similarity,
                        "contradiction_type": "pattern_match",
                        "pattern": pattern,
                        "confidence": min(0.95, similarity + 0.1),
                    })
                elif similarity > 0.85:
                    # Very high similarity but different - might be contradiction
                    if self._facts_differ(new_fact, est_fact):
                        contradictions.append({
                            "new_fact": new_fact,
                            "established_fact": est_fact,
                            "similarity_score": similarity,
                            "contradiction_type": "semantic_conflict",
                            "pattern": None,
                            "confidence": similarity * 0.7,
                        })
        
        return contradictions
    
    def _cosine_similarity(
        self, embedding: np.ndarray, embeddings: np.ndarray
    ) -> np.ndarray:
        """Compute cosine similarity between one embedding and many."""
        # Normalize
        embedding = embedding / np.linalg.norm(embedding, axis=-1, keepdims=True)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=-1, keepdims=True)
        
        # Compute similarity
        return np.dot(embedding, embeddings.T).flatten()
    
    def _check_contradiction_patterns(
        self,
        fact1: str,
        fact2: str,
        patterns: List[Tuple[str, str]],
    ) -> Tuple[bool, Optional[Tuple[str, str]]]:
        """Check if two facts contain contradictory patterns."""
        f1_lower = fact1.lower()
        f2_lower = fact2.lower()
        
        for p1, p2 in patterns:
            # Check if one fact has p1 and other has p2
            if (p1 in f1_lower and p2 in f2_lower) or (p2 in f1_lower and p1 in f2_lower):
                return True, (p1, p2)
        
        return False, None
    
    def _facts_differ(self, fact1: str, fact2: str) -> bool:
        """Check if two similar facts say different things."""
        # Simple heuristic: if they share a subject but have different predicates
        import re
        
        # Extract potential subjects (capitalized words)
        subjects1 = set(re.findall(r'\b[A-Z][a-z]+\b', fact1))
        subjects2 = set(re.findall(r'\b[A-Z][a-z]+\b', fact2))
        
        common_subjects = subjects1 & subjects2
        
        if not common_subjects:
            return False
        
        # If they share subjects but aren't nearly identical, they might conflict
        # Compute word overlap
        words1 = set(fact1.lower().split())
        words2 = set(fact2.lower().split())
        
        overlap = len(words1 & words2) / max(len(words1), len(words2))
        
        # If overlap is between 30-70%, likely saying different things about same subject
        return 0.3 < overlap < 0.7


# Convenience function for integration
async def validate_chapter_semantically(
    chapter_text: str,
    established_context: str,
    threshold: float = 0.8,
) -> List[Dict[str, Any]]:
    """
    Validate a chapter against established context using semantic analysis.
    
    Args:
        chapter_text: The new chapter content.
        established_context: Previously established facts/context.
        threshold: Contradiction detection threshold.
        
    Returns:
        List of potential semantic contradictions.
    """
    validator = SemanticValidator()
    
    new_facts = validator.extract_facts(chapter_text)
    established_facts = validator.extract_facts(established_context)
    
    return validator.detect_contradictions(
        new_facts=new_facts,
        established_facts=established_facts,
        similarity_threshold=threshold,
    )
```

**Ajouter dépendance** : `backend/requirements.txt`
```
sentence-transformers>=2.2.0
```

---

### 4.3 TÂCHE 2.3 : Promotion Automatique vers Story Bible

**Fichier** : `backend/app/tasks/coherence_tasks.py` (CRÉER)

```python
"""Celery tasks for coherence maintenance."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.project import Project, ProjectStatus
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Helper to run async code in sync Celery tasks."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(
    name="promote_facts_to_bible",
    queue="maintenance_low",
    soft_time_limit=300,
    time_limit=360,
)
def promote_facts_to_bible(project_id: str) -> Dict[str, Any]:
    """
    Analyze fact frequency and promote recurring facts to Story Bible.
    
    This task examines facts extracted from chapters and promotes
    frequently occurring patterns to permanent story rules.
    """
    return _run_async(_promote_facts_to_bible_async(project_id))


async def _promote_facts_to_bible_async(project_id: str) -> Dict[str, Any]:
    """Async implementation of fact promotion."""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return {"error": "Invalid project ID"}
    
    async with AsyncSessionLocal() as db:
        # Fetch project
        result = await db.execute(
            select(Project).where(Project.id == project_uuid)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return {"error": "Project not found"}
        
        metadata = project.project_metadata or {}
        continuity = metadata.get("continuity", {})
        story_bible = metadata.get("story_bible", {})
        
        # Initialize story_bible sections if needed
        if "characters" not in story_bible:
            story_bible["characters"] = []
        if "world_rules" not in story_bible:
            story_bible["world_rules"] = []
        if "locations" not in story_bible:
            story_bible["locations"] = []
        
        promotions = {
            "character_traits": [],
            "world_rules": [],
            "locations": [],
        }
        
        # Analyze character trait frequency
        characters = continuity.get("characters", [])
        trait_frequency = _analyze_character_traits(characters)
        
        for char_name, traits in trait_frequency.items():
            for trait, count in traits.items():
                if count >= settings.FACT_PROMOTION_THRESHOLD:
                    # Promote to story bible
                    _add_character_trait_to_bible(
                        story_bible, char_name, trait, count
                    )
                    promotions["character_traits"].append({
                        "character": char_name,
                        "trait": trait,
                        "frequency": count,
                    })
        
        # Analyze location rules frequency
        locations = continuity.get("locations", [])
        location_rules = _analyze_location_rules(locations)
        
        for loc_name, rules in location_rules.items():
            for rule, count in rules.items():
                if count >= settings.FACT_PROMOTION_THRESHOLD:
                    _add_location_rule_to_bible(
                        story_bible, loc_name, rule, count
                    )
                    promotions["locations"].append({
                        "location": loc_name,
                        "rule": rule,
                        "frequency": count,
                    })
        
        # Analyze recurring event patterns (potential world rules)
        events = continuity.get("events", [])
        world_rules = _extract_world_rules(events)
        
        for rule, count in world_rules.items():
            if count >= settings.FACT_PROMOTION_THRESHOLD:
                _add_world_rule_to_bible(story_bible, rule, count)
                promotions["world_rules"].append({
                    "rule": rule,
                    "frequency": count,
                })
        
        # Save updated story bible
        metadata["story_bible"] = story_bible
        metadata["story_bible_last_promotion"] = datetime.utcnow().isoformat()
        project.project_metadata = metadata
        await db.commit()
        
        logger.info(
            "Promoted facts to bible for project %s: %s",
            project_id, promotions
        )
        
        return {
            "success": True,
            "promotions": promotions,
            "total_promoted": sum(len(v) for v in promotions.values()),
        }


def _analyze_character_traits(
    characters: List[Dict[str, Any]]
) -> Dict[str, Dict[str, int]]:
    """Count trait occurrences per character."""
    trait_counts: Dict[str, Dict[str, int]] = {}
    
    for char in characters:
        name = char.get("name", "")
        if not name:
            continue
        
        if name not in trait_counts:
            trait_counts[name] = {}
        
        # Count traits
        traits = char.get("traits", [])
        if isinstance(traits, list):
            for trait in traits:
                if isinstance(trait, str) and trait:
                    trait_counts[name][trait] = trait_counts[name].get(trait, 0) + 1
        
        # Count motivations as traits
        motivations = char.get("motivations", [])
        if isinstance(motivations, list):
            for mot in motivations:
                if isinstance(mot, str) and mot:
                    key = f"motivation:{mot}"
                    trait_counts[name][key] = trait_counts[name].get(key, 0) + 1
    
    return trait_counts


def _analyze_location_rules(
    locations: List[Dict[str, Any]]
) -> Dict[str, Dict[str, int]]:
    """Count rule occurrences per location."""
    rule_counts: Dict[str, Dict[str, int]] = {}
    
    for loc in locations:
        name = loc.get("name", "")
        if not name:
            continue
        
        if name not in rule_counts:
            rule_counts[name] = {}
        
        rules = loc.get("rules", [])
        if isinstance(rules, list):
            for rule in rules:
                if isinstance(rule, str) and rule:
                    rule_counts[name][rule] = rule_counts[name].get(rule, 0) + 1
    
    return rule_counts


def _extract_world_rules(events: List[Dict[str, Any]]) -> Dict[str, int]:
    """Extract potential world rules from recurring event patterns."""
    rule_counts: Dict[str, int] = {}
    
    # Look for patterns in events that suggest world rules
    for event in events:
        impact = event.get("impact", "")
        if isinstance(impact, str) and len(impact) > 20:
            # Normalize and count
            normalized = impact.lower().strip()
            rule_counts[normalized] = rule_counts.get(normalized, 0) + 1
    
    return rule_counts


def _add_character_trait_to_bible(
    story_bible: Dict[str, Any],
    character_name: str,
    trait: str,
    frequency: int,
) -> None:
    """Add a character trait to the story bible."""
    characters = story_bible.get("characters", [])
    
    # Find or create character entry
    char_entry = None
    for c in characters:
        if c.get("name", "").lower() == character_name.lower():
            char_entry = c
            break
    
    if not char_entry:
        char_entry = {
            "name": character_name,
            "traits": [],
            "auto_promoted": True,
        }
        characters.append(char_entry)
    
    # Add trait if not already present
    if "traits" not in char_entry:
        char_entry["traits"] = []
    
    existing_traits = [t.get("trait") if isinstance(t, dict) else t for t in char_entry["traits"]]
    
    if trait not in existing_traits:
        char_entry["traits"].append({
            "trait": trait,
            "source": "auto_promoted",
            "confidence": min(1.0, frequency / 10),
            "promoted_at": datetime.utcnow().isoformat(),
        })
    
    story_bible["characters"] = characters


def _add_location_rule_to_bible(
    story_bible: Dict[str, Any],
    location_name: str,
    rule: str,
    frequency: int,
) -> None:
    """Add a location rule to the story bible."""
    locations = story_bible.get("locations", [])
    
    # Find or create location entry
    loc_entry = None
    for loc in locations:
        if loc.get("name", "").lower() == location_name.lower():
            loc_entry = loc
            break
    
    if not loc_entry:
        loc_entry = {
            "name": location_name,
            "rules": [],
            "auto_promoted": True,
        }
        locations.append(loc_entry)
    
    if "rules" not in loc_entry:
        loc_entry["rules"] = []
    
    existing_rules = [r.get("rule") if isinstance(r, dict) else r for r in loc_entry["rules"]]
    
    if rule not in existing_rules:
        loc_entry["rules"].append({
            "rule": rule,
            "source": "auto_promoted",
            "confidence": min(1.0, frequency / 10),
            "promoted_at": datetime.utcnow().isoformat(),
        })
    
    story_bible["locations"] = locations


def _add_world_rule_to_bible(
    story_bible: Dict[str, Any],
    rule: str,
    frequency: int,
) -> None:
    """Add a world rule to the story bible."""
    world_rules = story_bible.get("world_rules", [])
    
    existing_rules = [r.get("rule") if isinstance(r, dict) else r for r in world_rules]
    
    if rule not in existing_rules:
        world_rules.append({
            "rule": rule,
            "source": "auto_promoted",
            "confidence": min(1.0, frequency / 10),
            "promoted_at": datetime.utcnow().isoformat(),
        })
    
    story_bible["world_rules"] = world_rules


# Schedule periodic promotion
celery_app.conf.beat_schedule["daily-fact-promotion"] = {
    "task": "promote_all_project_facts",
    "schedule": timedelta(hours=settings.FACT_PROMOTION_SCHEDULE_HOURS),
}


@celery_app.task(name="promote_all_project_facts", queue="maintenance_low")
def promote_all_project_facts() -> Dict[str, Any]:
    """Promote facts for all active projects."""
    return _run_async(_promote_all_project_facts_async())


async def _promote_all_project_facts_async() -> Dict[str, Any]:
    """Async implementation of bulk fact promotion."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Project).where(
                Project.status.in_([ProjectStatus.DRAFT, ProjectStatus.IN_PROGRESS])
            )
        )
        projects = result.scalars().all()
    
    results = []
    for project in projects:
        result = await _promote_facts_to_bible_async(str(project.id))
        results.append({
            "project_id": str(project.id),
            "result": result,
        })
    
    return {
        "projects_processed": len(projects),
        "results": results,
    }
```

---

## 5. Phase 3 : Qualité Narrative

### 5.1 TÂCHE 3.1 : Détection Character Drift

**Fichier** : `backend/app/services/coherence/character_drift.py` (CRÉER)

```python
"""Character Drift Detector - Detect unjustified character changes."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.llm_client import DeepSeekClient
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class CharacterDriftDetector:
    """
    Detects when a character's behavior drifts from their established arc
    without proper justification through events or development.
    """
    
    def __init__(self) -> None:
        self.llm_client = DeepSeekClient()
        self.memory_service = MemoryService()
    
    async def analyze_character_consistency(
        self,
        character_name: str,
        current_behavior: str,
        project_id: str,
        chapter_index: int,
    ) -> Dict[str, Any]:
        """
        Analyze if current character behavior is consistent with their arc.
        
        Args:
            character_name: Name of the character.
            current_behavior: Description of current behavior/dialogue.
            project_id: Project identifier.
            chapter_index: Current chapter number.
            
        Returns:
            Analysis result with drift detection.
        """
        # Get character evolution from Neo4j
        evolution = self.memory_service.query_character_evolution(
            character_name, project_id
        )
        
        if not evolution:
            return {
                "character": character_name,
                "drift_detected": False,
                "reason": "No historical data for character",
            }
        
        # Get character from story bible if available
        character_bible = await self._get_character_from_bible(
            character_name, project_id
        )
        
        # Analyze drift
        prompt = f"""Tu es un analyste de cohérence de personnage.

PERSONNAGE : {character_name}

DONNÉES HISTORIQUES (Neo4j) :
- Première apparition : chapitre {evolution.get('first_appearance', '?')}
- Dernière vue : chapitre {evolution.get('last_seen_chapter', '?')}
- Historique des statuts : {evolution.get('status_history', [])}

DÉFINITION DANS LA STORY BIBLE :
{json.dumps(character_bible, ensure_ascii=False, indent=2) if character_bible else "Non défini"}

COMPORTEMENT ACTUEL (Chapitre {chapter_index}) :
{current_behavior}

Analyse si le comportement actuel est cohérent avec l'arc établi du personnage.

Questions à considérer :
1. Le comportement correspond-il aux traits établis ?
2. Si le comportement diffère, y a-t-il un événement justificatif ?
3. L'évolution est-elle naturelle ou abrupte ?

Retourne JSON :
{{
    "drift_detected": true/false,
    "drift_type": "personality|motivation|values|relationships|null",
    "severity": 1-10,
    "analysis": "Explication détaillée",
    "established_traits": ["trait1", "trait2"],
    "conflicting_behavior": "Description du conflit si drift détecté",
    "justification_found": true/false,
    "justification_event": "Événement justificatif si trouvé",
    "suggested_resolution": "Comment résoudre le drift si nécessaire"
}}
"""
        
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        
        try:
            result = json.loads(response)
            result["character"] = character_name
            result["chapter_index"] = chapter_index
            return result
        except json.JSONDecodeError:
            logger.error("Failed to parse character drift analysis")
            return {
                "character": character_name,
                "drift_detected": False,
                "error": "Analysis parsing failed",
            }
    
    async def analyze_chapter_characters(
        self,
        chapter_text: str,
        project_id: str,
        chapter_index: int,
        known_characters: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Analyze all characters in a chapter for drift.
        
        Args:
            chapter_text: The chapter content.
            project_id: Project identifier.
            chapter_index: Current chapter number.
            known_characters: List of known character names.
            
        Returns:
            List of drift analyses per character.
        """
        results = []
        
        # Extract character behaviors from chapter
        behaviors = await self._extract_character_behaviors(
            chapter_text, known_characters
        )
        
        for char_name, behavior in behaviors.items():
            analysis = await self.analyze_character_consistency(
                character_name=char_name,
                current_behavior=behavior,
                project_id=project_id,
                chapter_index=chapter_index,
            )
            
            if analysis.get("drift_detected"):
                results.append(analysis)
        
        return results
    
    async def _get_character_from_bible(
        self,
        character_name: str,
        project_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get character definition from story bible."""
        # This would fetch from project metadata
        # Simplified implementation
        return None
    
    async def _extract_character_behaviors(
        self,
        chapter_text: str,
        known_characters: List[str],
    ) -> Dict[str, str]:
        """Extract character behaviors from chapter text."""
        if not known_characters:
            return {}
        
        characters_list = ", ".join(known_characters)
        
        prompt = f"""Extrait les comportements et dialogues des personnages suivants dans ce chapitre :
Personnages à analyser : {characters_list}

Chapitre :
{chapter_text[:3000]}

Pour chaque personnage présent, décris :
- Ses actions principales
- Son attitude/ton
- Ses dialogues clés (paraphrasés)
- Ses décisions

Retourne JSON :
{{
    "personnages": {{
        "NomPersonnage": "Description du comportement dans ce chapitre"
    }}
}}

N'inclus que les personnages effectivement présents dans le chapitre.
"""
        
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        
        try:
            result = json.loads(response)
            return result.get("personnages", {})
        except json.JSONDecodeError:
            return {}
```

---

### 5.2 TÂCHE 3.2 : Analyse Constance de Voix

**Fichier** : `backend/app/services/coherence/voice_analyzer.py` (CRÉER)

```python
"""Voice Consistency Analyzer - Analyze character voice consistency."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.core.config import settings
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


class VoiceConsistencyAnalyzer:
    """
    Analyzes character voice consistency by comparing dialogues
    with validated historical patterns.
    """
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> None:
        self.memory_service = MemoryService()
        self.model = None
        
        if EMBEDDINGS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
    
    def extract_dialogues(
        self,
        text: str,
        character_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract dialogues from text, optionally filtering by character.
        
        Args:
            text: The text to extract dialogues from.
            character_name: Optional character to filter for.
            
        Returns:
            List of dialogue entries with speaker and content.
        """
        dialogues = []
        
        # Pattern for dialogues: "text" or « text » or - text
        patterns = [
            r'"([^"]+)"',  # "dialogue"
            r'«\s*([^»]+)\s*»',  # « dialogue »
            r'—\s*([^—\n]+)',  # — dialogue
            r'-\s+([A-Z][^-\n]+)',  # - Dialogue starting with capital
        ]
        
        # Pattern to detect speaker before dialogue
        speaker_pattern = r'(\b[A-Z][a-z]+)\s+(?:dit|demanda|répondit|murmura|cria|chuchota|expliqua|ajouta)'
        
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                dialogue = match.group(1).strip()
                if len(dialogue) < 5:
                    continue
                
                # Try to find speaker
                speaker = None
                context_start = max(0, match.start() - 100)
                context = text[context_start:match.start()]
                
                speaker_match = re.search(speaker_pattern, context)
                if speaker_match:
                    speaker = speaker_match.group(1)
                
                # Filter by character if specified
                if character_name and speaker:
                    if speaker.lower() != character_name.lower():
                        continue
                
                dialogues.append({
                    "speaker": speaker,
                    "dialogue": dialogue,
                    "position": match.start(),
                })
        
        return dialogues
    
    async def analyze_voice_consistency(
        self,
        character_name: str,
        new_dialogues: List[str],
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Analyze voice consistency for a character.
        
        Args:
            character_name: Name of the character.
            new_dialogues: New dialogues to analyze.
            project_id: Project identifier.
            
        Returns:
            Voice consistency analysis.
        """
        if not self.model or not new_dialogues:
            return {
                "character": character_name,
                "voice_consistency_score": 1.0,
                "analysis_available": False,
            }
        
        # Retrieve validated dialogues from ChromaDB
        validated_dialogues = self.memory_service.retrieve_style_memory(
            project_id=project_id,
            query=f"dialogues de {character_name}",
            top_k=20,
        )
        
        if not validated_dialogues or len(validated_dialogues) < settings.VOICE_MIN_DIALOGUES_FOR_ANALYSIS:
            return {
                "character": character_name,
                "voice_consistency_score": 1.0,
                "analysis_available": False,
                "reason": "Insufficient historical dialogues",
            }
        
        # Embed dialogues
        new_embeddings = self.model.encode(new_dialogues, convert_to_numpy=True)
        validated_embeddings = self.model.encode(validated_dialogues, convert_to_numpy=True)
        
        # Compute average similarity
        similarities = []
        outliers = []
        
        for i, new_emb in enumerate(new_embeddings):
            # Compute cosine similarity with all validated
            sims = self._cosine_similarity(new_emb, validated_embeddings)
            avg_sim = float(np.mean(sims))
            max_sim = float(np.max(sims))
            
            similarities.append(avg_sim)
            
            # Flag outliers
            if avg_sim < settings.VOICE_CONSISTENCY_THRESHOLD:
                outliers.append({
                    "dialogue": new_dialogues[i],
                    "avg_similarity": avg_sim,
                    "max_similarity": max_sim,
                })
        
        overall_score = float(np.mean(similarities))
        drift_detected = overall_score < settings.VOICE_CONSISTENCY_THRESHOLD
        
        return {
            "character": character_name,
            "voice_consistency_score": overall_score,
            "analysis_available": True,
            "drift_detected": drift_detected,
            "dialogues_analyzed": len(new_dialogues),
            "reference_dialogues": len(validated_dialogues),
            "outlier_dialogues": outliers,
            "individual_scores": similarities,
        }
    
    async def analyze_chapter_voices(
        self,
        chapter_text: str,
        project_id: str,
        known_characters: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze voice consistency for all characters in a chapter.
        
        Args:
            chapter_text: The chapter content.
            project_id: Project identifier.
            known_characters: List of known character names.
            
        Returns:
            Dict mapping character names to voice analyses.
        """
        results = {}
        
        for character in known_characters:
            dialogues = self.extract_dialogues(chapter_text, character)
            
            if not dialogues:
                continue
            
            dialogue_texts = [d["dialogue"] for d in dialogues]
            
            analysis = await self.analyze_voice_consistency(
                character_name=character,
                new_dialogues=dialogue_texts,
                project_id=project_id,
            )
            
            results[character] = analysis
        
        return results
    
    def store_validated_dialogues(
        self,
        character_name: str,
        dialogues: List[str],
        project_id: str,
        chapter_index: int,
    ) -> None:
        """
        Store validated dialogues for future reference.
        
        Args:
            character_name: Name of the character.
            dialogues: List of dialogue texts.
            project_id: Project identifier.
            chapter_index: Chapter number.
        """
        for dialogue in dialogues:
            self.memory_service.store_style_memory(
                project_id=project_id,
                chapter_id=f"ch{chapter_index}_{character_name}",
                text=dialogue,
                summary=f"Dialogue validé de {character_name}",
            )
    
    def _cosine_similarity(
        self, embedding: np.ndarray, embeddings: np.ndarray
    ) -> np.ndarray:
        """Compute cosine similarity."""
        embedding = embedding / np.linalg.norm(embedding)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        return np.dot(embeddings, embedding)
```

---

### 5.3 TÂCHE 3.3 : Incohérences Intentionnelles

**Fichier** : `backend/app/services/agents/consistency_analyst.py` (MODIFIER)

**Ajouter après la méthode `__init__`** :
```python
def _load_intentional_mysteries(
    self, context: Optional[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Load intentional mysteries from project context."""
    if not context:
        return []
    
    metadata = context.get("metadata") or {}
    story_bible = metadata.get("story_bible") or {}
    return story_bible.get("intentional_mysteries", [])

def _matches_mystery(
    self, contradiction: Dict[str, Any],
    mysteries: List[Dict[str, Any]],
) -> bool:
    """Check if a contradiction matches an intentional mystery."""
    if not mysteries:
        return False
    
    contradiction_desc = str(contradiction.get("description", "")).lower()
    contradiction_type = str(contradiction.get("type", "")).lower()
    
    for mystery in mysteries:
        mystery_desc = str(mystery.get("description", "")).lower()
        mystery_chars = [c.lower() for c in mystery.get("characters_involved", [])]
        
        # Check description overlap
        if mystery_desc and mystery_desc in contradiction_desc:
            return True
        
        # Check if contradiction involves mystery characters
        location = str(contradiction.get("location_in_text", "")).lower()
        if any(char in location or char in contradiction_desc for char in mystery_chars):
            # Additional check: is contradiction type compatible with mystery?
            mystery_type = mystery.get("contradiction_type", "")
            if mystery_type in ("lie", "unreliable_narrator", "hidden_info"):
                return True
    
    return False
```

**Modifier `_analyze_chapter_coherence`** :
```python
async def _analyze_chapter_coherence(
    self, task_data: Dict[str, Any], context: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Analyze chapter coherence against established context."""
    chapter_text, memory_context, story_bible, previous_chapters = self._resolve_chapter_inputs(
        task_data, context
    )
    
    # AJOUTER : Charger les mystères intentionnels
    intentional_mysteries = self._load_intentional_mysteries(context)
    
    # ... prompt existant ...
    
    response = await self._call_api(prompt, context, temperature=0.2)
    analysis = self._safe_json(response)
    
    # AJOUTER : Filtrer les contradictions qui matchent des mystères
    if intentional_mysteries:
        filtered_contradictions = []
        filtered_out = []
        
        for contradiction in analysis.get("contradictions", []):
            if self._matches_mystery(contradiction, intentional_mysteries):
                filtered_out.append({
                    **contradiction,
                    "filtered_reason": "Matches intentional mystery",
                })
            else:
                filtered_contradictions.append(contradiction)
        
        analysis["contradictions"] = filtered_contradictions
        analysis["filtered_intentional"] = filtered_out
    
    return {
        "agent": self.name,
        "action": "analyze_chapter",
        "analysis": analysis,
        "success": True,
        "total_issues": self._count_issues(analysis),
        "critical_count": self._count_by_severity(analysis, "critical"),
    }
```

**Schéma pour les mystères** : `backend/app/schemas/coherence.py` (CRÉER)
```python
"""Schemas for coherence features."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class IntentionalMystery(BaseModel):
    """An intentional contradiction/mystery in the narrative."""
    
    id: str
    description: str = Field(..., min_length=10)
    contradiction_type: str = Field(
        ...,
        pattern="^(lie|unreliable_narrator|hidden_info|time_paradox|identity_secret)$"
    )
    introduced_chapter: int = Field(..., ge=1)
    resolution_planned_chapter: Optional[int] = Field(None, ge=1)
    characters_involved: List[str] = Field(default_factory=list)
    hints_to_drop: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolution_chapter: Optional[int] = None


class IntentionalMysteryCreate(BaseModel):
    """Schema for creating an intentional mystery."""
    
    description: str = Field(..., min_length=10)
    contradiction_type: str = Field(
        ...,
        pattern="^(lie|unreliable_narrator|hidden_info|time_paradox|identity_secret)$"
    )
    introduced_chapter: int = Field(..., ge=1)
    resolution_planned_chapter: Optional[int] = Field(None, ge=1)
    characters_involved: List[str] = Field(default_factory=list)
    hints_to_drop: List[str] = Field(default_factory=list)


class ChekhovGunSchema(BaseModel):
    """Schema for a Chekhov's Gun."""
    
    element: str
    element_type: str = Field(
        ...,
        pattern="^(object|skill|threat|promise|foreshadowing|question)$"
    )
    expectation: str
    introduced_chapter: int
    urgency: int = Field(5, ge=1, le=10)
    resolved: bool = False
    resolved_chapter: Optional[int] = None
    hints_dropped: List[dict] = Field(default_factory=list)


class VoiceAnalysisResult(BaseModel):
    """Result of voice consistency analysis."""
    
    character: str
    voice_consistency_score: float = Field(..., ge=0.0, le=1.0)
    analysis_available: bool
    drift_detected: bool = False
    outlier_dialogues: List[dict] = Field(default_factory=list)


class CharacterDriftResult(BaseModel):
    """Result of character drift detection."""
    
    character: str
    drift_detected: bool
    drift_type: Optional[str] = None
    severity: int = Field(0, ge=0, le=10)
    analysis: str = ""
    justification_found: bool = False
    suggested_resolution: Optional[str] = None
```

---

## 6. Phase 4 : Features Avancées

### 6.1 TÂCHE 4.1 : Validation POV

**Fichier** : `backend/app/services/coherence/pov_validator.py` (CRÉER)

```python
"""POV Validator - Validate point of view consistency."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.llm_client import DeepSeekClient

logger = logging.getLogger(__name__)


class POVValidator:
    """
    Validates point of view consistency in narrative.
    
    Detects violations like:
    - Accessing thoughts of non-POV characters in limited POV
    - Knowing information the POV character couldn't know
    - Accidental omniscience in limited/first-person narratives
    """
    
    POV_TYPES = {
        "first_person": "Narrateur = personnage principal, 'je'",
        "limited": "Troisième personne, accès aux pensées d'un seul personnage",
        "omniscient": "Narrateur omniscient, accès à toutes les pensées",
        "objective": "Narrateur externe, pas d'accès aux pensées",
    }
    
    def __init__(self) -> None:
        self.llm_client = DeepSeekClient()
    
    async def validate_pov(
        self,
        chapter_text: str,
        pov_character: str,
        pov_type: str = "limited",
        known_information: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Validate POV consistency in a chapter.
        
        Args:
            chapter_text: The chapter content.
            pov_character: The POV character's name.
            pov_type: Type of POV (first_person, limited, omniscient, objective).
            known_information: List of facts the POV character knows.
            
        Returns:
            Validation result with any violations found.
        """
        if pov_type == "omniscient":
            return {
                "pov_character": pov_character,
                "pov_type": pov_type,
                "violations": [],
                "valid": True,
                "note": "POV omniscient allows access to all thoughts",
            }
        
        known_info_text = ""
        if known_information:
            known_info_text = "\n".join([f"- {info}" for info in known_information])
        
        prompt = f"""Tu es un expert en narration et point de vue (POV).

CONFIGURATION DU POV :
- Personnage POV : {pov_character}
- Type de POV : {pov_type} ({self.POV_TYPES.get(pov_type, '')})

INFORMATIONS CONNUES PAR {pov_character} :
{known_info_text if known_info_text else "Non spécifié"}

CHAPITRE À ANALYSER :
{chapter_text[:4000]}

Détecte les violations de POV :

1. PENSÉES INTERDITES : En POV {pov_type}, le narrateur ne devrait pas accéder aux pensées/émotions internes des personnages autres que {pov_character}.

2. INFORMATIONS IMPOSSIBLES : Le narrateur ne devrait pas révéler des informations que {pov_character} ne peut pas connaître (événements en son absence, secrets non révélés, etc.).

3. OMNISCIENCE ACCIDENTELLE : Passages où le narrateur semble tout savoir alors que le POV est {pov_type}.

Retourne JSON :
{{
    "violations": [
        {{
            "type": "forbidden_thoughts|impossible_knowledge|accidental_omniscience",
            "severity": "high|medium|low",
            "location": "Citation du passage problématique",
            "character_involved": "Personnage dont on accède aux pensées/infos",
            "explanation": "Pourquoi c'est une violation",
            "suggested_fix": "Comment corriger"
        }}
    ],
    "valid": true/false,
    "overall_assessment": "Évaluation globale de la cohérence POV"
}}
"""
        
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        
        try:
            result = json.loads(response)
            result["pov_character"] = pov_character
            result["pov_type"] = pov_type
            return result
        except json.JSONDecodeError:
            logger.error("Failed to parse POV validation response")
            return {
                "pov_character": pov_character,
                "pov_type": pov_type,
                "violations": [],
                "valid": True,
                "error": "Analysis failed",
            }
    
    async def detect_pov_from_text(
        self,
        chapter_text: str,
    ) -> Dict[str, Any]:
        """
        Auto-detect POV type and character from text.
        
        Args:
            chapter_text: The chapter content.
            
        Returns:
            Detected POV configuration.
        """
        prompt = f"""Analyse ce texte et détermine le point de vue narratif :

{chapter_text[:2000]}

Retourne JSON :
{{
    "pov_type": "first_person|limited|omniscient|objective",
    "pov_character": "Nom du personnage POV (si applicable)",
    "confidence": 0.0-1.0,
    "indicators": ["Indices ayant permis la détection"]
}}
"""
        
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "pov_type": "unknown",
                "pov_character": None,
                "confidence": 0.0,
            }
```

---

## 7. Tests et Validation

### 7.1 Structure des Tests

```
backend/tests/
├── test_coherence/
│   ├── __init__.py
│   ├── test_chekhov_tracker.py
│   ├── test_recursive_memory.py
│   ├── test_semantic_validator.py
│   ├── test_character_drift.py
│   ├── test_voice_analyzer.py
│   ├── test_pov_validator.py
│   └── test_coherence_tasks.py
├── test_pipeline_integration.py
└── conftest.py
```

### 7.2 Fixtures Communes

**Fichier** : `backend/tests/conftest.py` (AJOUTER)
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = MagicMock()
    client.chat = AsyncMock(return_value='{"result": "test"}')
    return client

@pytest.fixture
def mock_memory_service():
    """Mock memory service for testing."""
    service = MagicMock()
    service.neo4j_driver = MagicMock()
    service.chroma_client = MagicMock()
    service.query_character_evolution = MagicMock(return_value={})
    service.retrieve_style_memory = MagicMock(return_value=[])
    return service

@pytest.fixture
def sample_chapter_text():
    """Sample chapter text for testing."""
    return """
    Marie entra dans la pièce, la clé ancienne serrée dans sa main.
    "Je dois trouver ce coffre," murmura-t-elle.
    Jean la regardait depuis l'ombre, inquiet. Il savait que cette quête
    la mènerait vers des dangers qu'elle ne pouvait imaginer.
    "Tu es sûre de vouloir continuer ?" demanda-t-il.
    Marie hocha la tête, déterminée. Depuis la mort de son père,
    rien ne pouvait plus l'arrêter.
    """

@pytest.fixture
def sample_project_metadata():
    """Sample project metadata for testing."""
    return {
        "concept": {
            "data": {
                "premise": "Une jeune femme découvre un secret familial",
                "tone": "mystérieux",
                "tropes": ["quête", "secret familial"],
            }
        },
        "plan": {
            "data": {
                "arcs": [
                    {
                        "id": "arc1",
                        "title": "La Découverte",
                        "chapter_start": 1,
                        "chapter_end": 5,
                    }
                ],
                "chapters": []
            }
        },
        "story_bible": {
            "characters": [
                {"name": "Marie", "traits": ["déterminée", "curieuse"]},
                {"name": "Jean", "traits": ["protecteur", "secret"]},
            ]
        },
        "chekhov_guns": [],
        "intentional_mysteries": [],
    }
```

### 7.3 Critères de Validation par Tâche

| Tâche | Tests Requis | Critères de Succès |
|-------|--------------|-------------------|
| 1.1 Unification Pipeline | `test_validate_continuity_uses_analyst` | ConsistencyAnalyst appelé, résultat transformé |
| 1.2 Tracking Objets | `test_object_availability`, `test_location_consistency` | Détection objets perdus, voyages manquants |
| 1.3 Chekhov Tracker | `test_extract_guns`, `test_check_unresolved` | Extraction correcte, alertes appropriées |
| 2.1 Mémoire Récursive | `test_build_context`, `test_update_after_chapter` | Contexte pyramidal généré, mises à jour |
| 2.2 Validation Sémantique | `test_detect_contradictions` | Contradictions sémantiques détectées |
| 2.3 Promotion Facts | `test_promote_facts` | Faits fréquents promus |
| 3.1 Character Drift | `test_analyze_drift` | Dérives non justifiées détectées |
| 3.2 Voice Analyzer | `test_voice_consistency` | Score cohérence calculé |
| 3.3 Mystères Intentionnels | `test_filter_mysteries` | Contradictions intentionnelles filtrées |
| 4.1 POV Validator | `test_pov_violations` | Violations POV détectées |

---

## 8. Migrations de Base de Données

### 8.1 Nouvelle Migration Alembic

**Fichier** : `backend/alembic/versions/xxx_add_coherence_fields.py`

```python
"""Add coherence tracking fields to project metadata

Revision ID: xxx_add_coherence
Revises: previous_revision
Create Date: 2024-XX-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'xxx_add_coherence'
down_revision = 'previous_revision'  # Replace with actual
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Note: project_metadata is JSONB, so we just document the expected structure
    # No actual schema change needed, but we can add indexes if needed
    
    # Add GIN index for faster JSONB queries on coherence data
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_project_metadata_chekhov 
        ON projects USING GIN ((project_metadata -> 'chekhov_guns'))
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_project_metadata_mysteries 
        ON projects USING GIN ((project_metadata -> 'story_bible' -> 'intentional_mysteries'))
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_project_metadata_chekhov")
    op.execute("DROP INDEX IF EXISTS idx_project_metadata_mysteries")
```

### 8.2 Structure JSONB Attendue

```python
# Structure project_metadata après implémentation
{
    "concept": {...},
    "plan": {...},
    "continuity": {...},
    "story_bible": {
        "characters": [...],
        "locations": [...],
        "world_rules": [...],
        "timeline": [...],
        "glossary": {...},
        "intentional_mysteries": [  # NOUVEAU
            {
                "id": "mystery_1",
                "description": "Jean ment sur son passé",
                "contradiction_type": "lie",
                "introduced_chapter": 3,
                "resolution_planned_chapter": 15,
                "characters_involved": ["Jean"],
                "hints_to_drop": ["Mention de sa cicatrice", "Hésitation sur dates"],
            }
        ],
    },
    "chekhov_guns": [  # NOUVEAU
        {
            "element": "Clé ancienne",
            "element_type": "object",
            "expectation": "Ouvrira un coffre secret",
            "introduced_chapter": 1,
            "urgency": 8,
            "resolved": False,
            "hints_dropped": [
                {"hint": "Brille mystérieusement", "chapter": 1}
            ],
        }
    ],
    "recursive_memory": {  # NOUVEAU
        "global_synopsis": "...",
        "arc_summaries": {
            "arc1": "...",
        },
        "synopsis_updated_at": "2024-XX-XX",
    },
}
```

---

## 📋 Checklist d'Implémentation pour Agents IA

### Phase 1 : Fondations
- [ ] **TÂCHE 1.1** : Modifier `writing_pipeline.py` pour utiliser `ConsistencyAnalyst`
- [ ] **TÂCHE 1.2** : Ajouter tracking objets/localisation dans `memory_service.py`
- [ ] **TÂCHE 1.3** : Créer `coherence/chekhov_tracker.py`
- [ ] Créer `coherence/__init__.py`
- [ ] Ajouter variables d'environnement dans `.env.example`
- [ ] Écrire tests pour Phase 1

### Phase 2 : Mémoire Avancée
- [ ] **TÂCHE 2.1** : Créer `coherence/recursive_memory.py`
- [ ] **TÂCHE 2.2** : Créer `coherence/semantic_validator.py`
- [ ] **TÂCHE 2.3** : Créer `tasks/coherence_tasks.py` avec promotion
- [ ] Ajouter `sentence-transformers` à `requirements.txt`
- [ ] Intégrer mémoire récursive dans pipeline
- [ ] Écrire tests pour Phase 2

### Phase 3 : Qualité Narrative
- [ ] **TÂCHE 3.1** : Créer `coherence/character_drift.py`
- [ ] **TÂCHE 3.2** : Créer `coherence/voice_analyzer.py`
- [ ] **TÂCHE 3.3** : Modifier `consistency_analyst.py` pour mystères
- [ ] Créer `schemas/coherence.py`
- [ ] Écrire tests pour Phase 3

### Phase 4 : Features Avancées
- [ ] **TÂCHE 4.1** : Créer `coherence/pov_validator.py`
- [ ] Créer `api/v1/endpoints/coherence.py` (endpoints API)
- [ ] Créer migration Alembic
- [ ] Écrire tests pour Phase 4
- [ ] Documentation utilisateur

---

## 📚 Références Techniques

### Dépendances à Ajouter
```txt
# backend/requirements.txt
sentence-transformers>=2.2.0
numpy>=1.24.0
```

### Imports Standards par Module
```python
# Services coherence
from app.services.coherence.chekhov_tracker import ChekhovTracker
from app.services.coherence.recursive_memory import RecursiveMemory
from app.services.coherence.semantic_validator import SemanticValidator
from app.services.coherence.character_drift import CharacterDriftDetector
from app.services.coherence.voice_analyzer import VoiceConsistencyAnalyzer
from app.services.coherence.pov_validator import POVValidator
```

### Configuration Settings
```python
# backend/app/core/config.py - Ajouter
class Settings(BaseSettings):
    # ... existant ...
    
    # Coherence settings
    RECURSIVE_MEMORY_ENABLED: bool = True
    RECURSIVE_MEMORY_RECENT_CHAPTERS: int = 5
    RECURSIVE_MEMORY_ARC_SUMMARY_WORDS: int = 500
    RECURSIVE_MEMORY_GLOBAL_SYNOPSIS_WORDS: int = 1000
    
    CHEKHOV_TRACKER_ENABLED: bool = True
    CHEKHOV_MAX_UNRESOLVED_CHAPTERS: int = 15
    CHEKHOV_URGENCY_THRESHOLD: int = 7
    
    VOICE_ANALYZER_ENABLED: bool = True
    VOICE_CONSISTENCY_THRESHOLD: float = 0.75
    VOICE_MIN_DIALOGUES_FOR_ANALYSIS: int = 5
    
    CHARACTER_DRIFT_ENABLED: bool = True
    CHARACTER_DRIFT_THRESHOLD: float = 0.6
    
    POV_VALIDATOR_ENABLED: bool = True
    POV_DEFAULT_TYPE: str = "limited"
    
    SEMANTIC_VALIDATOR_ENABLED: bool = True
    SEMANTIC_CONFLICT_THRESHOLD: float = 0.8
    
    FACT_PROMOTION_THRESHOLD: int = 3
    FACT_PROMOTION_SCHEDULE_HOURS: int = 24
```

---

**FIN DU DOCUMENT D'IMPLÉMENTATION**
