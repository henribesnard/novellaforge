"""Characters endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional
import json
import re
from uuid import UUID

from app.db.session import get_db
from app.models.user import User
from app.schemas.character import (
    CharacterCreate,
    CharacterUpdate,
    CharacterResponse,
    CharacterList,
    CharacterGenerateRequest,
)
from app.services.character_service import CharacterService
from app.services.context_service import ProjectContextService
from app.services.llm_client import DeepSeekClient
from app.core.config import settings
from app.core.security import get_current_active_user

router = APIRouter()


def _extract_json_payload(raw_text: str) -> Any:
    text = (raw_text or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1].strip()
        if text.startswith("json"):
            text = text[4:].strip()

    obj_start = text.find("{")
    list_start = text.find("[")
    if obj_start == -1 and list_start == -1:
        return json.loads(text)

    if list_start != -1 and (obj_start == -1 or list_start < obj_start):
        end = text.rfind("]")
        if end != -1:
            text = text[list_start:end + 1]
    else:
        end = text.rfind("}")
        if end != -1:
            text = text[obj_start:end + 1]

    return json.loads(text)


def _infer_count_from_precision(precision: Optional[str]) -> Optional[int]:
    if not precision:
        return None

    text = precision.lower()
    patterns = [
        r"(?:^|\\b)(\\d{1,2})\\s*(?:personnages?|persos?|characters?)",
        r"(?:personnages?|persos?|characters?)\\s*[:=]?\\s*(\\d{1,2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                value = int(match.group(1))
            except ValueError:
                continue
            if 1 <= value <= 8:
                return value
    return None


@router.get("/", response_model=CharacterList)
async def list_characters(
    project_id: UUID = Query(..., description="Project ID to filter characters"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all characters for a project.

    - **project_id**: Project ID (required)
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return (max 100)
    """
    character_service = CharacterService(db)
    characters, total = await character_service.get_all_by_project(
        project_id=project_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )

    return CharacterList(characters=characters, total=total)


@router.post("/", response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def create_character(
    character_data: CharacterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new character.

    - **name**: Character name (required)
    - **description**: Character description
    - **physical_description**: Physical appearance
    - **personality**: Personality traits
    - **backstory**: Character backstory
    - **project_id**: Project ID (required)
    """
    character_service = CharacterService(db)
    character = await character_service.create(character_data, current_user.id)
    return character


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific character by ID.

    Returns 404 if character not found or user doesn't have access.
    """
    character_service = CharacterService(db)
    character = await character_service.get_by_id(character_id, current_user.id)

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    return character


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: UUID,
    character_data: CharacterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a character.

    All fields are optional. Only provided fields will be updated.
    """
    character_service = CharacterService(db)
    character = await character_service.update(character_id, character_data, current_user.id)
    return character


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
    character_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a character.
    """
    character_service = CharacterService(db)
    deleted = await character_service.delete(character_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    return None


@router.post("/auto", response_model=CharacterList, status_code=status.HTTP_201_CREATED)
async def generate_main_characters(
    request: CharacterGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Auto-generate main characters from the project summary and persist them.
    """
    context_service = ProjectContextService(db)
    context = await context_service.build_project_context(
        project_id=request.project_id,
        user_id=current_user.id,
    )

    project_info = context.get("project", {})
    summary = (request.summary or project_info.get("description") or "").strip()
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project summary is required to generate characters",
        )

    precision = (request.precision or "").strip()
    target_count = request.count
    if target_count is None:
        target_count = _infer_count_from_precision(precision)

    existing_names = {
        (char.get("name") or "").strip().lower()
        for char in context.get("characters", [])
        if char.get("name")
    }
    constraints = context.get("constraints", {})

    if target_count:
        count_instruction = f"Return exactly {target_count} characters in JSON format, no markdown.\n"
    else:
        count_instruction = (
            "Decide the appropriate number of main characters based on the summary "
            "and user precision (between 1 and 8). Return that many characters in JSON format, no markdown.\n"
        )

    prompt = (
        "Generate a JSON object with a list of main characters for this story.\n"
        f"{count_instruction}"
        "Schema:\n"
        "{\n"
        '  "characters": [\n'
        "    {\n"
        '      "name": "string",\n'
        '      "role": "protagonist|antagonist|supporting|minor",\n'
        '      "description": "string",\n'
        '      "physical_description": "string",\n'
        '      "personality": "string",\n'
        '      "backstory": "string",\n'
        '      "goals": "string",\n'
        '      "relationships": {"name": "relation"}\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"Project title: {project_info.get('title')}\n"
        f"Genre: {project_info.get('genre')}\n"
        f"Summary: {summary}\n"
        f"User precision: {precision or 'none'}\n"
        f"Constraints: {json.dumps(constraints, ensure_ascii=True)}\n"
        f"Existing character names: {', '.join(sorted(existing_names)) or 'none'}\n"
        "Avoid duplicate names and keep characters consistent with the genre."
    )

    llm_client = DeepSeekClient()
    raw = await llm_client.chat(
        messages=[
            {
                "role": "system",
                "content": "You are a senior character designer for novels. Return strict JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
        max_tokens=max(1, settings.CHAT_MAX_TOKENS),
    )

    try:
        parsed = _extract_json_payload(raw)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to parse character generation output",
        )

    if isinstance(parsed, dict):
        characters_payload = parsed.get("characters") or []
    elif isinstance(parsed, list):
        characters_payload = parsed
    else:
        characters_payload = []

    if not isinstance(characters_payload, list) or not characters_payload:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No characters generated",
        )

    if target_count is None:
        target_count = max(1, min(len(characters_payload), 8))
    else:
        target_count = max(1, min(target_count, 8))

    character_service = CharacterService(db)
    created = []
    for item in characters_payload[: target_count]:
        if not isinstance(item, dict):
            continue
        name = (item.get("name") or "").strip()
        if not name:
            continue
        if name.lower() in existing_names:
            continue

        metadata = {}
        role = item.get("role")
        goals = item.get("goals")
        relationships = item.get("relationships")
        if role:
            metadata["role"] = role
        if goals:
            metadata["goals"] = goals
        if isinstance(relationships, dict) and relationships:
            metadata["relationships"] = relationships
        if metadata:
            metadata["source"] = "auto"

        character = await character_service.create(
            CharacterCreate(
                name=name,
                description=item.get("description"),
                physical_description=item.get("physical_description"),
                personality=item.get("personality"),
                backstory=item.get("backstory"),
                metadata=metadata or None,
                project_id=request.project_id,
            ),
            current_user.id,
        )
        created.append(character)

    return CharacterList(characters=created, total=len(created))
