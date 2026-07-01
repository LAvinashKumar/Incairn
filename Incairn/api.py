"""
api.py — Incairn FastAPI Backend
==================================
Run:  uvicorn api:app --reload
Docs: http://127.0.0.1:8000/docs

Endpoints
---------
POST /incairn/load      — load daily / practice / past board
POST /incairn/check     — validate player's solution
GET  /incairn/answer    — reveal the correct solution
POST /incairn/hint      — return next hint cell
POST /incairn/feedback  — save player feedback (delegates to feedback.py)

Architecture
------------
  Streamlit frontend  →  fetch() calls  →  FastAPI (this file)
                                              ↓
                                    validator.py  feedback.py
                                              ↓
                                    incairn_boards.json
                                    incairn_feedback.json
"""

import hashlib
import json
import os
import secrets
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from validator import check_solution, get_hint, get_rule_fn
from feedback import add_note

# ── Paths ──────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
BOARDS_FILE = BASE_DIR / "incairn_boards.json"

# ── In-memory session store  { token: session_dict } ──────────
# Lightweight — no database needed.  Sessions expire naturally
# when the server restarts (stateless gameplay — client holds
# all persistence in localStorage anyway).
_sessions: dict[str, dict] = {}


# ══════════════════════════════════════════════════════════════
# APP SETUP
# ══════════════════════════════════════════════════════════════

app = FastAPI(
    title="Incairn API",
    description=(
        "Backend for the Incairn daily number-pyramid puzzle game. "
        "Handles board selection, solution validation, hints, "
        "answer reveal, and feedback."
    ),
    version="2.0.0",
)

# Allow the Streamlit frontend (same machine or Streamlit Cloud) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════
# BOARD LOADER  (cached at module level — file read once)
# ══════════════════════════════════════════════════════════════

def _load_boards() -> list[dict]:
    with open(BOARDS_FILE) as f:
        return json.load(f)

_BOARDS: list[dict] = _load_boards()


def _slim(b: dict) -> dict:
    """Return the player-facing subset of a board (no solution)."""
    num = b.get("board_number", 0)
    bid = (b["board_id"] if b["board_id"].startswith("R2-")
           else f"{b['difficulty'].lower()}-{str(num).zfill(2)}")
    return {
        "board_id":     b["board_id"],
        "bid":          bid,
        "difficulty":   b["difficulty"],
        "numbers":      b["puzzle"],       # shuffled — what player sees
        "generation":   b.get("generation", ""),
        "relationship": b.get("relationship", ""),
    }


def _get_board_by_id(board_id: str) -> Optional[dict]:
    for b in _BOARDS:
        if b["board_id"] == board_id:
            return b
    return None


# ── Daily board selection ─────────────────────────────────────

def _daily_board_for_date(d: date) -> dict:
    """
    Deterministically pick today's board using the date as a seed.
    Every player with the same calendar date gets the same board.
    """
    seed = int(hashlib.md5(d.isoformat().encode()).hexdigest(), 16)
    idx  = seed % len(_BOARDS)
    return _BOARDS[idx]


def _parse_tz_offset(tz_offset: Optional[int]) -> date:
    """
    Return 'today' in the player's local timezone.

    tz_offset: minutes WEST of UTC (JavaScript's getTimezoneOffset()).
      e.g.  India (UTC+5:30) → -330
            London (UTC+0)   →    0
            New York (UTC-5) →  300

    If tz_offset is None, fall back to UTC.
    """
    now_utc = datetime.now(timezone.utc)
    if tz_offset is None:
        return now_utc.date()
    # JS getTimezoneOffset returns minutes WEST, so subtract to get local time
    offset_seconds = -tz_offset * 60
    from datetime import timedelta
    local_now = now_utc + timedelta(seconds=offset_seconds)
    return local_now.date()


# ══════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ══════════════════════════════════════════════════════════════

