from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class NoteBase(BaseModel):
    """Base schema for Note"""
    content: str = Field(..., min_length=1, max_length=5000)
    author: str = Field(..., min_length=2, max_length=100)


class NoteCreate(NoteBase):
    """Schema for creating a new note"""
    pass


class NoteResponse(NoteBase):
    """Schema for note responses (includes DB fields)"""
    id: int
    candidate_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
