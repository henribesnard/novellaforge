import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.writing_pipeline import WritingPipeline
import app.services.writing_pipeline as writing_pipeline


def test_quality_gate_accepts_good_chapter():
    pipeline = WritingPipeline.__new__(WritingPipeline)
    state = {
        "critique_score": 8.5,
        "chapter_text": "one two three four",
        "min_word_count": 1,
        "max_word_count": 10,
        "revision_count": 0,
        "continuity_validation": {"blocking": False, "coherence_score": 8.0},
    }

    assert pipeline._quality_gate(state) == "done"


def test_quality_gate_requests_revision():
    pipeline = WritingPipeline.__new__(WritingPipeline)
    state = {
        "critique_score": 6.0,
        "chapter_text": "one two three four",
        "min_word_count": 1,
        "max_word_count": 10,
        "revision_count": 1,
        "continuity_validation": {"blocking": False, "coherence_score": 6.0},
    }

    assert pipeline._quality_gate(state) == "revise"


def test_quality_gate_stops_after_limit():
    pipeline = WritingPipeline.__new__(WritingPipeline)
    state = {
        "critique_score": 4.0,
        "chapter_text": "one two three four",
        "min_word_count": 1,
        "max_word_count": 10,
        "revision_count": 3,
        "continuity_validation": {"blocking": False, "coherence_score": 8.0},
    }

    assert pipeline._quality_gate(state) == "done"


@pytest.mark.asyncio
async def test_validate_continuity_detects_contradictions():
    class DummyClient:
        async def chat(self, *args, **kwargs):
            payload = {
                "severe_issues": [
                    {"type": "contradiction", "detail": "Bob is dead but appears alive", "severity": "blocking"}
                ],
                "minor_issues": [],
                "coherence_score": 2,
                "blocking": True,
            }
            return json.dumps(payload)

    pipeline = WritingPipeline.__new__(WritingPipeline)
    pipeline.llm_client = DummyClient()

    state = {
        "chapter_text": "Bob enters the room.",
        "project_context": {
            "project": {"metadata": {"continuity": {"characters": [{"name": "Bob", "status": "dead"}]}}}
        },
        "memory_context": "Characters: Bob (dead).",
        "retrieved_chunks": [],
        "current_plan": {"required_plot_points": []},
        "chapter_summary": "Bob returns",
        "chapter_emotional_stake": "shock",
    }

    result = await pipeline.validate_continuity(state)
    validation = result.get("continuity_validation", {})

    assert validation.get("blocking") is True
    assert validation.get("severe_issues")


@pytest.mark.asyncio
async def test_validate_continuity_adds_plot_point_validation():
    class DummyClient:
        async def chat(self, *args, **kwargs):
            payload = {
                "severe_issues": [],
                "minor_issues": [],
                "coherence_score": 7,
                "blocking": False,
                "covered_points": ["Reveal"],
                "missing_points": ["Secret"],
                "forbidden_violations": ["Kill the hero"],
                "coverage_score": 3,
                "explanation": "Missing key beats.",
            }
            return json.dumps(payload)

    pipeline = WritingPipeline.__new__(WritingPipeline)
    pipeline.llm_client = DummyClient()

    state = {
        "chapter_text": "Le heros doute mais n'agit pas.",
        "project_context": {"project": {"metadata": {}}},
        "memory_context": "Characters: Alice.",
        "retrieved_chunks": [],
        "current_plan": {
            "required_plot_points": ["Reveal", "Secret"],
            "forbidden_actions": ["Kill the hero"],
        },
        "chapter_summary": "Reveal",
        "chapter_emotional_stake": "tension",
    }

    result = await pipeline.validate_continuity(state)
    validation = result.get("continuity_validation", {})
    plot_validation = validation.get("plot_point_validation", {})

    assert plot_validation.get("missing_points") == ["Secret"]
    assert plot_validation.get("forbidden_violations") == ["Kill the hero"]
    assert validation.get("blocking") is True


