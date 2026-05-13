const DEFAULT_USER_ID = 1;
const API_BASE = "/notes";

const noteList = document.querySelector("#note-list");
const newNoteButton = document.querySelector("#new-note-button");
const saveNoteButton = document.querySelector("#save-note-button");
const deleteNoteButton = document.querySelector("#delete-note-button");
const titleInput = document.querySelector("#note-title");
const contentInput = document.querySelector("#note-content");
const editorStatus = document.querySelector("#editor-status");

let currentNoteId = null;
const currentUserId = getInitialUserId();

function getInitialUserId() {
  const params = new URLSearchParams(window.location.search);
  const userId = Number(params.get("user_id") || params.get("usr_id"));
  return Number.isInteger(userId) && userId > 0 ? userId : DEFAULT_USER_ID;
}

function withUserId(path = "") {
  return `${API_BASE}${path}?user_id=${currentUserId}`;
}

function setStatus(message) {
  editorStatus.textContent = message;
}

function setDeleteEnabled(enabled) {
  deleteNoteButton.disabled = !enabled;
}

function clearEditor(status = "New note") {
  currentNoteId = null;
  titleInput.value = "";
  contentInput.value = "";
  setDeleteEnabled(false);
  setStatus(status);
  document
    .querySelectorAll(".note-item.active")
    .forEach((item) => item.classList.remove("active"));
  titleInput.focus();
}

async function requestJson(url, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  options.headers = headers;
  const response = await fetch(url, options);

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const errorBody = await response.json();
      detail = errorBody.detail || detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return null;
  }

  const data = await response.json();
  return data;
}

async function renderSidebar(selectedId = currentNoteId) {
  noteList.textContent = "";
  const loadingState = document.createElement("div");
  loadingState.className = "empty-state";
  loadingState.textContent = "Loading...";
  noteList.appendChild(loadingState);

  try {
    const data = await requestJson(withUserId());
    const notes = data.items || [];
    noteList.textContent = "";

    if (notes.length === 0) {
      const emptyState = document.createElement("div");
      emptyState.className = "empty-state";
      emptyState.textContent = "No notes for this user.";
      noteList.appendChild(emptyState);
      return;
    }

    notes.forEach((note) => {
      const item = document.createElement("button");
      item.className = "note-item";
      item.type = "button";
      item.dataset.id = note.note_id;

      if (Number(selectedId) === Number(note.note_id)) {
        item.classList.add("active");
      }

      const title = document.createElement("span");
      title.className = "note-title";
      title.textContent = note.title;

      const date = document.createElement("span");
      date.className = "note-date";
      date.textContent = note.note_date;

      item.append(title, date);
      noteList.appendChild(item);
    });
  } catch (error) {
    noteList.textContent = "";
    const errorState = document.createElement("div");
    errorState.className = "error-state";
    errorState.textContent = error.message;
    noteList.appendChild(errorState);
  }
}

async function loadNote(noteId) {
  setStatus("Loading...");

  try {
    const note = await requestJson(withUserId(`/${noteId}`));
    currentNoteId = note.note_id;
    titleInput.value = note.title;
    contentInput.value = note.content;
    setDeleteEnabled(true);
    setStatus(`Loaded note ${note.note_id} for user ${currentUserId}`);
    await renderSidebar(currentNoteId);
  } catch (error) {
    setStatus(error.message);
  }
}

function getEditorPayload() {
  return {
    title: titleInput.value.trim() || "Untitled",
    content: contentInput.value || " ",
  };
}

async function saveNote() {
  const payload = getEditorPayload();
  const isNewNote = currentNoteId === null;
  const url = isNewNote ? withUserId() : withUserId(`/${currentNoteId}`);
  const method = isNewNote ? "POST" : "PATCH";

  saveNoteButton.disabled = true;
  setStatus("Saving...");

  try {
    const savedNote = await requestJson(url, {
      method,
      body: JSON.stringify(payload),
    });
    currentNoteId = savedNote.note_id;
    titleInput.value = savedNote.title;
    contentInput.value = savedNote.content;
    setDeleteEnabled(true);
    setStatus(`Saved for user ${currentUserId}`);
    await renderSidebar(currentNoteId);
  } catch (error) {
    setStatus(error.message);
  } finally {
    saveNoteButton.disabled = false;
  }
}

async function deleteCurrentNote() {
  if (currentNoteId === null) {
    return;
  }

  const shouldDelete = window.confirm("Delete this note?");
  if (!shouldDelete) {
    return;
  }

  deleteNoteButton.disabled = true;
  setStatus("Deleting...");

  try {
    await requestJson(withUserId(`/${currentNoteId}`), { method: "DELETE" });
    clearEditor("Deleted. Select or create a note.");
    await renderSidebar(null);
  } catch (error) {
    setStatus(error.message);
    setDeleteEnabled(true);
  }
}

noteList.addEventListener("click", async (event) => {
  const item = event.target.closest(".note-item");
  if (!item) {
    return;
  }

  await loadNote(item.dataset.id);
});

newNoteButton.addEventListener("click", () => clearEditor("New note"));
saveNoteButton.addEventListener("click", saveNote);
deleteNoteButton.addEventListener("click", deleteCurrentNote);

document.addEventListener("DOMContentLoaded", async () => {
  setDeleteEnabled(false);
  setStatus(`Viewing notes for user ${currentUserId}`);
  await renderSidebar();
});
