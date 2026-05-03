from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models.note import Note
from src.models.user import User
from src.schemas.note import NoteCreate, NoteUpdate


# Services contain business rules and database queries, keeping routers thin.
def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def get_note_or_404(db: Session, note_id: int, user_id: int) -> Note:
    get_user_or_404(db, user_id)

    note = (
        db.query(Note)
        .filter(Note.note_id == note_id, Note.user_id == user_id)
        .first()
    )
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    return note


def create_note(db: Session, user_id: int, payload: NoteCreate) -> Note:
    get_user_or_404(db, user_id)

    note = Note(user_id=user_id, title=payload.title, content=payload.content)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_notes(db: Session, user_id: int) -> list[Note]:
    get_user_or_404(db, user_id)

    return (
        db.query(Note)
        .filter(Note.user_id == user_id)
        .order_by(Note.note_id.desc())
        .all()
    )


def get_note(db: Session, note_id: int, user_id: int) -> Note:
    return get_note_or_404(db, note_id, user_id)


def update_note(
    db: Session,
    note_id: int,
    user_id: int,
    payload: NoteUpdate,
) -> Note:
    note = get_note_or_404(db, note_id, user_id)
    update_data = payload.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    for field, value in update_data.items():
        setattr(note, field, value)

    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, note_id: int, user_id: int) -> None:
    note = get_note_or_404(db, note_id, user_id)
    db.delete(note)
    db.commit()