class LoadRequest(BaseModel):
    mode: str = Field(
        ...,
        description="One of: 'daily', 'practice', 'past'",
        examples=["daily", "practice", "past"],
    )
    difficulty: Optional[str] = Field(
        None,
        description="Required when mode='practice'. One of: Easy, Medium, Hard",
        examples=["Easy", "Medium", "Hard"],
    )
    date: Optional[str] = Field(
        None,
        description="Required when mode='past'. ISO date string YYYY-MM-DD",
        examples=["2026-07-15"],
    )
    tz_offset: Optional[int] = Field(
        None,
        description=(
            "Player's timezone offset in minutes (JavaScript getTimezoneOffset()). "
            "Used for daily mode so midnight resets in the player's local timezone. "
            "e.g. India = -330, London = 0, New York = 300"
        ),
        examples=[-330, 0, 300],
    )


class LoadResponse(BaseModel):
    board_id:      str
    bid:           str
    difficulty:    str
    numbers:       list[int]
    generation:    str
    relationship:  str
    session_token: str


class CheckRequest(BaseModel):
    board_id:        str
    player_solution: list[int] = Field(
        ...,
        description=(
            "10-element list in top-down pyramid order: "
            "[apex, L2L, L2R, L3L, L3M, L3R, base0, base1, base2, base3]"
        ),
    )
    session_token: str


class CheckResponse(BaseModel):
    correct: bool


class HintRequest(BaseModel):
    board_id:         str
    player_placement: list[Optional[int]] = Field(
        ...,
        description=(
            "10-element list — current player placement. "
            "Use null / None for empty cells."
        ),
    )
    session_token: str


class HintResponse(BaseModel):
    cell_index:    Optional[int]
    correct_value: Optional[int]
    hints_used:    int
    hints_left:    int


class AnswerRequest(BaseModel):
    board_id: str


class AnswerResponse(BaseModel):
    solution:     list[int]
    relationship: str


class FeedbackRequest(BaseModel):
    board_id:   str
    rating:     Optional[int] = Field(None, ge=1, le=5, description="1–5 star rating")
    comment:    Optional[str] = Field(None, description="Free-text comment")


class FeedbackResponse(BaseModel):
    saved:     bool
    message:   str


# ══════════════════════════════════════════════════════════════
# SESSION HELPERS
# ══════════════════════════════════════════════════════════════

def _create_session(board: dict) -> str:
    """Create a new session for a game and return the token."""
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        "board_id":   board["board_id"],
        "hints_used": 0,
        "hints_max":  3,
        "solved":     False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return token


def _get_session(token: str) -> dict:
    """Retrieve a session or raise 401."""
    session = _sessions.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")
    return session


def _verify_session_board(session: dict, board_id: str) -> None:
    """Ensure the session belongs to the requested board."""
    if session["board_id"] != board_id:
        raise HTTPException(
            status_code=403,
            detail="Session token does not match the requested board.",
        )


# ══════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════

# ── Health check ─────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "service": "Incairn API",
        "version": "2.0.0",
        "boards_loaded": len(_BOARDS),
        "status": "ok",
    }


# ── 1. Load Board ─────────────────────────────────────────────
@app.post(
    "/incairn/load",
    response_model=LoadResponse,
    tags=["Game"],
    summary="Load a board",
    description=(
        "Load a board in one of three modes:\n\n"
        "- **daily** — today's puzzle (same for all players on the same date).\n"
        "  Pass `tz_offset` (JS `getTimezoneOffset()`) for correct midnight reset.\n"
        "- **practice** — random board at chosen difficulty.\n"
        "- **past** — replay a specific date's daily cairn."
    ),
)
def load_board(req: LoadRequest) -> LoadResponse:
    import random

    mode = req.mode.lower()

    if mode == "daily":
        local_date = _parse_tz_offset(req.tz_offset)
        board = _daily_board_for_date(local_date)

    elif mode == "practice":
        if not req.difficulty:
            raise HTTPException(
                status_code=422,
                detail="'difficulty' is required for practice mode.",
            )
        diff = req.difficulty.strip().capitalize()
        pool = [b for b in _BOARDS if b["difficulty"] == diff]
        if not pool:
            raise HTTPException(
                status_code=404,
                detail=f"No boards found for difficulty '{diff}'.",
            )
        board = random.choice(pool)

    elif mode == "past":
        if not req.date:
            raise HTTPException(
                status_code=422,
                detail="'date' is required for past mode (YYYY-MM-DD).",
            )
        try:
            past_date = date.fromisoformat(req.date)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="Invalid date format. Use YYYY-MM-DD.",
            )
        board = _daily_board_for_date(past_date)

    else:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown mode '{req.mode}'. Use 'daily', 'practice', or 'past'.",
        )

    token = _create_session(board)
    slim  = _slim(board)

    return LoadResponse(
        board_id      = slim["board_id"],
        bid           = slim["bid"],
        difficulty    = slim["difficulty"],
        numbers       = slim["numbers"],
        generation    = slim["generation"],
        relationship  = slim["relationship"],
        session_token = token,
    )


