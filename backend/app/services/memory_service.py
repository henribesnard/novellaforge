"""Memory and continuity service for long-form novels."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from app.core.config import settings
from app.services.llm_client import DeepSeekClient

try:
    from neo4j import GraphDatabase
except ImportError:  # pragma: no cover - optional dependency
    GraphDatabase = None

try:
    import chromadb
except ImportError:  # pragma: no cover - optional dependency
    chromadb = None


class MemoryService:
    """Hybrid memory service with optional Neo4j and ChromaDB support."""

    def __init__(self) -> None:
        self.llm_client = DeepSeekClient()
        self.neo4j_driver = self._init_neo4j()
        self.chroma_client = self._init_chroma()

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
        if settings.CHROMA_HOST and settings.CHROMA_PORT:
            return chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)

    async def extract_facts(self, chapter_text: str) -> Dict[str, Any]:
        prompt = (
            "Extract continuity facts as JSON with keys: summary, characters, locations, relations, events.\n"
            "characters: list of {name, role, status}\n"
            "locations: list of {name, description}\n"
            "relations: list of {from, to, type, detail}\n"
            "events: list of {name, summary}\n"
            "Return JSON only.\n\n"
            f"Chapter:\n{chapter_text[:6000]}"
        )
        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        return self._safe_json(response)

    def merge_facts(self, metadata: Dict[str, Any], facts: Dict[str, Any]) -> Dict[str, Any]:
        continuity = metadata.get("continuity") if isinstance(metadata.get("continuity"), dict) else {}
        continuity.setdefault("characters", [])
        continuity.setdefault("locations", [])
        continuity.setdefault("relations", [])
        continuity.setdefault("events", [])

        continuity["characters"] = self._merge_named(
            continuity["characters"], facts.get("characters", [])
        )
        continuity["locations"] = self._merge_named(
            continuity["locations"], facts.get("locations", [])
        )
        continuity["relations"] = self._merge_relations(
            continuity["relations"], facts.get("relations", [])
        )
        continuity["events"] = self._merge_named(
            continuity["events"], facts.get("events", [])
        )
        continuity["updated_at"] = datetime.utcnow().isoformat()
        metadata["continuity"] = continuity
        return metadata

    def build_context_block(self, metadata: Dict[str, Any]) -> str:
        continuity = metadata.get("continuity") if isinstance(metadata.get("continuity"), dict) else {}
        characters = continuity.get("characters", [])
        locations = continuity.get("locations", [])
        relations = continuity.get("relations", [])
        events = continuity.get("events", [])
        return (
            "CONTINUITY FACTS:\n"
            f"Characters: {self._stringify_items(characters)}\n"
            f"Locations: {self._stringify_items(locations)}\n"
            f"Relations: {self._stringify_relations(relations)}\n"
            f"Events: {self._stringify_items(events)}\n"
        )

    def update_neo4j(self, facts: Dict[str, Any]) -> None:
        if not self.neo4j_driver:
            return
        database = settings.NEO4J_DATABASE or None
        with self.neo4j_driver.session(database=database) as session:
            for char in facts.get("characters", []):
                name = char.get("name")
                if not name:
                    continue
                session.run(
                    "MERGE (c:Character {name: $name}) "
                    "SET c.role = $role, c.status = $status",
                    name=name,
                    role=char.get("role"),
                    status=char.get("status"),
                )
            for loc in facts.get("locations", []):
                name = loc.get("name")
                if not name:
                    continue
                session.run(
                    "MERGE (l:Location {name: $name}) SET l.description = $description",
                    name=name,
                    description=loc.get("description"),
                )
            for rel in facts.get("relations", []):
                source = rel.get("from")
                target = rel.get("to")
                if not source or not target:
                    continue
                session.run(
                    "MATCH (a:Character {name: $source}), (b:Character {name: $target}) "
                    "MERGE (a)-[r:RELATION {type: $type}]->(b) "
                    "SET r.detail = $detail",
                    source=source,
                    target=target,
                    type=rel.get("type"),
                    detail=rel.get("detail"),
                )
            for event in facts.get("events", []):
                name = event.get("name")
                if not name:
                    continue
                session.run(
                    "MERGE (e:Event {name: $name}) SET e.summary = $summary",
                    name=name,
                    summary=event.get("summary"),
                )

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
                return payload
        except json.JSONDecodeError:
            pass
        return {"summary": "", "characters": [], "locations": [], "relations": [], "events": []}

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
                by_key[rel_key] = {**by_key[rel_key], **rel}
            else:
                by_key[rel_key] = rel
        return list(by_key.values())

    def _stringify_items(self, items: List[Dict[str, Any]]) -> str:
        names = [item.get("name") for item in items if item.get("name")]
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