@pytest.mark.asyncio
async def test_validate_continuity_includes_graph_issues():
    class DummyClient:
        async def chat(self, *args, **kwargs):
            payload = {
                "severe_issues": [],
                "minor_issues": [],
                "coherence_score": 8,
                "blocking": False,
            }
            return json.dumps(payload)

    class DummyMemoryService:
        neo4j_driver = True

        def detect_character_contradictions(self, name, project_id=None):
            return [
                {
                    "contradiction": "resurrection",
                    "from_chapter": 10,
                    "to_chapter": 12,
                }
            ]

        def find_orphaned_plot_threads(self, chapter_index, project_id=None):
            return [{"event": "Mystere", "last_mentioned": 1}]

    pipeline = WritingPipeline.__new__(WritingPipeline)
    pipeline.llm_client = DummyClient()
    pipeline.memory_service = DummyMemoryService()

    state = {
        "chapter_text": "Bob revient dans la salle.",
        "project_context": {"characters": [{"name": "Bob"}]},
        "chapter_index": 12,
        "memory_context": "",
        "retrieved_chunks": [],
        "current_plan": {"required_plot_points": []},
        "chapter_summary": "Retour de Bob",
        "chapter_emotional_stake": "choc",
    }

    result = await pipeline.validate_continuity(state)
    validation = result.get("continuity_validation", {})

    assert validation.get("blocking") is True
    assert validation.get("graph_issues")


@pytest.mark.asyncio
async def test_validate_continuity_filters_resolved_contradictions():
    class DummyClient:
        async def chat(self, *args, **kwargs):
            payload = {
                "severe_issues": [
                    {
                        "type": "contradiction",
                        "detail": "Bob is dead but appears alive",
                        "severity": "blocking",
                    }
                ],
                "minor_issues": [],
                "coherence_score": 3,
                "blocking": True,
            }
            return json.dumps(payload)

    pipeline = WritingPipeline.__new__(WritingPipeline)
    pipeline.llm_client = DummyClient()
    pipeline.memory_service = SimpleNamespace(neo4j_driver=None)

    state = {
        "chapter_text": "Bob enters the room.",
        "project_context": {
            "project": {
                "metadata": {
                    "tracked_contradictions": [
                        {"description": "Bob is dead but appears alive", "status": "resolved"}
                    ]
                }
            }
        },
        "memory_context": "",
        "retrieved_chunks": [],
        "current_plan": {},
        "chapter_summary": "",
        "chapter_emotional_stake": "",
    }

    result = await pipeline.validate_continuity(state)
    validation = result.get("continuity_validation", {})

    assert validation.get("severe_issues") == []
    assert validation.get("blocking") is False


@pytest.mark.asyncio
async def test_track_contradiction_updates_affected_chapters():
    project_id = uuid4()
    project = SimpleNamespace(id=project_id, project_metadata={})

    class DummyDB:
        def __init__(self):
            self.commits = 0

        async def get(self, model, pid):
            if pid == project_id:
                return project
            return None

        async def commit(self):
            self.commits += 1

    pipeline = WritingPipeline.__new__(WritingPipeline)
    pipeline.db = DummyDB()

    issue = {"type": "contradiction", "detail": "Bob is dead", "severity": "blocking"}
    await pipeline._track_contradiction(project_id, issue, 5)
    await pipeline._track_contradiction(project_id, issue, 6)

    contradictions = project.project_metadata["tracked_contradictions"]
    assert len(contradictions) == 1
    assert contradictions[0]["description"] == "Bob is dead"
    assert contradictions[0]["severity"] == "critical"
    assert contradictions[0]["status"] == "pending"
    assert contradictions[0]["affected_chapters"] == [5, 6]
    assert pipeline.db.commits == 2


def test_quality_gate_blocks_on_coherence_issues():
    pipeline = WritingPipeline.__new__(WritingPipeline)
    state = {
        "critique_score": 9.0,
        "chapter_text": "one two three four",
        "min_word_count": 1,
        "max_word_count": 10,
        "continuity_validation": {
            "blocking": True,
            "coherence_score": 3,
            "severe_issues": [{"type": "contradiction", "detail": "..." }],
        },
        "revision_count": 0,
    }

    assert pipeline._quality_gate(state) == "revise"


