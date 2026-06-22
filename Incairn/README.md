# Incairn · Daily Cairn Puzzle

A daily number-pyramid puzzle game built with Streamlit. Every day a new board is generated — ten numbered stones that must be arranged into a four-row pyramid. The twist: every parent stone is derived from its two children using a hidden arithmetic rule. Find the rule, fill the cairn.

---

## How to Play

1. Open the game and click **Play Today's Cairn** for the daily puzzle, or choose **Practice** to pick a difficulty.
2. Ten numbered stones appear in a tray at the bottom of the screen.
3. Drag each stone into the pyramid until all ten slots are filled.
4. Press **Check the Cairn** to verify your arrangement.
5. If you're stuck, use a **Hint** (you get three per game).
6. Once the cairn is complete, the hidden rule is revealed on the win screen.

---

## Difficulty Levels

| Level  | Rule Type              | Boards |
|--------|------------------------|--------|
| Easy   | Addition variants      | 10     |
| Medium | Multiplication variants| 10     |
| Hard   | Complex multiplication | 5      |

Easy boards use rules like `parent = left + right`. Hard boards use rules like `parent = left × right − left`, which require more deductive thinking.

---

## Project Structure

```
Incairn/
├── app.py                  # Streamlit app — full game UI (JS-driven, single component)
├── generator.py            # Board generation pipeline (R1 rule framework)
├── feedback.py             # Player feedback / notes system
├── review.py               # Creator review tool (terminal, not for players)
├── incairn_boards.json     # Pre-generated puzzle boards
└── incairn_feedback.json   # Saved player feedback entries
```

### File Overview

**`app.py`** — The entire game UI lives in a single `components.html` call. Python injects board data and handles feedback saves; JavaScript controls all screen navigation (Home, Difficulty, Game, Win, History).

**`generator.py`** — The R1 rule framework. Contains the rule registry across three tiers (easy, medium, hard), the pyramid builder, a safety filter (no duplicates, all values 1–98), a uniqueness/mirror solver, and the batch generator. Run directly to regenerate `incairn_boards.json`.

**`feedback.py`** — Isolated feedback module. Reads and writes `incairn_feedback.json`. Provides `add_note()`, `get_notes_for_board()`, and a `feedback_summary()` for review purposes.

**`review.py`** — A private terminal tool for the creator to walk through every board, verify triplets visually, and mark boards as OK, broken, or needing regeneration. Results are saved to `creator_review.json`.

---

## Setup

**Requirements:** Python 3.10+, Streamlit

```bash
pip install streamlit
```

**Run the game:**

```bash
streamlit run app.py
```

**Regenerate boards:**

```bash
# Default: 10 Easy + 10 Medium + 5 Hard
python generator.py

# Single difficulty
python generator.py --mode easy
python generator.py --mode medium
python generator.py --mode hard

# Show developer inspector after generation
python generator.py --dev
```

**Run the creator review tool:**

```bash
python review.py              # interactive review of all boards
python review.py --auto       # auto-walk, no prompts
```

---

## Rule System (R1 Framework)

Each board has a `generation` field that stores the rule ID used to build it (e.g. `R1_E01`, `R1_M03`, `R1_H02`). The rule ID is stored as developer metadata and is never shown to the player — the UI only says *"a hidden arithmetic rule connects every parent to its two children."*

| Prefix | Tier   | Example rules                     |
|--------|--------|-----------------------------------|
| R1_E   | Easy   | `x+y`, `x+y+1`, `2x+y`, `abs(x-y)` |
| R1_M   | Medium | `x*y`, `x*y+1`, `x*y+y`          |
| R1_H   | Hard   | `x*y−x`, `x*y−y`, `x*y+x+y`      |

---

## Board JSON Schema

Each entry in `incairn_boards.json` follows this shape:

```json
{
  "board_id":     "uuid",
  "generated":    "ISO timestamp",
  "generation":   "R1_E01",
  "difficulty":   "Easy",
  "relationship": "A hidden arithmetic rule...",
  "solution":     [31, 19, 12, 11, 8, 4, 6, 5, 3, 1],
  "puzzle":       [3, 6, 31, 19, 11, 4, 1, 5, 8, 12],
  "board_number": 1
}
```

`solution` is top-down: `[apex, L2-left, L2-right, L3-left, L3-mid, L3-right, base0, base1, base2, base3]`.  
`puzzle` is the same ten values shuffled for the player tray.
