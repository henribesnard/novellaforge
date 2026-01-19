"""Pydantic schemas for request/response validation"""
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    UserInDB
)
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectList,
    ContradictionResolution,
    ContradictionIntentionalRequest,
)
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentList,
    DocumentVersionCreate,
    DocumentVersionSummary,
    DocumentVersionResponse,
    DocumentVersionList,
    DocumentCommentCreate,
    DocumentComment,
    DocumentCommentList,
)
from app.schemas.character import (
    CharacterCreate,
    CharacterUpdate,
    CharacterResponse,
    CharacterList,
    CharacterGenerateRequest
)
from app.schemas.instruction import (
    InstructionCreate,
    InstructionUpdate,
    InstructionResponse,
    InstructionList,
)
from app.schemas.token import Token, TokenPayload
from app.schemas.story_bible import (
    StoryBible,
    StoryBibleDraftValidationRequest,
    StoryBibleGlossary,
    StoryBibleValidationResponse,
    StoryBibleViolation,
    WorldRule,
    TimelineEvent,
    GlossaryTerm,
    GlossaryPlace,
    GlossaryFaction,
    CoreTheme,
    EstablishedFact,
)
from app.schemas.agents import (
    ConsistencyChapterRequest,
    ConsistencyProjectRequest,
    ConsistencyFixesRequest,
)

__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "UserInDB",
    # Project
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectList",
    "ContradictionResolution",
    "ContradictionIntentionalRequest",
    # Document
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
    "DocumentList",
    "DocumentVersionCreate",
    "DocumentVersionSummary",
    "DocumentVersionResponse",
    "DocumentVersionList",
    "DocumentCommentCreate",
    "DocumentComment",
    "DocumentCommentList",
    # Character
    "CharacterCreate",
    "CharacterUpdate",
    "CharacterResponse",
    "CharacterList",
    "CharacterGenerateRequest",
    # Instruction
    "InstructionCreate",
    "InstructionUpdate",
    "InstructionResponse",
    "InstructionList",
    # Token
    "Token",
    "TokenPayload",
    # Story Bible
    "StoryBible",
    "StoryBibleDraftValidationRequest",
    "StoryBibleGlossary",
    "StoryBibleValidationResponse",
    "StoryBibleViolation",
    "WorldRule",
    "TimelineEvent",
    "GlossaryTerm",
    "GlossaryPlace",
    "GlossaryFaction",
    "CoreTheme",
    "EstablishedFact",
    # Agents
    "ConsistencyChapterRequest",
    "ConsistencyProjectRequest",
    "ConsistencyFixesRequest",
]
