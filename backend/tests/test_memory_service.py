import json

import pytest

from app.services.memory_service import MemoryService
from app.core.config import settings


def test_merge_facts_updates_continuity():
    service = MemoryService.__new__(MemoryService)
    metadata = {
        "continuity": {
            "characters": [{"name": "Lena", "role": "hero", "status": "alive"}],
            "locations": [],
            "relations": [],
            "events": [],
        }
    }
    facts = {
        "summary": "Lena is injured.",
        "characters": [{"name": "Lena", "status": "injured"}],
        "locations": [{"name": "Dock", "description": "Foggy"}],
        "relations": [{"from": "Lena", "to": "Mark", "type": "ally", "detail": "trust"}],
        "events": [{"name": "Ambush", "summary": "Night attack"}],
    }

    updated = service.merge_facts(metadata, facts)
    continuity = updated["continuity"]

    assert continuity["characters"][0]["name"] == "Lena"
    assert continuity["characters"][0]["status"] == "injured"
    assert continuity["locations"][0]["name"] == "Dock"
    assert continuity["relations"][0]["type"] == "ally"
    assert continuity["events"][0]["name"] == "Ambush"
    assert "updated_at" in continuity


@pytest.mark.asyncio
async def test_extract_facts_enriched_schema():
    class DummyClient:
        async def chat(self, *args, **kwargs):
            payload = {
                "summary": "Alice is wounded but determined.",
                "characters": [
                    {
                        "name": "Alice",
                        "role": "protagonist",
                        "status": "injured",
                        "current_state": "wounded but determined",
                        "motivations": ["revenge"],
                        "traits": ["impulsive"],
                        "goals": ["confront Victor"],
                        "arc_stage": "approaching confrontation",
                        "last_seen_chapter": 5,
                        "relationships": ["Victor (enemy)"],
                    }
                ],
                "locations": [
                    {
                        "name": "Dark Forest",
                        "description": "forbidden zone",
                        "rules": ["no magic"],
                        "timeline_markers": ["battle"],
                        "atmosphere": "ominous",
                        "last_mentioned_chapter": 5,
                    }
                ],
                "relations": [
                    {
                        "from": "Alice",
                        "to": "Victor",
                        "type": "enemy",
                        "detail": "seeks revenge",
                        "start_chapter": 1,
                        "current_state": "active",
                        "evolution": "intensified",
                    }
                ],
                "events": [
                    {
                        "name": "Forest Battle",
                        "summary": "Alice is wounded",
                        "chapter_index": 5,
                        "time_reference": "after ambush",
                        "impact": "Alice weakened",
                        "unresolved_threads": ["Victor escaped"],
                    }
                ],
            }
            return json.dumps(payload)

    service = MemoryService.__new__(MemoryService)
    service.llm_client = DummyClient()

    facts = await service.extract_facts("Alice faces Victor in the forest.")

    assert "characters" in facts
    alice = facts["characters"][0]
    assert "motivations" in alice
    assert "current_state" in alice
    assert "traits" in alice
    assert alice["motivations"]
    assert "wounded" in alice["current_state"].lower()


def test_merge_facts_temporal_tracking():
    service = MemoryService.__new__(MemoryService)
    metadata = {
        "continuity": {
            "characters": [
                {"name": "Alice", "status": "healthy", "last_seen_chapter": 1}
            ],
            "locations": [],
            "relations": [],
            "events": [],
        }
    }
    facts = {
        "characters": [
            {"name": "Alice", "status": "injured", "last_seen_chapter": 5}
        ]
    }

    updated = service.merge_facts(metadata, facts)

    alice = updated["continuity"]["characters"][0]
    assert alice["status"] == "injured"
    assert alice["last_seen_chapter"] == 5
    assert alice.get("status_history")
    assert alice["status_history"][-1]["value"] == "injured"


def test_build_context_block_detailed():
    service = MemoryService.__new__(MemoryService)
    metadata = {
        "continuity": {
            "characters": [
                {
                    "name": "Alice",
                    "role": "protagonist",
                    "status": "injured",
                    "current_state": "wounded but determined",
                    "motivations": ["revenge", "protect Bob"],
                    "traits": ["impulsive", "brave"],
                    "goals": ["defeat Victor", "survive the forest"],
                    "arc_stage": "near confrontation",
                    "last_seen_chapter": 12,
                    "relationships": ["Bob (ally)", "Victor (enemy)"],
                }
            ],
            "locations": [
                {
                    "name": "Dark Forest",
                    "description": "forbidden zone",
                    "rules": ["no magic", "spirits whisper"],
                    "timeline_markers": ["battle", "escape"],
                    "atmosphere": "ominous",
                    "last_mentioned_chapter": 11,
                }
            ],
            "relations": [
                {
                    "from": "Alice",
                    "to": "Victor",
                    "type": "enemy",
                    "detail": "seeks revenge",
                    "start_chapter": 1,
                    "current_state": "active",
                    "evolution": "intensified",
                }
            ],
            "events": [
                {
                    "name": "Forest Battle",
                    "summary": "Alice is wounded",
                    "chapter_index": 12,
                    "time_reference": "after the ambush",
                    "impact": "Alice weakened",
                    "unresolved_threads": ["Victor escaped", "mystery blade"],
                }
            ],
        }
    }

    block = service.build_context_block(metadata)

    assert len(block.split()) >= 200
    assert "Alice" in block
    assert "injured" in block
    assert "revenge" in block


