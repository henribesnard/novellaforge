"""Memory and continuity service for long-form novels."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import json
import logging
import warnings

from app.core.config import settings

# Suppress Neo4j warnings about missing property keys in schema
# These occur when querying for properties that don't exist yet in the graph
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="neo4j",
    message=".*property key.*not in the database.*",
)
from app.services.llm_client import DeepSeekClient

try:
    from neo4j import GraphDatabase as Neo4jGraphDatabase  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency
    Neo4jGraphDatabase = None  # type: ignore[assignment]

GraphDatabase: Optional[Any] = Neo4jGraphDatabase

try:
    import chromadb as chromadb_module
except ImportError:  # pragma: no cover - optional dependency
    chromadb_module = None  # type: ignore[assignment]

chromadb: Optional[Any] = chromadb_module

try:
    from chromadb.config import Settings as ChromaSettings  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency
    ChromaSettings = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)

OBJECT_STATUSES = ["possessed", "lost", "destroyed", "hidden", "transferred"]
CHARACTER_LOCATIONS = ["known", "unknown", "traveling"]

_NEO4J_CACHE = {}
_NEO4J_CACHE_TTL = timedelta(minutes=10)
_NEO4J_SCHEMA_READY = False


class MemoryService:
    """Hybrid memory service with optional Neo4j and ChromaDB support."""

    def __init__(
        self,
        llm_client: Optional[DeepSeekClient] = None,
        neo4j_driver: Optional[Any] = None,
        chroma_client: Optional[Any] = None,
        neo4j_async_client: Optional[Any] = None,
    ) -> None:
        self.llm_client = llm_client or DeepSeekClient()
        self.neo4j_driver = neo4j_driver if neo4j_driver is not None else self._init_neo4j()
        self.chroma_client = chroma_client if chroma_client is not None else self._init_chroma()
        self.neo4j_async_client = neo4j_async_client
        if self.neo4j_driver:
            self._ensure_neo4j_schema()

    def _init_neo4j(self):
        if not settings.NEO4J_URI or not GraphDatabase:
            return None
        auth = None
        if settings.NEO4J_USER and settings.NEO4J_PASSWORD:
            auth = (settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        return GraphDatabase.driver(settings.NEO4J_URI, auth=auth)

    def _init_chroma(self):
        if not chromadb:
            return None
        chroma_settings = None
        if ChromaSettings is not None:
            chroma_settings = ChromaSettings(
                anonymized_telemetry=settings.CHROMA_ANONYMIZED_TELEMETRY
            )
        if settings.CHROMA_HOST and settings.CHROMA_PORT:
            return chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
                settings=chroma_settings,
            )
        return chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=chroma_settings,
        )

    def _ensure_neo4j_schema(self) -> None:
        global _NEO4J_SCHEMA_READY
        if _NEO4J_SCHEMA_READY or not self.neo4j_driver:
            return
        database = settings.NEO4J_DATABASE or None
        try:
            with self.neo4j_driver.session(database=database) as session:
                session.run(
                    "CREATE INDEX event_project_id IF NOT EXISTS "
                    "FOR (e:Event) ON (e.project_id)"
                )
                session.run(
                    "CREATE INDEX event_unresolved IF NOT EXISTS "
                    "FOR (e:Event) ON (e.unresolved)"
                )
                session.run(
                    "CREATE INDEX event_last_mentioned IF NOT EXISTS "
                    "FOR (e:Event) ON (e.last_mentioned_chapter)"
                )
            _NEO4J_SCHEMA_READY = True
        except Exception:
            logger.warning("Neo4j schema initialization failed.", exc_info=True)

    async def extract_facts(self, chapter_text: str) -> Dict[str, Any]:
        """Extract enriched continuity facts from chapter text."""
        if not chapter_text or not chapter_text.strip():
            return self._empty_facts()

        chunks = self._select_extraction_chunks(chapter_text, max_chars=10000)
        merged = self._empty_facts()
        for chunk in chunks:
            chunk_facts = await self._extract_facts_chunk(chunk)
            merged = self._merge_fact_payloads(merged, chunk_facts)
        return merged

    def merge_facts(self, metadata: Dict[str, Any], facts: Dict[str, Any]) -> Dict[str, Any]:
        continuity_raw = metadata.get("continuity")
        continuity: Dict[str, Any] = continuity_raw if isinstance(continuity_raw, dict) else {}
        continuity.setdefault("characters", [])
        continuity.setdefault("locations", [])
        continuity.setdefault("relations", [])
        continuity.setdefault("events", [])

        continuity["characters"] = self._merge_characters(
            continuity["characters"], facts.get("characters", [])
        )
        continuity["locations"] = self._merge_locations(
            continuity["locations"], facts.get("locations", [])
        )
        continuity["relations"] = self._merge_relations(
            continuity["relations"], facts.get("relations", [])
        )
        continuity["events"] = self._merge_events(
            continuity["events"], facts.get("events", [])
        )
        continuity["updated_at"] = datetime.utcnow().isoformat()
        metadata["continuity"] = continuity
        return metadata

    def build_context_block(self, metadata: Dict[str, Any]) -> str:
        continuity_raw = metadata.get("continuity")
        continuity: Dict[str, Any] = continuity_raw if isinstance(continuity_raw, dict) else {}
        characters = continuity.get("characters", [])
        if not isinstance(characters, list):
            characters = []
        locations = continuity.get("locations", [])
        if not isinstance(locations, list):
            locations = []
        relations = continuity.get("relations", [])
        if not isinstance(relations, list):
            relations = []
        events = continuity.get("events", [])
        if not isinstance(events, list):
            events = []
        lines = ["CONTINUITY FACTS:", ""]
        lines.append("Characters:")
        if characters:
            for item in characters:
                lines.append(self._format_character(item))
        else:
            lines.append("- none")

        lines.append("")
        lines.append("Locations:")
        if locations:
            for item in locations:
                lines.append(self._format_location(item))
        else:
            lines.append("- none")

        lines.append("")
        lines.append("Relations:")
        if relations:
            for item in relations:
                lines.append(self._format_relation(item))
        else:
            lines.append("- none")

        lines.append("")
        lines.append("Events:")
        if events:
            for item in events:
                lines.append(self._format_event(item))
        else:
            lines.append("- none")

        context_block = "\n".join(lines).strip()
        if self._word_count(context_block) < 200:
            context_block = f"{context_block}\n\n{self._build_padding_note()}".strip()
        return context_block

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

    def update_neo4j(
        self,
        facts: Dict[str, Any],
        project_id: Optional[str] = None,
        chapter_index: Optional[int] = None,
    ) -> None:
        """Update Neo4j graph nodes with temporal attributes."""
        if not self.neo4j_driver:
            return
        timestamp = datetime.utcnow().isoformat()
        database = settings.NEO4J_DATABASE or None
        base_chapter = self._resolve_chapter_index(chapter_index)
        with self.neo4j_driver.session(database=database) as session:
            for char in facts.get("characters", []):
                name = char.get("name")
                if not name:
                    continue
                char_chapter = self._resolve_chapter_index(char.get("last_seen_chapter"), base_chapter)
                status = char.get("status")
                status_entry = []
                if status and isinstance(char_chapter, int):
                    status_entry = [{"status": status, "chapter": char_chapter, "timestamp": timestamp}]
                params = {
                    "name": name,
                    "role": char.get("role"),
                    "status": status,
                    "chapter_index": char_chapter,
                    "timestamp": timestamp,
                    "status_entry": status_entry,
                }
                if project_id:
                    params["project_id"] = project_id
                    session.run(
                        "MERGE (c:Character {name: $name, project_id: $project_id}) "
                        "ON CREATE SET c.created_chapter = $chapter_index, c.first_appearance = $timestamp "
                        "SET c.role = $role, c.status = $status, c.last_seen_chapter = $chapter_index, "
                        "c.last_updated = $timestamp, c.project_id = $project_id, "
                        "c.status_history = coalesce(c.status_history, []) + $status_entry",
                        **params,
                    )
                else:
                    session.run(
                        "MERGE (c:Character {name: $name}) "
                        "ON CREATE SET c.created_chapter = $chapter_index, c.first_appearance = $timestamp "
                        "SET c.role = $role, c.status = $status, c.last_seen_chapter = $chapter_index, "
                        "c.last_updated = $timestamp, "
                        "c.status_history = coalesce(c.status_history, []) + $status_entry",
                        **params,
                    )
            for loc in facts.get("locations", []):
                name = loc.get("name")
                if not name:
                    continue
                loc_chapter = self._resolve_chapter_index(loc.get("last_mentioned_chapter"), base_chapter)
                params = {
                    "name": name,
                    "description": loc.get("description"),
                    "rules": self._normalize_list(loc.get("rules")),
                    "timeline_markers": self._normalize_list(loc.get("timeline_markers")),
                    "atmosphere": loc.get("atmosphere"),
                    "chapter_index": loc_chapter,
                    "timestamp": timestamp,
                }
                if project_id:
                    params["project_id"] = project_id
                    session.run(
                        "MERGE (l:Location {name: $name, project_id: $project_id}) "
                        "ON CREATE SET l.created_chapter = $chapter_index, l.first_appearance = $timestamp "
                        "SET l.description = $description, l.rules = $rules, l.timeline_markers = $timeline_markers, "
                        "l.atmosphere = $atmosphere, l.last_mentioned_chapter = $chapter_index, "
                        "l.last_updated = $timestamp, l.project_id = $project_id",
                        **params,
                    )
                else:
                    session.run(
                        "MERGE (l:Location {name: $name}) "
                        "ON CREATE SET l.created_chapter = $chapter_index, l.first_appearance = $timestamp "
                        "SET l.description = $description, l.rules = $rules, l.timeline_markers = $timeline_markers, "
                        "l.atmosphere = $atmosphere, l.last_mentioned_chapter = $chapter_index, "
                        "l.last_updated = $timestamp",
                        **params,
                    )
            for rel in facts.get("relations", []):
                source = rel.get("from")
                target = rel.get("to")
                rel_type = rel.get("type")
                if not source or not target or not rel_type:
                    continue
                rel_chapter = self._resolve_chapter_index(rel.get("start_chapter"), base_chapter)
                current_state = rel.get("current_state")
                evolution_entry = []
                if current_state and isinstance(rel_chapter, int):
                    evolution_entry = [{"state": current_state, "chapter": rel_chapter, "timestamp": timestamp}]
                params = {
                    "source": source,
                    "target": target,
                    "type": rel_type,
                    "detail": rel.get("detail"),
                    "current_state": current_state,
                    "evolution": rel.get("evolution"),
                    "start_chapter": rel_chapter,
                    "timestamp": timestamp,
                    "evolution_entry": evolution_entry,
                }
                if project_id:
                    params["project_id"] = project_id
                    session.run(
                        "MERGE (a:Character {name: $source, project_id: $project_id}) "
                        "MERGE (b:Character {name: $target, project_id: $project_id}) "
                        "MERGE (a)-[r:RELATION {type: $type}]->(b) "
                        "SET r.detail = $detail, r.current_state = $current_state, "
                        "r.evolution = $evolution, r.start_chapter = $start_chapter, "
                        "r.last_updated = $timestamp, r.project_id = $project_id, "
                        "r.evolution_history = coalesce(r.evolution_history, []) + $evolution_entry",
                        **params,
                    )
                else:
                    session.run(
                        "MERGE (a:Character {name: $source}) "
                        "MERGE (b:Character {name: $target}) "
                        "MERGE (a)-[r:RELATION {type: $type}]->(b) "
                        "SET r.detail = $detail, r.current_state = $current_state, "
                        "r.evolution = $evolution, r.start_chapter = $start_chapter, "
                        "r.last_updated = $timestamp, "
                        "r.evolution_history = coalesce(r.evolution_history, []) + $evolution_entry",
                        **params,
                    )
            for event in facts.get("events", []):
                name = event.get("name")
                if not name:
                    continue
                event_chapter = self._resolve_chapter_index(event.get("chapter_index"), base_chapter)
                unresolved_threads = self._normalize_list(event.get("unresolved_threads"))
                unresolved = bool(unresolved_threads)
                params = {
                    "name": name,
                    "summary": event.get("summary"),
                    "time_reference": event.get("time_reference"),
                    "impact": event.get("impact"),
                    "chapter_index": event_chapter,
                    "timestamp": timestamp,
                    "unresolved": unresolved,
                    "unresolved_threads": unresolved_threads,
                }
                if project_id:
                    params["project_id"] = project_id
                    session.run(
                        "MERGE (e:Event {name: $name, project_id: $project_id}) "
                        "ON CREATE SET e.created_chapter = $chapter_index, e.first_appearance = $timestamp "
                        "SET e.summary = $summary, e.time_reference = $time_reference, "
                        "e.impact = $impact, e.last_mentioned_chapter = $chapter_index, "
                        "e.unresolved = $unresolved, e.unresolved_threads = $unresolved_threads, "
                        "e.last_updated = $timestamp, e.project_id = $project_id",
                        **params,
                    )
                else:
                    session.run(
                        "MERGE (e:Event {name: $name}) "
                        "ON CREATE SET e.created_chapter = $chapter_index, e.first_appearance = $timestamp "
                        "SET e.summary = $summary, e.time_reference = $time_reference, "
                        "e.impact = $impact, e.last_mentioned_chapter = $chapter_index, "
                        "e.unresolved = $unresolved, e.unresolved_threads = $unresolved_threads, "
                        "e.last_updated = $timestamp",
                        **params,
                    )

    async def update_neo4j_async(
        self,
        facts: Dict[str, Any],
        project_id: Optional[str] = None,
        chapter_index: Optional[int] = None,
    ) -> None:
        """Async wrapper for Neo4j updates (uses thread fallback)."""
        await asyncio.to_thread(self.update_neo4j, facts, project_id, chapter_index)

    def query_character_evolution(
        self, character_name: str, project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch the evolution of a character from Neo4j."""
        if not self.neo4j_driver:
            return {}
        database = settings.NEO4J_DATABASE or None
        if project_id:
            query = (
                "MATCH (c:Character {name: $name, project_id: $project_id}) "
                "RETURN c.name as name, c.status_history as status_history, "
                "c.first_appearance as first_appearance, c.last_seen_chapter as last_seen_chapter"
            )
            params = {"name": character_name, "project_id": project_id}
        else:
            query = (
                "MATCH (c:Character {name: $name}) "
                "RETURN c.name as name, c.status_history as status_history, "
                "c.first_appearance as first_appearance, c.last_seen_chapter as last_seen_chapter"
            )
            params = {"name": character_name}
        with self.neo4j_driver.session(database=database) as session:
            result = session.run(query, **params)
            record = result.single()
            return dict(record) if record else {}

    def detect_character_contradictions(
        self, character_name: str, project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Detect contradictions in character status history with caching."""
        cache_key = f"contradictions:{project_id}:{character_name}"
        cached = _NEO4J_CACHE.get(cache_key)
        if cached and datetime.utcnow() - cached["timestamp"] < _NEO4J_CACHE_TTL:
            return cached["result"]

        if not self.neo4j_driver:
            return []
        
        database = settings.NEO4J_DATABASE or None
        if project_id:
            match_clause = "MATCH (c:Character {name: $name, project_id: $project_id})"
        else:
            match_clause = "MATCH (c:Character {name: $name})"
        query = (
            f"{match_clause} "
            "UNWIND coalesce(c.status_history, []) as history "
            "WITH c, history "
            "ORDER BY history.chapter "
            "WITH c, collect(history) as ordered_history "
            "UNWIND range(0, size(ordered_history) - 2) as i "
            "WITH c, ordered_history[i] as current, ordered_history[i + 1] as next "
            "WHERE current.status = 'dead' AND next.status IN ['alive', 'active', 'healthy'] "
            "RETURN {"
            "  character: c.name, "
            "  contradiction: 'resurrection', "
            "  from_chapter: current.chapter, "
            "  from_status: current.status, "
            "  to_chapter: next.chapter, "
            "  to_status: next.status"
            "} as issue"
        )
        params = {"name": character_name}
        if project_id:
            params["project_id"] = project_id
            
        result_list = []
        try:
            with self.neo4j_driver.session(database=database) as session:
                result = session.run(query, **params)
                result_list = [dict(record["issue"]) for record in result]
        except Exception as e:
            logger.error(f"Error checking contradictions for {character_name}: {e}")
            return []

        _NEO4J_CACHE[cache_key] = {
            "result": result_list,
            "timestamp": datetime.utcnow()
        }
        return result_list

    def query_relationship_evolution(
        self, char_a: str, char_b: str, project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch the evolution of a relationship between two characters."""
        if not self.neo4j_driver:
            return []
        database = settings.NEO4J_DATABASE or None
        if project_id:
            query = (
                "MATCH (a:Character {name: $char_a, project_id: $project_id})"
                "-[r:RELATION]->"
                "(b:Character {name: $char_b, project_id: $project_id}) "
                "RETURN r.type as type, r.start_chapter as start_chapter, "
                "r.evolution_history as evolution, r.current_state as current_state"
            )
            params = {"char_a": char_a, "char_b": char_b, "project_id": project_id}
        else:
            query = (
                "MATCH (a:Character {name: $char_a})-[r:RELATION]->(b:Character {name: $char_b}) "
                "RETURN r.type as type, r.start_chapter as start_chapter, "
                "r.evolution_history as evolution, r.current_state as current_state"
            )
            params = {"char_a": char_a, "char_b": char_b}
        with self.neo4j_driver.session(database=database) as session:
            result = session.run(query, **params)
            return [dict(record) for record in result]

    def find_orphaned_plot_threads(
        self, current_chapter: Optional[int], project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find unresolved plot threads not mentioned for 10+ chapters."""
        if not self.neo4j_driver:
            return []
        chapter_value = self._resolve_chapter_index(current_chapter)
        if chapter_value is None:
            return []
        cutoff = chapter_value - 10
        database = settings.NEO4J_DATABASE or None
        with self.neo4j_driver.session(database=database) as session:
            if project_id:
                count_result = session.run(
                    "MATCH (e:Event {project_id: $project_id}) RETURN count(e) as total",
                    project_id=project_id,
                ).single()
            else:
                count_result = session.run(
                    "MATCH (e:Event) RETURN count(e) as total"
                ).single()
            total = count_result.get("total") if count_result else 0
            if not total:
                return []
        if project_id:
            query = (
                "MATCH (e:Event {project_id: $project_id}) "
                "WHERE e.unresolved = true AND e.last_mentioned_chapter < $cutoff "
                "RETURN e.name as event, e.last_mentioned_chapter as last_mentioned, e.summary as summary "
                "ORDER BY e.last_mentioned_chapter"
            )
            params = {"project_id": project_id, "cutoff": cutoff}
        else:
            query = (
                "MATCH (e:Event) "
                "WHERE e.unresolved = true AND e.last_mentioned_chapter < $cutoff "
                "RETURN e.name as event, e.last_mentioned_chapter as last_mentioned, e.summary as summary "
                "ORDER BY e.last_mentioned_chapter"
            )
            params = {"cutoff": cutoff}
        with self.neo4j_driver.session(database=database) as session:
            result = session.run(query, **params)
            return [dict(record) for record in result]

    def export_graph_for_visualization(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Export Neo4j nodes and edges for visualization."""
        if not self.neo4j_driver:
            return {"nodes": [], "edges": []}
        database = settings.NEO4J_DATABASE or None
        if project_id:
            node_query = (
                "MATCH (n) WHERE n.project_id = $project_id "
                "RETURN id(n) as id, labels(n) as labels, n as props"
            )
            edge_query = (
                "MATCH (a)-[r]->(b) WHERE a.project_id = $project_id AND b.project_id = $project_id "
                "RETURN id(a) as source, id(b) as target, type(r) as type, r as props"
            )
            params = {"project_id": project_id}
        else:
            node_query = "MATCH (n) RETURN id(n) as id, labels(n) as labels, n as props"
            edge_query = "MATCH (a)-[r]->(b) RETURN id(a) as source, id(b) as target, type(r) as type, r as props"
            params = {}
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        with self.neo4j_driver.session(database=database) as session:
            for record in session.run(node_query, **params):
                labels = record.get("labels") or []
                props = record.get("props")
                props_dict = dict(props) if isinstance(props, dict) or props is not None else {}
                label = props_dict.get("name") or props_dict.get("title") or ""
                node_type = labels[0] if labels else "Node"
                nodes.append(
                    {
                        "id": str(record.get("id")),
                        "label": label,
                        "type": node_type,
                        "properties": props_dict,
                    }
                )
            for record in session.run(edge_query, **params):
                props = record.get("props")
                props_dict = dict(props) if isinstance(props, dict) or props is not None else {}
                edges.append(
                    {
                        "source": str(record.get("source")),
                        "target": str(record.get("target")),
                        "type": record.get("type"),
                        "properties": props_dict,
                    }
                )
        return {"nodes": nodes, "edges": edges}

    def store_style_memory(
        self,
        project_id: str,
        chapter_id: str,
        chapter_text: str,
        summary: Optional[str],
    ) -> None:
        if not self.chroma_client:
            return
        collection_name = f"{settings.CHROMA_COLLECTION_PREFIX}-{project_id}"
        collection = self.chroma_client.get_or_create_collection(collection_name)
        collection.add(
            documents=[chapter_text],
            ids=[chapter_id],
            metadatas=[{"summary": summary or "", "project_id": project_id}],
        )

    def retrieve_style_memory(self, project_id: str, query: str, top_k: int = 3) -> List[str]:
        if not self.chroma_client:
            return []
        collection_name = f"{settings.CHROMA_COLLECTION_PREFIX}-{project_id}"
        collection = self.chroma_client.get_or_create_collection(collection_name)
        results = collection.query(query_texts=[query], n_results=top_k)
        return results.get("documents", [[]])[0]

    def _safe_json(self, text: str) -> Dict[str, Any]:
        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                return self._normalize_facts_payload(payload)
        except json.JSONDecodeError:
            pass
        return self._empty_facts()

    def _empty_facts(self) -> Dict[str, Any]:
        return {
            "summary": "", 
            "characters": [], 
            "locations": [], 
            "relations": [], 
            "events": [], 
            "objects": [], 
            "character_locations": []
        }

    def _normalize_facts_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "summary": payload.get("summary") or "",
            "characters": self._ensure_list(payload.get("characters")),
            "locations": self._ensure_list(payload.get("locations")),
            "relations": self._ensure_list(payload.get("relations")),
            "events": self._ensure_list(payload.get("events")),
            "objects": self._ensure_list(payload.get("objects")),
            "character_locations": self._ensure_list(payload.get("character_locations")),
        }

    def _ensure_list(self, value: Any) -> List[Dict[str, Any]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return []

    def _select_extraction_chunks(self, chapter_text: str, max_chars: int) -> List[str]:
        if len(chapter_text) <= max_chars:
            return [chapter_text[:max_chars]]
        start = chapter_text[:max_chars]
        end = chapter_text[-max_chars:]
        return [start, end]

    async def _extract_facts_chunk(self, chapter_text: str) -> Dict[str, Any]:
        prompt = self._build_extraction_prompt(chapter_text)
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        facts = self._safe_json(response)
        if not facts.get("characters") and not facts.get("locations"):
            logger.debug("Memory extraction returned minimal data.")
        return facts

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

    def _merge_fact_payloads(self, current: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        merged = self._empty_facts()
        merged["summary"] = self._merge_summary(current.get("summary"), incoming.get("summary"))
        merged["characters"] = self._merge_characters(
            current.get("characters", []), incoming.get("characters", [])
        )
        merged["locations"] = self._merge_locations(
            current.get("locations", []), incoming.get("locations", [])
        )
        merged["relations"] = self._merge_relations(
            current.get("relations", []), incoming.get("relations", [])
        )
        merged["events"] = self._merge_events(
            current.get("events", []), incoming.get("events", [])
        )
        # Note: objects and character_locations are currently not merged deeply in memory context 
        # but are tracked in Neo4j. We can simply extend the list or pick the latest for context block if needed.
        # For now, we mainly rely on Neo4j for these.
        return merged

    def _merge_summary(self, current: Optional[str], incoming: Optional[str]) -> str:
        current = (current or "").strip()
        incoming = (incoming or "").strip()
        if current and incoming and current != incoming:
            return f"{current} / {incoming}"
        return incoming or current

    def _merge_characters(self, existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_name = {item.get("name"): item for item in existing if item.get("name")}
        for item in incoming:
            name = item.get("name")
            if not name:
                continue
            current = by_name.get(name, {})
            merged = {**current, **item}
            merged["motivations"] = self._merge_unique_list(
                current.get("motivations"), item.get("motivations")
            )
            merged["traits"] = self._merge_unique_list(current.get("traits"), item.get("traits"))
            merged["goals"] = self._merge_unique_list(current.get("goals"), item.get("goals"))
            merged["relationships"] = self._merge_unique_list(
                current.get("relationships"), item.get("relationships")
            )
            merged["last_seen_chapter"] = self._merge_numeric_max(
                current.get("last_seen_chapter"), item.get("last_seen_chapter")
            )
            merged = self._merge_with_temporal_tracking(
                merged,
                current,
                item,
                field="status",
                history_field="status_history",
                chapter_field="last_seen_chapter",
            )
            by_name[name] = merged
        return list(by_name.values())

    def _merge_locations(self, existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_name = {item.get("name"): item for item in existing if item.get("name")}
        for item in incoming:
            name = item.get("name")
            if not name:
                continue
            current = by_name.get(name, {})
            merged = {**current, **item}
            merged["rules"] = self._merge_unique_list(current.get("rules"), item.get("rules"))
            merged["timeline_markers"] = self._merge_unique_list(
                current.get("timeline_markers"), item.get("timeline_markers")
            )
            merged["last_mentioned_chapter"] = self._merge_numeric_max(
                current.get("last_mentioned_chapter"), item.get("last_mentioned_chapter")
            )
            by_name[name] = merged
        return list(by_name.values())

    def _merge_events(self, existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_name = {item.get("name"): item for item in existing if item.get("name")}
        for item in incoming:
            name = item.get("name")
            if not name:
                continue
            current = by_name.get(name, {})
            merged = {**current, **item}
            merged["unresolved_threads"] = self._merge_unique_list(
                current.get("unresolved_threads"), item.get("unresolved_threads")
            )
            merged["chapter_index"] = self._merge_numeric_max(
                current.get("chapter_index"), item.get("chapter_index")
            )
            by_name[name] = merged
        return list(by_name.values())

    def _merge_named(self, existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_name = {item.get("name"): item for item in existing if item.get("name")}
        for item in incoming:
            name = item.get("name")
            if not name:
                continue
            current = by_name.get(name, {})
            merged = {**current, **item}
            by_name[name] = merged
        return list(by_name.values())

    def _merge_relations(self, existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def key(rel: Dict[str, Any]) -> str:
            return f"{rel.get('from')}|{rel.get('to')}|{rel.get('type')}"

        by_key = {key(rel): rel for rel in existing}
        for rel in incoming:
            rel_key = key(rel)
            if rel_key in by_key:
                current = by_key[rel_key]
                merged = {**current, **rel}
                merged["start_chapter"] = self._merge_numeric_min(
                    current.get("start_chapter"), rel.get("start_chapter")
                )
                by_key[rel_key] = merged
            else:
                by_key[rel_key] = rel
        return list(by_key.values())

    def _stringify_items(self, items: List[Dict[str, Any]]) -> str:
        names = [str(item.get("name")) for item in items if item.get("name")]
        return ", ".join(names) if names else "none"

    def _stringify_relations(self, relations: List[Dict[str, Any]]) -> str:
        parts = []
        for rel in relations:
            source = rel.get("from")
            target = rel.get("to")
            rel_type = rel.get("type")
            if source and target and rel_type:
                parts.append(f"{source} -[{rel_type}]-> {target}")
        return "; ".join(parts) if parts else "none"

    def _merge_with_temporal_tracking(
        self,
        merged: Dict[str, Any],
        existing: Dict[str, Any],
        incoming: Dict[str, Any],
        field: str,
        history_field: str,
        chapter_field: str,
    ) -> Dict[str, Any]:
        """Track changes to a field over time by storing a history list."""
        previous = existing.get(field)
        new_value = incoming.get(field)
        history = list(existing.get(history_field) or [])
        if new_value and new_value != previous:
            history.append(
                {
                    "value": new_value,
                    "chapter_index": incoming.get(chapter_field),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        if history:
            merged[history_field] = history
        return merged

    def _merge_unique_list(self, current: Any, incoming: Any) -> List[str]:
        items = []
        items.extend(self._normalize_list(current))
        items.extend(self._normalize_list(incoming))
        seen = set()
        unique = []
        for item in items:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique

    def _normalize_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        raw_items = value if isinstance(value, list) else [value]
        cleaned = []
        for item in raw_items:
            if item is None:
                continue
            if isinstance(item, str):
                text = item.strip()
            else:
                text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned

    def _resolve_chapter_index(self, *values: Any) -> Optional[int]:
        for value in values:
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return None

    def _merge_numeric_max(self, current: Any, incoming: Any) -> Optional[int]:
        values = [value for value in (current, incoming) if isinstance(value, int)]
        return max(values) if values else (incoming if isinstance(incoming, int) else current)

    def _merge_numeric_min(self, current: Any, incoming: Any) -> Optional[int]:
        values = [value for value in (current, incoming) if isinstance(value, int)]
        return min(values) if values else (incoming if isinstance(incoming, int) else current)

    def _format_character(self, item: Dict[str, Any]) -> str:
        name = item.get("name") or "Unknown"
        role = item.get("role") or "unknown"
        status = item.get("status") or "unknown"
        current_state = item.get("current_state") or "not specified"
        motivations = self._format_list(item.get("motivations"))
        traits = self._format_list(item.get("traits"))
        goals = self._format_list(item.get("goals"))
        arc_stage = item.get("arc_stage") or "not specified"
        last_seen = item.get("last_seen_chapter")
        relationships = self._format_list(item.get("relationships"))
        last_seen_text = f"chapter {last_seen}" if isinstance(last_seen, int) else "unknown"
        return (
            f"- {name} (role: {role}) status: {status}. Current state: {current_state}. "
            f"Motivations: {motivations}. Traits: {traits}. Goals: {goals}. "
            f"Arc stage: {arc_stage}. Last seen: {last_seen_text}. "
            f"Relationships: {relationships}."
        )

    def _format_location(self, item: Dict[str, Any]) -> str:
        name = item.get("name") or "Unknown"
        description = item.get("description") or "not specified"
        rules = self._format_list(item.get("rules"))
        markers = self._format_list(item.get("timeline_markers"))
        atmosphere = item.get("atmosphere") or "not specified"
        last_seen = item.get("last_mentioned_chapter")
        last_seen_text = f"chapter {last_seen}" if isinstance(last_seen, int) else "unknown"
        return (
            f"- {name}: {description}. Rules: {rules}. Timeline markers: {markers}. "
            f"Atmosphere: {atmosphere}. Last mentioned: {last_seen_text}."
        )

    def _format_relation(self, item: Dict[str, Any]) -> str:
        source = item.get("from") or "unknown"
        target = item.get("to") or "unknown"
        rel_type = item.get("type") or "unspecified"
        detail = item.get("detail") or "not specified"
        start = item.get("start_chapter")
        start_text = f"chapter {start}" if isinstance(start, int) else "unknown"
        current_state = item.get("current_state") or "not specified"
        evolution = item.get("evolution") or "not specified"
        return (
            f"- {source} -> {target} ({rel_type}). Detail: {detail}. "
            f"Start: {start_text}. Current state: {current_state}. Evolution: {evolution}."
        )

    def _format_event(self, item: Dict[str, Any]) -> str:
        name = item.get("name") or "Unknown"
        summary = item.get("summary") or "not specified"
        chapter_index = item.get("chapter_index")
        chapter_text = f"chapter {chapter_index}" if isinstance(chapter_index, int) else "unknown"
        time_reference = item.get("time_reference") or "not specified"
        impact = item.get("impact") or "not specified"
        unresolved = self._format_list(item.get("unresolved_threads"))
        return (
            f"- {name} ({chapter_text}): {summary}. Time reference: {time_reference}. "
            f"Impact: {impact}. Unresolved threads: {unresolved}."
        )

    def _format_list(self, value: Any) -> str:
        items = self._normalize_list(value)
        return ", ".join(items) if items else "none"

    def _build_padding_note(self) -> str:
        return (
            "Notes de coherence: ce contexte synthese les faits connus et doit guider toute generation. "
            "Si une motivation, un trait ou un objectif n'est pas indique, ne l'invente pas sans lien clair "
            "avec un evenement ou un indice. Maintiens la continuite des statuts (vivant, blesse, disparu) "
            "et explique tout changement important par une cause explicite. Verifie la coherence des relations "
            "et des dynamiques emotionnelles, surtout si elles evoluent rapidement. Respecte les regles du monde "
            "associees aux lieux et note les effets durables des evenements majeurs. Utilise les fils narratifs "
            "non resolus pour entretenir la tension et eviter les contradictions. Si un element est ambigu, "
            "privilegie une formulation prudente ou une transition explicative pour conserver la coherence globale."
        )

    def _word_count(self, text: str) -> int:
        return len(text.split())
