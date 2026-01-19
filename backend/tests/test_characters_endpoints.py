from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import characters as characters_module
from app.schemas.character import CharacterCreate, CharacterGenerateRequest


def test_extract_json_payload_handles_code_block():
    raw = "```json\n{\"characters\": [{\"name\": \"Alice\"}]}\n```"
    parsed = characters_module._extract_json_payload(raw)
    assert isinstance(parsed, dict)
    assert parsed["characters"][0]["name"] == "Alice"


def test_extract_json_payload_handles_list_snippet():
    raw = "text before [{\"name\": \"Bob\"}] text after"
    parsed = characters_module._extract_json_payload(raw)
    assert isinstance(parsed, list)
    assert parsed[0]["name"] == "Bob"


def test_infer_count_from_precision():
    assert characters_module._infer_count_from_precision("2 characters") is None
    assert characters_module._infer_count_from_precision("characters: 3") is None
    assert characters_module._infer_count_from_precision("unknown") is None


@pytest.mark.asyncio
async def test_list_characters_returns_list(monkeypatch):
    class DummyService:
        def __init__(self, db):
            self.db = db

        async def get_all_by_project(self, project_id, user_id, skip=0, limit=100):
            character = SimpleNamespace(
                id=uuid4(),
                name="Alice",
                project_id=project_id,
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
                description=None,
                physical_description=None,
                personality=None,
                backstory=None,
                character_metadata={},
            )
            return ([character], 1)

    monkeypatch.setattr(characters_module, "CharacterService", DummyService)

    result = await characters_module.list_characters(
        project_id=uuid4(),
        skip=0,
        limit=100,
        db=None,
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result.total == 1


@pytest.mark.asyncio
async def test_get_character_missing_raises(monkeypatch):
    class DummyService:
        def __init__(self, db):
            self.db = db

        async def get_by_id(self, character_id, user_id):
            return None

    monkeypatch.setattr(characters_module, "CharacterService", DummyService)

    with pytest.raises(HTTPException):
        await characters_module.get_character(uuid4(), db=None, current_user=SimpleNamespace(id=uuid4()))


@pytest.mark.asyncio
async def test_delete_character_missing_raises(monkeypatch):
    class DummyService:
        def __init__(self, db):
            self.db = db

        async def delete(self, character_id, user_id):
            return False

    monkeypatch.setattr(characters_module, "CharacterService", DummyService)

    with pytest.raises(HTTPException):
        await characters_module.delete_character(uuid4(), db=None, current_user=SimpleNamespace(id=uuid4()))


@pytest.mark.asyncio
async def test_generate_main_characters_requires_summary(monkeypatch):
    project_id = uuid4()

    class DummyContextService:
        def __init__(self, db):
            self.db = db

        async def build_project_context(self, project_id, user_id):
            return {"project": {"description": ""}, "characters": [], "constraints": {}}

    monkeypatch.setattr(characters_module, "ProjectContextService", DummyContextService)

    with pytest.raises(HTTPException):
        await characters_module.generate_main_characters(
            CharacterGenerateRequest(project_id=project_id, summary=" "),
            db=None,
            current_user=SimpleNamespace(id=uuid4()),
        )


@pytest.mark.asyncio
async def test_generate_main_characters_handles_parse_error(monkeypatch):
    project_id = uuid4()

    class DummyContextService:
        def __init__(self, db):
            self.db = db

        async def build_project_context(self, project_id, user_id):
            return {"project": {"description": "Summary"}, "characters": [], "constraints": {}}

    class DummyLLM:
        async def chat(self, *args, **kwargs):
            return "not json"

    monkeypatch.setattr(characters_module, "ProjectContextService", DummyContextService)
    monkeypatch.setattr(characters_module, "DeepSeekClient", lambda: DummyLLM())

    with pytest.raises(HTTPException):
        await characters_module.generate_main_characters(
            CharacterGenerateRequest(project_id=project_id, summary="Summary"),
            db=None,
            current_user=SimpleNamespace(id=uuid4()),
        )


@pytest.mark.asyncio
async def test_generate_main_characters_no_characters(monkeypatch):
    project_id = uuid4()

    class DummyContextService:
        def __init__(self, db):
            self.db = db

        async def build_project_context(self, project_id, user_id):
            return {"project": {"description": "Summary"}, "characters": [], "constraints": {}}

    class DummyLLM:
        async def chat(self, *args, **kwargs):
            return "{\"characters\": []}"

    monkeypatch.setattr(characters_module, "ProjectContextService", DummyContextService)
    monkeypatch.setattr(characters_module, "DeepSeekClient", lambda: DummyLLM())

    with pytest.raises(HTTPException):
        await characters_module.generate_main_characters(
            CharacterGenerateRequest(project_id=project_id, summary="Summary"),
            db=None,
            current_user=SimpleNamespace(id=uuid4()),
        )


@pytest.mark.asyncio
async def test_generate_main_characters_creates_unique(monkeypatch):
    project_id = uuid4()
    created = []

    class DummyContextService:
        def __init__(self, db):
            self.db = db

        async def build_project_context(self, project_id, user_id):
            return {
                "project": {"description": "Summary", "title": "Proj", "genre": None},
                "characters": [{"name": "Alice"}],
                "constraints": {},
            }

    class DummyLLM:
        async def chat(self, *args, **kwargs):
            return "{\"characters\": [{\"name\": \"Alice\"}, {\"name\": \"Bob\", \"role\": \"protagonist\"}]}"

    class DummyCharacterService:
        def __init__(self, db):
            self.db = db

        async def create(self, character_data: CharacterCreate, user_id):
            created.append(character_data.name)
            return SimpleNamespace(
                id=uuid4(),
                name=character_data.name,
                project_id=character_data.project_id,
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
                description=character_data.description,
                physical_description=character_data.physical_description,
                personality=character_data.personality,
                backstory=character_data.backstory,
                character_metadata=character_data.metadata or {},
            )

    monkeypatch.setattr(characters_module, "ProjectContextService", DummyContextService)
    monkeypatch.setattr(characters_module, "DeepSeekClient", lambda: DummyLLM())
    monkeypatch.setattr(characters_module, "CharacterService", DummyCharacterService)

    result = await characters_module.generate_main_characters(
        CharacterGenerateRequest(project_id=project_id, summary="Summary", precision="2 characters"),
        db=None,
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert result.total == 1
    assert created == ["Bob"]