def test_quality_gate_blocks_on_missing_plot_points():
    pipeline = WritingPipeline.__new__(WritingPipeline)
    state = {
        "critique_score": 9.0,
        "chapter_text": "one two three four",
        "min_word_count": 1,
        "max_word_count": 10,
        "continuity_validation": {
            "blocking": False,
            "coherence_score": 9,
            "plot_point_validation": {"missing_points": ["Reveal"], "forbidden_violations": []},
        },
        "revision_count": 0,
    }

    assert pipeline._quality_gate(state) == "revise"


def test_quality_gate_passes_with_good_coherence():
    pipeline = WritingPipeline.__new__(WritingPipeline)
    state = {
        "critique_score": 9.0,
        "chapter_text": "one two three four",
        "min_word_count": 1,
        "max_word_count": 10,
        "continuity_validation": {
            "blocking": False,
            "coherence_score": 9,
            "severe_issues": [],
        },
        "revision_count": 0,
    }

    assert pipeline._quality_gate(state) == "done"


def test_build_bible_context_block_formats_sections():
    pipeline = WritingPipeline.__new__(WritingPipeline)
    bible = {
        "world_rules": [
            {"rule": "No magic in the forest", "importance": "critical", "exceptions": ["elves"]}
        ],
        "timeline": [
            {"event": "Battle in forest", "chapter_index": 2, "time_reference": "night"}
        ],
        "established_facts": [
            {"fact": "Victor killed the father", "established_chapter": 1, "cannot_contradict": True}
        ],
    }

    block = pipeline._build_bible_context_block(bible)

    assert "REGLES DU MONDE" in block
    assert "No magic in the forest" in block
    assert "Ch.2" in block
    assert "FAITS ETABLIS" in block


@pytest.mark.asyncio
async def test_approve_chapter_updates_rag(monkeypatch):
    import app.services.writing_pipeline as writing_pipeline

    doc = SimpleNamespace(
        id=uuid4(),
        project_id=uuid4(),
        content="Alice avance dans la foret.",
        document_metadata={"status": "draft", "chapter_index": 1},
        title="Chapitre 1",
        order_index=0,
    )

    class DummyDocumentService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, document_id, user_id):
            return doc

        async def update(self, document_id, document_data, user_id):
            if document_data.content is not None:
                doc.content = document_data.content
            if document_data.metadata is not None:
                doc.document_metadata = document_data.metadata
            if document_data.title is not None:
                doc.title = document_data.title
            return doc

    class DummyMemoryService:
        async def extract_facts(self, chapter_text):
            return {
                "summary": "Alice avance.",
                "characters": [],
                "locations": [],
                "relations": [],
                "events": [],
            }

        def merge_facts(self, metadata, facts):
            if not isinstance(metadata, dict):
                metadata = {}
            metadata["continuity"] = {"updated_at": "now"}
            return metadata

        def update_neo4j(self, facts, project_id=None, chapter_index=None):
            return None

        def store_style_memory(self, project_id, chapter_id, chapter_text, summary):
            return None

    class DummyContextService:
        async def build_project_context(self, project_id, user_id):
            return {"project": {"metadata": {}}}

    class DummyRagService:
        def __init__(self):
            self.calls = []

        async def aindex_documents(self, project_id, documents, clear_existing=True):
            self.calls.append(("index", project_id, documents, clear_existing))
            return 1

        async def aupdate_document(self, project_id, document):
            self.calls.append(("update", project_id, document))
            return 1

    pipeline = WritingPipeline.__new__(WritingPipeline)
    pipeline.db = SimpleNamespace()
    pipeline.memory_service = DummyMemoryService()
    pipeline.context_service = DummyContextService()
    pipeline.rag_service = DummyRagService()

    async def noop_update(project_id, metadata):
        return None

    pipeline._update_project_metadata = noop_update

    monkeypatch.setattr(writing_pipeline, "DocumentService", DummyDocumentService)

    result = await pipeline.approve_chapter(str(doc.id), uuid4())

    assert result.get("rag_updated") is True
    assert result.get("rag_update_error") is None
    assert pipeline.rag_service.calls
    assert pipeline.rag_service.calls
    call_type, project_id, document = pipeline.rag_service.calls[0]
    assert call_type == "update"
    assert project_id == doc.project_id
    assert document == doc


