from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.models.note import Note
from src.models.user import User
from src.schemas.note import NoteCreate, NoteUpdate
from src.services import note_service


def make_query(first=None, all_=None):
	query = MagicMock()
	query.filter.return_value = query
	query.order_by.return_value = query
	query.first.return_value = first
	query.all.return_value = [] if all_ is None else all_
	return query


def test_get_user_or_404_returns_user():
	user = User(user_id=1, user_name="A", user_email="a@example.com")
	user_query = make_query(first=user)
	db = MagicMock(spec=Session)
	db.query.return_value = user_query

	result = note_service.get_user_or_404(db=db, user_id=1)

	assert result is user


def test_get_user_or_404_missing_user_raises():
	user_query = make_query(first=None)
	db = MagicMock(spec=Session)
	db.query.return_value = user_query

	with pytest.raises(HTTPException) as excinfo:
		note_service.get_user_or_404(db=db, user_id=99)

	assert excinfo.value.status_code == 404
	assert excinfo.value.detail == "User not found"


def test_get_note_or_404_missing_note_raises():
	user = User(user_id=1, user_name="A", user_email="a@example.com")
	user_query = make_query(first=user)
	note_query = make_query(first=None)
	db = MagicMock(spec=Session)
	db.query = MagicMock(side_effect=[user_query, note_query])

	with pytest.raises(HTTPException) as excinfo:
		note_service.get_note_or_404(db=db, note_id=10, user_id=1)

	assert excinfo.value.status_code == 404
	assert excinfo.value.detail == "Note not found"


def test_create_note_commits_and_returns_note():
	user = User(user_id=1, user_name="A", user_email="a@example.com")
	user_query = make_query(first=user)
	db = MagicMock(spec=Session)
	db.query.return_value = user_query

	payload = NoteCreate(title="Hello", content="World")
	result = note_service.create_note(db=db, user_id=1, payload=payload)

	assert isinstance(result, Note)
	assert result.user_id == 1
	assert result.title == "Hello"
	assert result.content == "World"
	db.add.assert_called_once_with(result)
	db.commit.assert_called_once()
	db.refresh.assert_called_once_with(result)


def test_list_notes_returns_sorted_notes():
	user = User(user_id=1, user_name="A", user_email="a@example.com")
	notes = [
		Note(
			note_id=2,
			user_id=1,
			title="B",
			content="second",
			note_date=date(2026, 5, 3),
		),
		Note(
			note_id=1,
			user_id=1,
			title="A",
			content="first",
			note_date=date(2026, 5, 2),
		),
	]
	user_query = make_query(first=user)
	note_query = make_query(all_=notes)
	db = MagicMock(spec=Session)
	db.query = MagicMock(side_effect=[user_query, note_query])

	result = note_service.list_notes(db=db, user_id=1)

	assert result == notes
	assert note_query.order_by.called


def test_get_note_returns_note():
	user = User(user_id=1, user_name="A", user_email="a@example.com")
	note = Note(
		note_id=1,
		user_id=1,
		title="A",
		content="first",
		note_date=date(2026, 5, 3),
	)
	user_query = make_query(first=user)
	note_query = make_query(first=note)
	db = MagicMock(spec=Session)
	db.query = MagicMock(side_effect=[user_query, note_query])

	result = note_service.get_note(db=db, note_id=1, user_id=1)

	assert result is note


def test_update_note_no_fields_raises():
	user = User(user_id=1, user_name="A", user_email="a@example.com")
	note = Note(
		note_id=1,
		user_id=1,
		title="Old",
		content="text",
		note_date=date(2026, 5, 3),
	)
	user_query = make_query(first=user)
	note_query = make_query(first=note)
	db = MagicMock(spec=Session)
	db.query = MagicMock(side_effect=[user_query, note_query])

	with pytest.raises(HTTPException) as excinfo:
		note_service.update_note(
			db=db,
			note_id=1,
			user_id=1,
			payload=NoteUpdate(),
		)

	assert excinfo.value.status_code == 400
	assert excinfo.value.detail == "No fields to update"


def test_update_note_updates_fields():
	user = User(user_id=1, user_name="A", user_email="a@example.com")
	note = Note(
		note_id=1,
		user_id=1,
		title="Old",
		content="text",
		note_date=date(2026, 5, 3),
	)
	user_query = make_query(first=user)
	note_query = make_query(first=note)
	db = MagicMock(spec=Session)
	db.query = MagicMock(side_effect=[user_query, note_query])

	payload = NoteUpdate(title="New")
	result = note_service.update_note(
		db=db,
		note_id=1,
		user_id=1,
		payload=payload,
	)

	assert result is note
	assert note.title == "New"
	db.commit.assert_called_once()
	db.refresh.assert_called_once_with(note)


def test_delete_note_deletes_and_commits():
	user = User(user_id=1, user_name="A", user_email="a@example.com")
	note = Note(
		note_id=1,
		user_id=1,
		title="A",
		content="text",
		note_date=date(2026, 5, 3),
	)
	user_query = make_query(first=user)
	note_query = make_query(first=note)
	db = MagicMock(spec=Session)
	db.query = MagicMock(side_effect=[user_query, note_query])

	note_service.delete_note(db=db, note_id=1, user_id=1)

	db.delete.assert_called_once_with(note)
	db.commit.assert_called_once()