def test_select_extraction_chunks_dual_pass():
    service = MemoryService.__new__(MemoryService)
    text = "a" * 25000
    chunks = service._select_extraction_chunks(text, max_chars=10000)

    assert len(chunks) == 2
    assert len(chunks[0]) == 10000
    assert len(chunks[1]) == 10000


def test_merge_unique_list_deduplicates_and_strips():
    service = MemoryService.__new__(MemoryService)
    merged = service._merge_unique_list(["Alpha", " ", None], ["Alpha", "Beta", "beta"])

    assert merged == ["Alpha", "Beta", "beta"]


def test_merge_numeric_helpers():
    service = MemoryService.__new__(MemoryService)

    assert service._merge_numeric_max(2, 5) == 5
    assert service._merge_numeric_max(None, 3) == 3
    assert service._merge_numeric_min(2, 5) == 2
    assert service._merge_numeric_min(None, 3) == 3


def test_merge_with_temporal_tracking_skips_no_change():
    service = MemoryService.__new__(MemoryService)
    existing = {"status": "alive", "status_history": [{"value": "alive"}]}
    incoming = {"status": "alive"}
    merged = service._merge_with_temporal_tracking(
        {"status": "alive"},
        existing,
        incoming,
        field="status",
        history_field="status_history",
        chapter_field="last_seen_chapter",
    )

    assert merged["status"] == "alive"
    assert merged["status_history"] == [{"value": "alive"}]


def test_init_clients_with_neo4j_and_chroma(monkeypatch):
    import app.services.memory_service as memory_service

    class DummyGraphDatabase:
        @staticmethod
        def driver(uri, auth=None):
            return ("driver", uri, auth)

    class DummyChroma:
        class HttpClient:
            def __init__(self, host=None, port=None):
                self.host = host
                self.port = port

        class PersistentClient:
            def __init__(self, path=None):
                self.path = path

    monkeypatch.setattr(memory_service, "GraphDatabase", DummyGraphDatabase)
    monkeypatch.setattr(memory_service, "chromadb", DummyChroma)
    monkeypatch.setattr(settings, "NEO4J_URI", "bolt://localhost")
    monkeypatch.setattr(settings, "NEO4J_USER", "user")
    monkeypatch.setattr(settings, "NEO4J_PASSWORD", "pass")
    monkeypatch.setattr(settings, "CHROMA_HOST", "localhost")
    monkeypatch.setattr(settings, "CHROMA_PORT", 9999)

    service = memory_service.MemoryService()

    assert service.neo4j_driver[0] == "driver"
    assert isinstance(service.chroma_client, DummyChroma.HttpClient)


def test_update_neo4j_runs_queries():
    service = MemoryService.__new__(MemoryService)
    calls = []

    class DummySession:
        def run(self, *args, **kwargs):
            calls.append((args, kwargs))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyDriver:
        def session(self, database=None):
            return DummySession()

    service.neo4j_driver = DummyDriver()

    facts = {
        "characters": [{"name": "Alice", "role": "hero", "status": "alive"}],
        "locations": [{"name": "Dock", "description": "Foggy"}],
        "relations": [{"from": "Alice", "to": "Bob", "type": "ally", "detail": "trust"}],
        "events": [{"name": "Ambush", "summary": "Night attack"}],
    }

    service.update_neo4j(facts)

    assert len(calls) == 4


def test_graph_queries_return_empty_without_driver():
    service = MemoryService.__new__(MemoryService)
    service.neo4j_driver = None

    assert service.query_character_evolution("Alice") == {}
    assert service.detect_character_contradictions("Alice") == []
    assert service.query_relationship_evolution("Alice", "Bob") == []
    assert service.find_orphaned_plot_threads(5) == []
    assert service.export_graph_for_visualization() == {"nodes": [], "edges": []}


def test_store_and_retrieve_style_memory():
    service = MemoryService.__new__(MemoryService)

    class DummyCollection:
        def __init__(self):
            self.add_called = False

        def add(self, documents, ids, metadatas):
            self.add_called = True

        def query(self, query_texts, n_results):
            return {"documents": [["one", "two"]]}

    class DummyChroma:
        def __init__(self):
            self.collection = DummyCollection()

        def get_or_create_collection(self, name):
            return self.collection

    service.chroma_client = DummyChroma()

    service.store_style_memory("proj", "chap", "text", "summary")
    results = service.retrieve_style_memory("proj", "query", top_k=2)

    assert results == ["one", "two"]


def test_build_extraction_prompt_and_merge_summary():
    service = MemoryService.__new__(MemoryService)

    prompt = service._build_extraction_prompt("Texte")
    assert "characters" in prompt
    assert "locations" in prompt
    assert "relations" in prompt
    assert "events" in prompt

    merged = service._merge_summary("A", "B")
    assert merged == "A / B"