@pytest.mark.asyncio
async def test_collect_context_applies_word_range():
    pipeline = WritingPipeline.__new__(WritingPipeline)

    class DummyContextService:
        async def build_project_context(self, project_id, user_id):
            return {
                "project": {"metadata": {"chapter_word_range": {"min": 1500, "max": 1800}}}
            }

    pipeline.context_service = DummyContextService()

    async def fake_resolve(state, context):
        return {
            "chapter_index": 2,
            "chapter_title": "Chapitre 2",
            "chapter_summary": "Resume",
            "chapter_emotional_stake": "tension",
        }

    pipeline._resolve_chapter_context = fake_resolve

    result = await pipeline.collect_context(
        {"project_id": uuid4(), "user_id": uuid4(), "target_word_count": 1600}
    )

    assert result["min_word_count"] == 1500
    assert result["max_word_count"] == 1800
    assert result["target_word_count"] == 1600
    assert result["chapter_title"] == "Chapitre 2"


@pytest.mark.asyncio
async def test_plan_chapter_normalizes_response():
    pipeline = WritingPipeline.__new__(WritingPipeline)

    class DummyLLM:
        async def chat(self, *args, **kwargs):
            payload = {
                "chapter_number": 2,
                "scene_beats": ["Setup", "Conflict", "Cliffhanger"],
                "target_emotion": "tension",
                "required_plot_points": ["Reveal"],
                "cliffhanger_type": "revelation",
                "estimated_word_count": 1500,
            }
            return {"content": json.dumps(payload), "reasoning_content": "Reasoned"}

    pipeline.llm_client = DummyLLM()

    result = await pipeline.plan_chapter(
        {
            "current_plan": None,
            "chapter_index": 2,
            "target_word_count": 1500,
            "chapter_summary": "Resume",
            "chapter_emotional_stake": "tension",
            "project_context": {
                "project": {
                    "genre": "fantasy",
                    "concept": {"premise": "Premise", "tone": "dark", "tropes": ["x"]},
                    "plan": {"global_summary": "Global"},
                    "recent_chapter_summaries": ["a", "b"],
                }
            },
        }
    )

    plan = result["current_plan"]
    assert plan["chapter_number"] == 2
    assert plan["required_plot_points"] == ["Reveal"]
    assert result["debug_reasoning"] == ["Reasoned"]


@pytest.mark.asyncio
async def test_write_chapter_does_not_condense_without_limits():
    pipeline = WritingPipeline.__new__(WritingPipeline)

    class DummyLLM:
        def __init__(self):
            self.prompts = []

        async def chat(self, messages, **kwargs):
            prompt = messages[-1]["content"]
            self.prompts.append(prompt)
            return "mot " * 60

    pipeline.llm_client = DummyLLM()

    state = {
        "current_plan": {
            "scene_beats": ["Setup"],
            "target_emotion": "tension",
            "required_plot_points": [],
            "cliffhanger_type": "revelation",
            "estimated_word_count": 20,
        },
        "project_context": {"project": {"concept": {"premise": "", "tone": "", "tropes": []}}},
        "chapter_title": "Chapitre 1",
        "chapter_summary": "Resume",
        "chapter_emotional_stake": "tension",
        "min_word_count": 10,
        "max_word_count": 20,
        "target_word_count": 15,
        "memory_context": "memoire",
        "retrieved_chunks": [],
        "style_chunks": [],
    }

    result = await pipeline.write_chapter(state)
    word_count = pipeline._count_words(result["chapter_text"])

    assert word_count == 60
    assert all("Chapitre a condenser" not in prompt for prompt in pipeline.llm_client.prompts)


def test_build_continuity_alerts_formats_output():
    pipeline = WritingPipeline.__new__(WritingPipeline)
    validation = {
        "severe_issues": [{"type": "contradiction", "detail": "Issue"}],
        "minor_issues": [{"detail": "Minor"}],
    }

    alerts = pipeline._build_continuity_alerts(validation)

    assert alerts == ["contradiction: Issue", "Minor"]


