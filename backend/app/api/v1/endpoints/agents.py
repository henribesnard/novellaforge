"""AI Agents endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from pydantic import BaseModel
from uuid import UUID

from app.db.session import get_db
from app.models.user import User
from app.core.security import get_current_active_user
from app.services.agents import AgentFactory
from app.services.context_service import ProjectContextService

router = APIRouter()


class AgentTaskRequest(BaseModel):
    """Request schema for agent tasks"""
    agent_type: str
    action: str
    task_data: Dict[str, Any]
    project_id: UUID | None = None


class AgentTaskResponse(BaseModel):
    """Response schema for agent tasks"""
    success: bool
    result: Dict[str, Any]
    agent_name: str


@router.get("/list")
async def list_agents():
    """List all available AI agents"""
    return {
        "agents": AgentFactory.get_available_agents(),
        "total": len(AgentFactory.list_agent_types()),
    }


@router.post("/execute", response_model=AgentTaskResponse)
async def execute_agent_task(
    request: AgentTaskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Execute a task with a specific AI agent.

    Available agents:
    - narrative_architect: Structure narrative
    - character_manager: Gestion des personnages
    - style_expert: Qualité stylistique
    - dialogue_master: Dialogues authentiques

    Args:
        agent_type: Type d'agent à utiliser
        action: Action spécifique à exécuter
        task_data: Données pour la tâche
        project_id: ID du projet (optionnel, pour le contexte)
    """
    try:
        # Create agent instance
        agent = AgentFactory.create_agent(request.agent_type)

        context = None
        if request.project_id:
            context_service = ProjectContextService(db)
            context = await context_service.build_project_context(
                project_id=request.project_id,
                user_id=current_user.id,
            )

        # Execute task
        result = await agent.execute(request.task_data, context)

        return AgentTaskResponse(
            success=result.get("success", True),
            result=result,
            agent_name=agent.name,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing agent task: {str(e)}",
        )
