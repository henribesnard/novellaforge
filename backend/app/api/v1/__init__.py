"""API v1 router"""
from fastapi import APIRouter

from app.api.v1.endpoints import health, auth, projects, documents, characters, agents, chat, upload, writing

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(characters.router, prefix="/characters", tags=["Characters"])
api_router.include_router(agents.router, prefix="/agents", tags=["AI Agents"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
api_router.include_router(writing.router, prefix="/writing", tags=["Writing"])