@pytest.mark.asyncio
async def test_retrieve_context_returns_memory_when_rag_disabled(monkeypatch):
    pipeline = WritingPipeline.__new__(WritingPipeline)

    class DummyMemoryService:
        def build_context_block(self, metadata):
            return "context"

        def retrieve_style_memory(self, project_id, query, top_k=3):
            return []

    pipeline.memory_service = DummyMemoryService()

    class DummyCacheService:
        async def get_memory_context(self, metadata):
            return None
        async def set_memory_context(self, metadata, context):
            pass
        async def get_rag_results(self, query, project_id):
            return None
        async def set_rag_results(self, query, project_id, results):
            pass

    pipeline.cache_service = DummyCacheService()

    monkeypatch.setattr(
        writing_pipeline.SmartContextTruncator,
        "truncate_memory_context",
        lambda *args, **kwargs: "context",
    )

    result = await pipeline.retrieve_context(
        {
            "use_rag": False,
            "project_context": {"project": {"metadata": {}}},
        }
    )

    assert result["memory_context"] == "context"


def test_pipeline_init_builds_graph(monkeypatch):
    import app.services.writing_pipeline as writing_pipeline

    class DummyContextService:
        def __init__(self, db):
            self.db = db

    class DummyRagService:
        def __init__(self):
            self.ready = True

    class DummyMemoryService:
        def __init__(self):
            self.ready = True

    class DummyCacheService:
        def __init__(self):
            self.ready = True

    class DummyLLM:
        def __init__(self):
            self.ready = True

    monkeypatch.setattr(writing_pipeline, "ProjectContextService", DummyContextService)
    monkeypatch.setattr(writing_pipeline, "RagService", DummyRagService)
    monkeypatch.setattr(writing_pipeline, "MemoryService", DummyMemoryService)
    monkeypatch.setattr(writing_pipeline, "CacheService", DummyCacheService)
    monkeypatch.setattr(writing_pipeline, "DeepSeekClient", DummyLLM)

    pipeline = writing_pipeline.WritingPipeline(SimpleNamespace())

    assert pipeline.graph is not None


@pytest.mark.asyncio
async def test_retrieve_context_with_rag(monkeypatch):
    pipeline = WritingPipeline.__new__(WritingPipeline)

    class DummyRagService:
        def __init__(self):
            self.indexed = False
            self.queried = False

        async def aindex_documents(self, project_id, documents, clear_existing=True):
            self.indexed = True
            return 0

        async def aretrieve(self, project_id, query, top_k):
            self.queried = True
            return ["chunk"]

    class DummyMemoryService:
        def build_context_block(self, metadata):
            return "context"

        def retrieve_style_memory(self, project_id, query, top_k=3):
            return ["style"]

    pipeline.rag_service = DummyRagService()
    pipeline.memory_service = DummyMemoryService()

    class DummyCacheService:
        async def get_memory_context(self, metadata):
            return None
        async def set_memory_context(self, metadata, context):
            pass
        async def get_rag_results(self, query, project_id):
            return None
        async def set_rag_results(self, query, project_id, results):
            pass

    pipeline.cache_service = DummyCacheService()

    async def fake_load(project_id):
        return []

    async def fake_load(project_id):
        return []

    pipeline._load_project_documents = fake_load

    monkeypatch.setattr(
        writing_pipeline.SmartContextTruncator,
        "truncate_memory_context",
        lambda *args, **kwargs: "context",
    )

    result = await pipeline.retrieve_context(
        {
            "use_rag": True,
            "reindex_documents": True,
            "project_id": uuid4(),
            "chapter_title": "Title",
            "chapter_summary": "Summary",
            "project_context": {"project": {"metadata": {}}},
        }
    )

    assert result["retrieved_chunks"] == ["chunk"]
    assert result["style_chunks"] == ["style"]
    assert result["memory_context"] == "context"
    assert pipeline.rag_service.indexed is True
    assert pipeline.rag_service.queried is True


