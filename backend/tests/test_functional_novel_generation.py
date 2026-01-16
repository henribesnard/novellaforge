import math
from uuid import uuid4

import pytest

from app.services.writing_pipeline import WritingPipeline


class DummyPipeline(WritingPipeline):
    def __init__(self) -> None:
        self.db = None
        self.context_service = None
        self.rag_service = None
        self.memory_service = None
        self.llm_client = None
        self.documents = {}
        self.graph = self._build_graph()

    async def collect_context(self, state):
        target_words = state.get("target_word_count", 10000)
        min_words = state.get("min_word_count", target_words)
        max_words = state.get("max_word_count", target_words)
        chapter_index = state.get("chapter_index", 1)
        return {
            "project_context": {
                "project": {
                    "genre": "fantasy",
                    "concept": {"premise": "Test premise", "tone": "intense", "tropes": ["test"]},
                    "plan": {},
                    "metadata": {"chapter_word_range": {"min": min_words, "max": max_words}},
                }
            },
            "min_word_count": min_words,
            "max_word_count": max_words,
            "target_word_count": target_words,
            "chapter_index": chapter_index,
            "chapter_title": state.get("chapter_title") or f"Chapter {chapter_index}",
            "chapter_summary": state.get("chapter_summary") or "",
            "chapter_emotional_stake": state.get("chapter_emotional_stake") or "tension",
        }

    async def retrieve_context(self, state):
        return {"retrieved_chunks": [], "style_chunks": [], "memory_context": ""}

    async def plan_chapter(self, state):
        return {
            "current_plan": {
                "chapter_number": state.get("chapter_index", 1),
                "scene_beats": ["Setup", "Escalation", "Cliffhanger"],
                "target_emotion": "tension",
                "required_plot_points": [],
                "cliffhanger_type": "revelation",
                "estimated_word_count": state.get("target_word_count", 10000),
            }
        }

    async def write_chapter(self, state):
        target_words = state.get("target_word_count", 10000)
        text = ("word " * (target_words - 1)) + "word"
        return {"chapter_text": text}

    async def critic(self, state):
        return {
            "critique_score": 9.5,
            "critique_feedback": [],
            "critique_payload": {
                "score": 9.5,
                "issues": [],
                "suggestions": [],
                "cliffhanger_ok": True,
                "pacing_ok": True,
            },
            "revision_count": state.get("revision_count", 0) + 1,
            "continuity_alerts": [],
        }

    async def _persist_draft(self, state, result, chapter_text, word_count):
        doc_id = f"doc-{state.get('chapter_index', len(self.documents) + 1)}"
        self.documents[doc_id] = {
            "title": result.get("chapter_title") or state.get("chapter_title"),
            "content": chapter_text,
            "word_count": word_count,
            "status": "draft",
        }
        return doc_id

    async def approve_chapter(self, document_id, user_id):
        document = self.documents.get(document_id)
        if not document:
            return {}
        document["status"] = "approved"
        return {"document_id": document_id, "status": "approved", "summary": None}


@pytest.mark.asyncio
async def test_functional_end_to_end_novel_generation():
    pipeline = DummyPipeline()
    target_total_words = 200_000
    words_per_chapter = 10_000
    chapters_needed = math.ceil((target_total_words + 1) / words_per_chapter)

    project_id = uuid4()
    user_id = uuid4()
    total_words = 0

    for chapter_index in range(1, chapters_needed + 1):
        result = await pipeline.generate_chapter(
            {
                "project_id": project_id,
                "user_id": user_id,
                "chapter_index": chapter_index,
                "target_word_count": words_per_chapter,
                "use_rag": False,
                "reindex_documents": False,
                "create_document": True,
                "auto_approve": True,
            }
        )
        total_words += result["word_count"]

    assert total_words > target_total_words
    assert len(pipeline.documents) == chapters_needed
    assert all(doc["status"] == "approved" for doc in pipeline.documents.values())
