from datetime import date

from pydantic import BaseModel, ConfigDict, Field


# Pydantic schemas define the HTTP request and response shapes.
class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)


class NoteRead(BaseModel):
    note_id: int
    user_id: int
    title: str
    content: str
    note_date: date

    model_config = ConfigDict(from_attributes=True)


class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)


class NoteListResponse(BaseModel):
    items: list[NoteRead]