@pytest.mark.asyncio
async def test_write_chapter_includes_notes_and_style():
    pipeline = WritingPipeline.__new__(WritingPipeline)

    class DummyLLM:
        async def chat(self, messages, **kwargs):
            return "mot " * 5

    pipeline.llm_client = DummyLLM()

    state = {
        "current_plan": {
            "scene_beats": ["Beat 1", "Beat 2"],
            "target_emotion": "tension",
            "required_plot_points": [],
            "cliffhanger_type": "revelation",
            "estimated_word_count": 20,
        },
        "project_context": {"project": {"concept": {"premise": "", "tone": "", "tropes": []}}},
        "chapter_title": "Chapitre 1",
        "chapter_summary": "Resume",
        "chapter_emotional_stake": "tension",
        "min_word_count": 5,
        "max_word_count": 50,
        "target_word_count": 20,
        "memory_context": "memoire",
        "retrieved_chunks": ["rag one"],
        "style_chunks": ["style one"],
        "critique_feedback": ["fix pacing"],
        "chapter_instruction": "add suspense",
    }

    result = await pipeline.write_chapter(state)

    assert "mot" in result["chapter_text"]


@pytest.mark.asyncio
async def test_write_chapter_includes_missing_plot_points():
    pipeline = WritingPipeline.__new__(WritingPipeline)

    class DummyLLM:
        def __init__(self):
            self.last_prompt = ""

        async def chat(self, messages, **kwargs):
            self.last_prompt = messages[-1]["content"]
            return "mot " * 5

    pipeline.llm_client = DummyLLM()

    state = {
        "current_plan": {
            "scene_beats": ["Beat 1"],
            "target_emotion": "tension",
            "required_plot_points": [],
            "cliffhanger_type": "revelation",
            "estimated_word_count": 20,
        },
        "project_context": {"project": {"concept": {"premise": "", "tone": "", "tropes": []}}},
        "chapter_title": "Chapitre 1",
        "chapter_summary": "Resume",
        "chapter_emotional_stake": "tension",
        "min_word_count": 5,
        "max_word_count": 50,
        "target_word_count": 20,
        "memory_context": "memoire",
        "retrieved_chunks": [],
        "style_chunks": [],
        "continuity_validation": {
            "plot_point_validation": {"missing_points": ["Reveal"], "forbidden_violations": []}
        },
    }

    await pipeline.write_chapter(state)

    assert "POINTS D'INTRIGUE MANQUANTS" in pipeline.llm_client.last_prompt
    assert "Reveal" in pipeline.llm_client.last_prompt


