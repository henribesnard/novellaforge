"""Chat service with context and AI integration"""
import os
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timezone

from app.models.chat import ChatMessage, MessageRole
from app.models.project import Project
from app.models.document import Document
from app.models.character import Character
from app.schemas.chat import ChatMessageResponse
from app.core.config import settings


class ChatService:
    """Service for chat functionality with context awareness"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

    async def _build_project_context(self, project_id: UUID) -> Dict[str, Any]:
        """Build context from project data for AI"""
        # Get project
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            return {}

        # Get documents
        doc_result = await self.db.execute(
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.order_index)
        )
        documents = doc_result.scalars().all()

        # Get characters
        char_result = await self.db.execute(
            select(Character)
            .where(Character.project_id == project_id)
        )
        characters = char_result.scalars().all()

        context = {
            "project": {
                "title": project.title,
                "description": project.description,
                "genre": project.genre.value if project.genre else None,
                "status": project.status.value,
                "structure_template": project.structure_template,
                "word_count": project.current_word_count,
                "target_word_count": project.target_word_count,
            },
            "documents": [
                {
                    "title": doc.title,
                    "type": doc.document_type.value if doc.document_type else None,
                    "word_count": doc.word_count,
                    "content_preview": doc.content[:500] if doc.content else None,
                }
                for doc in documents[:10]  # Limit to 10 most recent
            ],
            "characters": [
                {
                    "name": char.name,
                    "role": char.role,
                    "description": char.description,
                }
                for char in characters
            ],
        }

        return context

    async def _get_conversation_history(
        self, user_id: UUID, project_id: Optional[UUID] = None, limit: int = 10
    ) -> List[ChatMessage]:
        """Get recent conversation history"""
        query = select(ChatMessage).where(ChatMessage.user_id == user_id)

        if project_id:
            query = query.where(ChatMessage.project_id == project_id)

        query = query.order_by(desc(ChatMessage.created_at)).limit(limit)

        result = await self.db.execute(query)
        messages = result.scalars().all()

        return list(reversed(messages))  # Return in chronological order

    def _build_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """Build system prompt with context"""
        base_prompt = """Tu es NovellaForge, un assistant d'écriture littéraire expert et bienveillant.
Ta mission est d'aider les auteurs francophones à créer des romans, nouvelles et œuvres littéraires de qualité.

Tu peux :
- Aider à développer des intrigues et structures narratives
- Créer et développer des personnages complexes et crédibles
- Suggérer des améliorations stylistiques et narratives
- Analyser la cohérence du récit
- Proposer des dialogues authentiques
- Aider à surmonter les blocages créatifs
- Donner des conseils sur la construction de scènes
- Analyser et améliorer le rythme narratif

Ton style est professionnel mais chaleureux, encourageant mais honnête. Tu poses des questions pour mieux comprendre la vision de l'auteur avant de faire des suggestions."""

        if context and context.get("project"):
            project = context["project"]
            context_info = f"""

CONTEXTE DU PROJET ACTUEL :
Titre : {project.get('title')}
Genre : {project.get('genre', 'Non spécifié')}
Description : {project.get('description', 'Aucune description')}
Structure : {project.get('structure_template', 'Aucune structure définie')}
Progression : {project.get('word_count', 0)} / {project.get('target_word_count', 'N/A')} mots
"""

            if context.get("characters"):
                context_info += "\nPERSONNAGES :\n"
                for char in context["characters"]:
                    context_info += f"- {char['name']} ({char['role']}): {char['description'] or 'Pas de description'}\n"

            if context.get("documents"):
                context_info += f"\nDOCUMENTS : {len(context['documents'])} chapitre(s)/scène(s)\n"

            base_prompt += context_info

        return base_prompt

    async def _call_deepseek_api(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        """Call DeepSeek API for chat completion"""
        try:
            import httpx

            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max(1, settings.CHAT_MAX_TOKENS),
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60.0,
                )

                if response.status_code != 200:
                    raise Exception(f"DeepSeek API error: {response.text}")

                result = response.json()
                return result["choices"][0]["message"]["content"]

        except Exception as e:
            print(f"Error calling DeepSeek API: {e}")
            # Fallback response
            return "Je suis désolé, je rencontre actuellement des difficultés techniques. Pouvez-vous reformuler votre question ?"

    async def send_message(
        self,
        user_id: UUID,
        message_content: str,
        project_id: Optional[UUID] = None,
    ) -> ChatMessageResponse:
        """Send a message and get AI response"""

        # Save user message
        user_message = ChatMessage(
            role=MessageRole.USER,
            content=message_content,
            user_id=user_id,
            project_id=project_id,
        )
        self.db.add(user_message)

        # Build context if project_id is provided
        context = None
        if project_id:
            context = await self._build_project_context(project_id)

        # Get conversation history
        history = await self._get_conversation_history(user_id, project_id)

        # Build messages for AI
        ai_messages = [
            {"role": "system", "content": self._build_system_prompt(context)}
        ]

        # Add conversation history
        for msg in history[-10:]:  # Last 10 messages
            ai_messages.append({
                "role": msg.role.value,
                "content": msg.content,
            })

        # Add current message
        ai_messages.append({
            "role": "user",
            "content": message_content,
        })

        # Get AI response
        ai_response = await self._call_deepseek_api(ai_messages)

        # Save assistant message
        assistant_message = ChatMessage(
            role=MessageRole.ASSISTANT,
            content=ai_response,
            user_id=user_id,
            project_id=project_id,
        )
        self.db.add(assistant_message)

        await self.db.commit()
        await self.db.refresh(assistant_message)

        return ChatMessageResponse(
            response=ai_response,
            message_id=str(assistant_message.id),
            project_context=context,
        )

    async def get_history(
        self,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[ChatMessage]:
        """Get chat history"""
        return await self._get_conversation_history(user_id, project_id, limit)