# ── 2. Check Solution ─────────────────────────────────────────
@app.post(
    "/incairn/check",
    response_model=CheckResponse,
    tags=["Game"],
    summary="Check player's solution",
    description=(
        "Validate the player's 10-element solution array against the board's rule. "
        "The array must be in top-down pyramid order: "
        "[apex, L2L, L2R, L3L, L3M, L3R, base0, base1, base2, base3]."
    ),
)
def check(req: CheckRequest) -> CheckResponse:
    session = _get_session(req.session_token)
    _verify_session_board(session, req.board_id)

    if len(req.player_solution) != 10:
        raise HTTPException(status_code=422, detail="player_solution must have exactly 10 values.")

    board = _get_board_by_id(req.board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found.")

    correct = check_solution(
        solution       = req.player_solution,
        generation_id  = board.get("generation", ""),
        relationship   = board.get("relationship", ""),
    )

    if correct:
        session["solved"] = True

    return CheckResponse(correct=correct)


# ── 3. Reveal Answer ─────────────────────────────────────────
@app.get(
    "/incairn/answer",
    response_model=AnswerResponse,
    tags=["Game"],
    summary="Reveal the correct solution",
    description="Return the full solution and the relationship formula for a board.",
)
def answer(board_id: str) -> AnswerResponse:
    board = _get_board_by_id(board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found.")

    return AnswerResponse(
        solution     = board["solution"],
        relationship = board.get("relationship", ""),
    )


# ── 4. Hint ───────────────────────────────────────────────────
@app.post(
    "/incairn/hint",
    response_model=HintResponse,
    tags=["Game"],
    summary="Get a hint",
    description=(
        "Return the index and correct value of the next misplaced or empty cell. "
        "Players get 3 hints per game. The hint scans base → apex so the "
        "lowest actionable cell is always suggested first."
    ),
)
def hint(req: HintRequest) -> HintResponse:
    session = _get_session(req.session_token)
    _verify_session_board(session, req.board_id)

    if session["hints_used"] >= session["hints_max"]:
        raise HTTPException(status_code=403, detail="No hints remaining.")

    if len(req.player_placement) != 10:
        raise HTTPException(status_code=422, detail="player_placement must have exactly 10 values.")

    board = _get_board_by_id(req.board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found.")

    result = get_hint(
        solution          = board["solution"],
        player_placement  = req.player_placement,
        generation_id     = board.get("generation", ""),
        relationship      = board.get("relationship", ""),
    )

    # Only decrement hint count when an actionable hint is returned
    if result["cell_index"] is not None:
        session["hints_used"] += 1

    return HintResponse(
        cell_index    = result["cell_index"],
        correct_value = result["correct_value"],
        hints_used    = session["hints_used"],
        hints_left    = session["hints_max"] - session["hints_used"],
    )


# ── 5. Save Feedback ─────────────────────────────────────────
@app.post(
    "/incairn/feedback",
    response_model=FeedbackResponse,
    tags=["Feedback"],
    summary="Save player feedback",
    description=(
        "Save a rating and/or comment for a completed board. "
        "Delegates to feedback.py and stores in incairn_feedback.json."
    ),
)
def feedback(req: FeedbackRequest) -> FeedbackResponse:
    note_parts = []
    if req.rating is not None:
        note_parts.append(f"Rating: {req.rating}/5")
    if req.comment and req.comment.strip():
        note_parts.append(req.comment.strip())

    if not note_parts:
        raise HTTPException(
            status_code=422,
            detail="Provide at least a rating or a comment.",
        )

    note_text = " | ".join(note_parts)

    try:
        entry = add_note(board_id=req.board_id, note=note_text)
        return FeedbackResponse(saved=True, message="Feedback saved.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {e}")