@pytest.mark.asyncio
async def test_condense_to_word_limit_retries():
    pipeline = WritingPipeline.__new__(WritingPipeline)

    class DummyLLM:
        def __init__(self):
            self.calls = 0

        async def chat(self, messages, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return "mot " * 50
            return "mot " * 10

    pipeline.llm_client = DummyLLM()

    condensed = await pipeline._condense_to_word_limit(
        "mot " * 60,
        min_words=5,
        max_words=15,
        target_word_count=10,
    )

    assert pipeline._count_words(condensed) <= 15


def test_safe_json_returns_empty_on_invalid():
    pipeline = WritingPipeline.__new__(WritingPipeline)
    assert pipeline._safe_json("not json") == {}


@pytest.mark.asyncio
async def test_resolve_chapter_context_from_document():
    pipeline = WritingPipeline.__new__(WritingPipeline)
    document_id = uuid4()
    project_id = uuid4()
    doc = SimpleNamespace(
        id=document_id,
        project_id=project_id,
        order_index=0,
        title="Chapitre 1",
        document_metadata={"chapter_index": 1, "summary": "Resume", "emotional_stake": "tension"},
    )

    async def fake_get_document(doc_id):
        return doc

    pipeline._get_document = fake_get_document

    result = await pipeline._resolve_chapter_context(
        {"chapter_id": document_id, "project_id": project_id},
        {"project": {"plan": {}}},
    )

    assert result["chapter_index"] == 1
    assert result["chapter_title"] == "Chapitre 1"


@pytest.mark.asyncio
async def test_resolve_chapter_context_from_plan():
    pipeline = WritingPipeline.__new__(WritingPipeline)
    project_id = uuid4()
    plan = {
        "chapters": [
            {"index": 1, "title": "Chapitre 1", "summary": "S1", "emotional_stake": "tension"},
            {"index": 2, "title": "Chapitre 2", "summary": "S2", "emotional_stake": "fear"},
        ]
    }

    async def fake_next_order(project_id_value):
        return 3

    pipeline._get_next_order_index = fake_next_order

    result = await pipeline._resolve_chapter_context(
        {"project_id": project_id},
        {"project": {"plan": plan}},
    )

    assert result["chapter_index"] == 1
    assert result["chapter_title"] == "Chapitre 1"


@pytest.mark.asyncio
async def test_get_document_and_order_helpers():
    doc = SimpleNamespace(id=uuid4())

    class DummyResult:
        def __init__(self, doc=None, scalar_value=None, rows=None):
            self._doc = doc
            self._scalar_value = scalar_value
            self._rows = rows or []

        def scalar_one_or_none(self):
            return self._doc

        def scalar(self):
            return self._scalar_value

        def scalars(self):
            return self

        def all(self):
            return self._rows

    class DummyDB:
        def __init__(self):
            self.calls = 0

        async def execute(self, query):
            self.calls += 1
            if self.calls == 1:
                return DummyResult(doc=doc)
            if self.calls == 2:
                return DummyResult(scalar_value=3)
            return DummyResult(rows=[doc])

        async def get(self, model, project_id):
            return SimpleNamespace(project_metadata={})

        async def commit(self):
            return None

    pipeline = WritingPipeline.__new__(WritingPipeline)
    pipeline.db = DummyDB()

    fetched = await pipeline._get_document(doc.id)
    assert fetched == doc

    next_index = await pipeline._get_next_order_index(uuid4())
    assert next_index == 4

    docs = await pipeline._load_project_documents(uuid4())
    assert docs == [doc]

    await pipeline._update_project_metadata(uuid4(), {"continuity": {}})


@pytest.mark.asyncio
async def test_generate_chapter_auto_approves():
    pipeline = WritingPipeline.__new__(WritingPipeline)

    class DummyGraph:
        async def ainvoke(self, state):
            return {
                "chapter_text": "mot mot",
                "current_plan": {},
                "critique_payload": {},
                "retrieved_chunks": [],
            }

    pipeline.graph = DummyGraph()

    async def fake_persist(state, result, chapter_text, word_count):
        return "doc-1"

    async def fake_approve(document_id, user_id):
        return {"document_id": document_id}

    pipeline._persist_draft = fake_persist
    pipeline.approve_chapter = fake_approve

    result = await pipeline.generate_chapter(
        {
            "project_id": uuid4(),
            "user_id": uuid4(),
            "create_document": True,
            "auto_approve": True,
        }
    )

    assert result["document_id"] == "doc-1"


@pytest.mark.asyncio
async def test_persist_draft_updates_history(monkeypatch):
    import app.services.writing_pipeline as writing_pipeline

    existing_doc = SimpleNamespace(
        id=uuid4(),
        document_metadata={"continuity_validation_history": [{"blocking": False}]},
    )
    captured = {}

    class DummyDocumentService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, document_id, user_id):
            return existing_doc

        async def update(self, document_id, document_data, user_id):
            captured["update_metadata"] = document_data.metadata
            return existing_doc

        async def create(self, document_data, user_id):
            captured["create_metadata"] = document_data.metadata
            created = SimpleNamespace(id=uuid4())
            return created

    pipeline = WritingPipeline.__new__(WritingPipeline)
    pipeline.db = SimpleNamespace()

    async def fake_next_order(project_id):
        return 0

    pipeline._get_next_order_index = fake_next_order

    monkeypatch.setattr(writing_pipeline, "DocumentService", DummyDocumentService)

    draft_id = await pipeline._persist_draft(
        {
            "chapter_id": uuid4(),
            "user_id": uuid4(),
            "chapter_title": "Chapitre",
            "chapter_summary": "Resume",
            "chapter_emotional_stake": "tension",
        },
        {"current_plan": {}, "continuity_validation": {"blocking": True}},
        "texte",
        10,
    )

    assert draft_id == str(existing_doc.id)
    assert "plot_point_coverage" in (captured.get("update_metadata") or {})

    created_id = await pipeline._persist_draft(
        {
            "project_id": uuid4(),
            "user_id": uuid4(),
            "chapter_title": "Chapitre",
            "chapter_summary": "Resume",
            "chapter_emotional_stake": "tension",
        },
        {"current_plan": {}, "continuity_validation": None},
        "texte",
        10,
    )

    assert created_id is not None
    assert "plot_point_coverage" in (captured.get("create_metadata") or {})
