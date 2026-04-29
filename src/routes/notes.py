from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.schemas.note import NoteCreate, NoteListResponse, NoteRead, NoteUpdate
from src.services import note_service


# Routers define HTTP details and delegate all CRUD work to services.
router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: NoteCreate,
    user_id: int = Query(..., description="Simulated current user ID"),
    db: Session = Depends(get_db),
):
    return note_service.create_note(db=db, user_id=user_id, payload=payload)


@router.get("", response_model=NoteListResponse)
def list_notes(
    user_id: int = Query(..., description="Simulated current user ID"),
    db: Session = Depends(get_db),
):
    notes = note_service.list_notes(db=db, user_id=user_id)
    return NoteListResponse(items=notes)


@router.get("/{note_id}", response_model=NoteRead)
def get_note(
    note_id: int,
    user_id: int = Query(..., description="Simulated current user ID"),
    db: Session = Depends(get_db),
):
    return note_service.get_note(db=db, note_id=note_id, user_id=user_id)


@router.patch("/{note_id}", response_model=NoteRead)
def update_note(
    note_id: int,
    payload: NoteUpdate,
    user_id: int = Query(..., description="Simulated current user ID"),
    db: Session = Depends(get_db),
):
    return note_service.update_note(
        db=db,
        note_id=note_id,
        user_id=user_id,
        payload=payload,
    )


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: int,
    user_id: int = Query(..., description="Simulated current user ID"),
    db: Session = Depends(get_db),
):
    note_service.delete_note(db=db, note_id=note_id, user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
