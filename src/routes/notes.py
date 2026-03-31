from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter()

# Data models (similar to TypeScript interfaces)
class Note(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime

class NoteCreate(BaseModel):
    title: str
    content: str