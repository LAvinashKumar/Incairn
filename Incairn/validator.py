"""
validator.py — Incairn Rule Engine & Solution Validator
=========================================================
Single source of truth for all arithmetic rules used in the game.
Used by both api.py (backend validation) and can be imported anywhere.

Covers:
  - R1 rules  (original generator.py boards)
  - R2 rules  (new boards from boards_r2 — derived dynamically from
               the relationship string stored in each board)
  - Legacy generation IDs (Gen01_Add etc.)

Public API:
  get_rule_fn(generation_id, relationship="") -> callable | None
  check_solution(solution, generation_id, relationship="") -> bool
  get_hint(solution, player_placement, generation_id, relationship="") -> dict
"""

import math
import re
from typing import Callable, Optional

# ── Pyramid parent→(left, right) triplets ─────────────────────
# Indices map to the 10-cell top-down layout:
#   [0]
#  [1][2]
# [3][4][5]
#[6][7][8][9]
TRIPLETS: list[tuple[int, int, int]] = [
    (0, 1, 2),
    (1, 3, 4),
    (2, 4, 5),
    (3, 6, 7),
    (4, 7, 8),
    (5, 8, 9),
]


# ══════════════════════════════════════════════════════════════
# R1 STATIC RULE TABLE
# ══════════════════════════════════════════════════════════════

_R1_RULES: dict[str, Callable[[int, int], float]] = {
    # Legacy IDs (backward compat)
    "Gen01_Add":      lambda x, y: x + y,
    "Gen02_Mul":      lambda x, y: x * y,
    "Gen03_AddPlus1": lambda x, y: x + y + 1,
    # R1 Easy
    "R1_E01": lambda x, y: x + y,
    "R1_E02": lambda x, y: x + y + 1,
    "R1_E03": lambda x, y: x + y - 1,
    "R1_E04": lambda x, y: 2 * x + y,
    "R1_E05": lambda x, y: x + 2 * y,
    "R1_E06": lambda x, y: abs(x - y),
    "R1_E07": lambda x, y: max(x, y),
    "R1_E08": lambda x, y: min(x, y),
    # R1 Medium
    "R1_M01": lambda x, y: x * y,
    "R1_M02": lambda x, y: x * y + 1,
    "R1_M03": lambda x, y: x * y - 1,
    "R1_M04": lambda x, y: x * y + x,
    "R1_M05": lambda x, y: x * y + y,
    # R1 Hard
    "R1_H01": lambda x, y: x * y + x + y,
    "R1_H02": lambda x, y: x * y - x,
    "R1_H03": lambda x, y: x * y - y,
    "R1_H04": lambda x, y: x * y - (x + y),
    "R1_H05": lambda x, y: x * y + 2,
}


# ══════════════════════════════════════════════════════════════
# R2 DYNAMIC RULE BUILDER
# Parses the relationship string stored on each R2 board and
# returns a callable.  All R2 relationship strings follow the
# pattern "z = <expr>" where expr is one of the forms below.
# ══════════════════════════════════════════════════════════════

