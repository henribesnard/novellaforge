"""Instruction schemas"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class InstructionBase(BaseModel):
    """Base instruction schema"""
    title: str = Field(..., min_length=1, max_length=255)
    detail: str = Field(..., min_length=1, max_length=4000)


class InstructionCreate(InstructionBase):
    """Schema for creating an instruction"""
    pass


class InstructionUpdate(BaseModel):
    """Schema for updating an instruction"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    detail: Optional[str] = Field(None, min_length=1, max_length=4000)


class InstructionResponse(InstructionBase):
    """Schema for instruction response"""
    id: UUID
    created_at: datetime


class InstructionList(BaseModel):
    """Schema for list of instructions"""
    instructions: list[InstructionResponse]
    total: int
