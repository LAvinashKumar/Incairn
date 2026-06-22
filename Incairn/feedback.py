"""
feedback.py — Incairn Feedback System
======================================
Handles reading and writing player feedback notes for boards.

Each feedback entry stores:
    board_id  — which board the note is about
    timestamp — ISO UTC string of when the note was saved
    note      — free-text player comment

WHY a separate module?
  Keeps feedback logic isolated so app.py stays focused on UI.
  Also makes it easy to swap storage (e.g., SQLite) later without
  touching the Streamlit app code.
"""

import json
import os
from datetime import datetime, timezone

FEEDBACK_FILE = "incairn_feedback.json"


# ─────────────────────────────────────────────
# 1. LOAD ALL FEEDBACK
# ─────────────────────────────────────────────

def load_feedback() -> list[dict]:
    """
    Return all stored feedback entries as a list.
    Returns an empty list if the feedback file doesn't exist yet.
    """
    if not os.path.exists(FEEDBACK_FILE):
        return []
    with open(FEEDBACK_FILE, "r") as f:
        return json.load(f)


# ─────────────────────────────────────────────
# 2. SAVE ALL FEEDBACK
# ─────────────────────────────────────────────

def save_feedback(entries: list[dict]) -> None:
    """Persist the full feedback list to JSON."""
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(entries, f, indent=2)


# ─────────────────────────────────────────────
# 3. ADD A NOTE
# ─────────────────────────────────────────────

def add_note(board_id: str, note: str) -> dict:
    """
    Append a new feedback note for a given board_id.

    Returns the newly created entry dict so the caller can
    display a confirmation in the UI.
    """
    if not note or not note.strip():
        raise ValueError("Note cannot be empty.")

    entry = {
        "board_id": board_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "note": note.strip(),
    }

    entries = load_feedback()
    entries.append(entry)
    save_feedback(entries)
    return entry


# ─────────────────────────────────────────────
# 4. GET NOTES FOR A SPECIFIC BOARD
# ─────────────────────────────────────────────

def get_notes_for_board(board_id: str) -> list[dict]:
    """Return all feedback entries for a specific board_id."""
    return [e for e in load_feedback() if e["board_id"] == board_id]


# ─────────────────────────────────────────────
# 5. FEEDBACK SUMMARY (for Week 4 review support)
# ─────────────────────────────────────────────

def feedback_summary() -> dict:
    """
    Return aggregate stats useful for the Week 4 review:
      - total_notes
      - boards_with_feedback
      - most_recent_note
    """
    entries = load_feedback()
    if not entries:
        return {"total_notes": 0, "boards_with_feedback": 0, "most_recent_note": None}

    boards_seen = {e["board_id"] for e in entries}
    most_recent = max(entries, key=lambda e: e["timestamp"])

    return {
        "total_notes": len(entries),
        "boards_with_feedback": len(boards_seen),
        "most_recent_note": most_recent,
    }