def _build_r2_fn(rel: str) -> Optional[Callable[[int, int], float]]:
    """
    Convert a relationship string (e.g. 'z=x+y+3') into a callable.
    Returns None if the pattern is unrecognised.
    """
    r = rel.replace(" ", "").lower()

    # ── Exact matches ─────────────────────────────────────────
    if r in ("z=x+y", "z=y+x"):
        return lambda x, y: x + y
    if r == "z=2x+y":
        return lambda x, y: 2 * x + y
    if r == "z=x+2y":
        return lambda x, y: x + 2 * y
    if r == "z=max(x,y)":
        return lambda x, y: max(x, y)
    if r == "z=min(x,y)":
        return lambda x, y: min(x, y)
    if r == "z=x*y":
        return lambda x, y: x * y
    if r == "z=x*y-x":
        return lambda x, y: x * y - x
    if r == "z=x*y-y":
        return lambda x, y: x * y - y
    if r == "z=(x*y)/2":
        return lambda x, y: (x * y) / 2
    if r == "z=(x*y)/3":
        return lambda x, y: (x * y) / 3

    # ── z = x + y ± N ─────────────────────────────────────────
    m = re.match(r"^z=x\+y([+\-]\d+)$", r)
    if m:
        k = int(m.group(1))
        return lambda x, y, _k=k: x + y + _k

    # ── z = x * y ± N ─────────────────────────────────────────
    m = re.match(r"^z=x\*y([+\-]\d+)$", r)
    if m:
        k = int(m.group(1))
        return lambda x, y, _k=k: x * y + _k

    # ── z = (x + y) / 2 ± N  (or just /2) ────────────────────
    m = re.match(r"^z=\(x\+y\)\/2([+\-]\d+)?$", r)
    if m:
        k = int(m.group(1)) if m.group(1) else 0
        return lambda x, y, _k=k: (x + y) / 2 + _k

    # ── z = (x * y) / N ───────────────────────────────────────
    m = re.match(r"^z=\(x\*y\)\/(\d+)$", r)
    if m:
        d = int(m.group(1))
        return lambda x, y, _d=d: (x * y) / _d

    return None  # unrecognised pattern


# ══════════════════════════════════════════════════════════════
# PUBLIC: get_rule_fn
# ══════════════════════════════════════════════════════════════

def get_rule_fn(
    generation_id: str,
    relationship: str = "",
) -> Optional[Callable[[int, int], float]]:
    """
    Return the rule function for a board.

    R1 / Legacy boards: looked up from the static table by generation_id.
    R2 boards         : derived dynamically from the relationship string.

    Returns None if the rule cannot be resolved.
    """
    # R1 / legacy
    if generation_id in _R1_RULES:
        return _R1_RULES[generation_id]

    # R2 — generation IDs look like "R2_E01", "R2_M07", etc.
    if generation_id.startswith("R2_") and relationship:
        return _build_r2_fn(relationship)

    # Last-ditch: try parsing the relationship string directly
    # (handles boards that may have been saved without a generation ID)
    if relationship:
        return _build_r2_fn(relationship)

    return None


# ══════════════════════════════════════════════════════════════
# PUBLIC: check_solution
# ══════════════════════════════════════════════════════════════

def check_solution(
    solution: list[int],
    generation_id: str,
    relationship: str = "",
) -> bool:
    """
    Return True if every triplet in `solution` satisfies the rule.

    solution       : 10-element list in top-down order
                     [apex, L2L, L2R, L3L, L3M, L3R, b0, b1, b2, b3]
    generation_id  : e.g. "R1_E01" or "R2_M07"
    relationship   : relationship formula string (required for R2 boards)
    """
    fn = get_rule_fn(generation_id, relationship)
    if fn is None:
        return False

    for parent, left, right in TRIPLETS:
        try:
            expected = fn(solution[left], solution[right])
            # Use integer comparison (rules may return float for /2, /3)
            if int(expected) != expected:
                return False
            if solution[parent] != int(expected):
                return False
        except Exception:
            return False

    return True


# ══════════════════════════════════════════════════════════════
# PUBLIC: get_hint
# Returns the index and correct value of the first misplaced or
# empty cell, scanning base → apex (bottom-up) so the hint is
# always actionable.
# ══════════════════════════════════════════════════════════════

def get_hint(
    solution: list[int],
    player_placement: list[Optional[int]],
    generation_id: str,
    relationship: str = "",
) -> dict:
    """
    Given the correct solution and the player's current placement
    (None = empty cell), return a hint dict.

    Returns:
        { "cell_index": int, "correct_value": int }   — hint found
        { "cell_index": None, "correct_value": None }  — all correct
    """
    # Scan base → apex so lowest actionable cell is hinted first
    scan_order = [6, 7, 8, 9, 3, 4, 5, 1, 2, 0]

    for idx in scan_order:
        placed = player_placement[idx]
        if placed is None or placed != solution[idx]:
            return {"cell_index": idx, "correct_value": solution[idx]}

    return {"cell_index": None, "correct_value": None}
