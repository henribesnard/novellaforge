"""Character service"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.character import Character
from app.models.project import Project
from app.schemas.character import CharacterCreate, CharacterUpdate


class CharacterService:
    """Service for character operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _verify_project_ownership(
        self,
        project_id: UUID,
        user_id: UUID
    ) -> Project:
        """
        Verify that user owns the project.

        Raises:
            HTTPException: If project not found or not owned by user
        """
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == user_id
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )

        return project

    async def get_by_id(
        self,
        character_id: UUID,
        user_id: UUID
    ) -> Optional[Character]:
        """
        Get character by ID (with ownership check via project).

        Args:
            character_id: Character ID
            user_id: User ID

        Returns:
            Character if found and user has access
        """
        result = await self.db.execute(
            select(Character)
            .join(Project)
            .where(
                Character.id == character_id,
                Project.owner_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_all_by_project(
        self,
        project_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Character], int]:
        """
        Get all characters for a project.

        Args:
            project_id: Project ID
            user_id: User ID (for ownership check)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (characters list, total count)
        """
        # Verify ownership
        await self._verify_project_ownership(project_id, user_id)

        # Get total count
        count_result = await self.db.execute(
            select(func.count(Character.id)).where(
                Character.project_id == project_id
            )
        )
        total = count_result.scalar()

        # Get characters
        result = await self.db.execute(
            select(Character)
            .where(Character.project_id == project_id)
            .order_by(Character.name.asc())
            .offset(skip)
            .limit(limit)
        )
        characters = result.scalars().all()

        return list(characters), total

    async def create(
        self,
        character_data: CharacterCreate,
        user_id: UUID
    ) -> Character:
        """
        Create a new character.

        Args:
            character_data: Character creation data
            user_id: User ID (for ownership check)

        Returns:
            Created character
        """
        # Verify ownership
        await self._verify_project_ownership(character_data.project_id, user_id)

        character = Character(
            name=character_data.name,
            description=character_data.description,
            physical_description=character_data.physical_description,
            personality=character_data.personality,
            backstory=character_data.backstory,
            character_metadata=character_data.metadata or {},
            project_id=character_data.project_id
        )

        self.db.add(character)
        await self.db.commit()
        await self.db.refresh(character)

        return character

    async def update(
        self,
        character_id: UUID,
        character_data: CharacterUpdate,
        user_id: UUID
    ) -> Character:
        """
        Update character.

        Args:
            character_id: Character ID
            character_data: Update data
            user_id: User ID (for ownership check)

        Returns:
            Updated character

        Raises:
            HTTPException: If character not found or access denied
        """
        character = await self.get_by_id(character_id, user_id)
        if not character:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Character not found"
            )

        # Update fields
        update_data = character_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(character, field, value)

        await self.db.commit()
        await self.db.refresh(character)

        return character

    async def delete(self, character_id: UUID, user_id: UUID) -> bool:
        """
        Delete character.

        Args:
            character_id: Character ID
            user_id: User ID (for ownership check)

        Returns:
            True if deleted, False if not found
        """
        character = await self.get_by_id(character_id, user_id)
        if not character:
            return False

        await self.db.delete(character)
        await self.db.commit()

        return True
