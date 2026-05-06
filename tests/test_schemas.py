from datetime import date

import pytest
from pydantic import ValidationError

from src.schemas.note import NoteCreate, NoteListResponse, NoteRead, NoteUpdate


def test_note_create_valid():
	payload = NoteCreate(title="Hello", content="World")
	assert payload.title == "Hello"
	assert payload.content == "World"


def test_note_create_rejects_empty_title():
	with pytest.raises(ValidationError):
		NoteCreate(title="", content="World")


def test_note_create_rejects_long_title():
	with pytest.raises(ValidationError):
		NoteCreate(title="a" * 201, content="World")


def test_note_create_rejects_empty_content():
	with pytest.raises(ValidationError):
		NoteCreate(title="Hello", content="")


def test_note_read_requires_positive_id():
	with pytest.raises(ValidationError):
		NoteRead(
			note_id=0,
			user_id=1,
			title="Hello",
			content="World",
			note_date=date(2026, 5, 3),
		)


def test_note_update_allows_partial_update():
	payload = NoteUpdate(title="Updated")
	assert payload.title == "Updated"
	assert payload.content is None


def test_note_update_rejects_empty_title():
	with pytest.raises(ValidationError):
		NoteUpdate(title="")


def test_note_list_response_accepts_items():
	note = NoteRead(
		note_id=1,
		user_id=1,
		title="Hello",
		content="World",
		note_date=date(2026, 5, 3),
	)
	response = NoteListResponse(items=[note])
	assert response.items[0].note_id == 1
