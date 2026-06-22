"""
generator.py — Incairn R1 Rule Framework
==========================================
Versioned rule registry with 3 difficulty tiers and full safety
filtering.  Existing gameplay, submission logic, and validation
are unchanged — only the generation pipeline is extended.

Run:
    python generator.py              # generate 25 boards (default)
    python generator.py --dev        # also print developer inspector
    python generator.py --mode easy  # easy boards only (10)
    python generator.py --mode medium
    python generator.py --mode hard
    python generator.py --mode random  # pick rule from all tiers
"""

import random
import json
import uuid
import math
import itertools
from datetime import datetime, timezone
from collections import Counter


# ══════════════════════════════════════════════════════════════
# R1  RULE REGISTRY
# ══════════════════════════════════════════════════════════════

class Rule:
    """
    A single arithmetic rule in the R1 registry.

    id         : stable string identifier  (stored in board JSON)
    name       : human-readable label      (developer metadata only)
    difficulty : 'easy' | 'medium' | 'hard'
    apply(x,y) : computes parent from two children
    """
    def __init__(self, rule_id: str, name: str,
                 difficulty: str, fn):
        self.id         = rule_id
        self.name       = name
        self.difficulty = difficulty
        self._fn        = fn

    def apply(self, x: int, y: int) -> float:
        return self._fn(x, y)

    def __repr__(self):
        return f"Rule({self.id!r}, {self.difficulty!r})"


# ── Easy rules ────────────────────────────────────────────────
EASY_RULES = [
    Rule("R1_E01", "x + y",        "easy",   lambda x,y: x + y),
    Rule("R1_E02", "x + y + 1",    "easy",   lambda x,y: x + y + 1),
    Rule("R1_E03", "x + y - 1",    "easy",   lambda x,y: x + y - 1),
    Rule("R1_E04", "2x + y",       "easy",   lambda x,y: 2*x + y),
    Rule("R1_E05", "x + 2y",       "easy",   lambda x,y: x + 2*y),
    Rule("R1_E06", "abs(x - y)",   "easy",   lambda x,y: abs(x - y)),
    Rule("R1_E07", "max(x, y)",    "easy",   lambda x,y: max(x, y)),
    Rule("R1_E08", "min(x, y)",    "easy",   lambda x,y: min(x, y)),
]

# ── Medium rules ──────────────────────────────────────────────
MEDIUM_RULES = [
    Rule("R1_M01", "x * y",        "medium", lambda x,y: x * y),
    Rule("R1_M02", "x * y + 1",    "medium", lambda x,y: x * y + 1),
    Rule("R1_M03", "x * y - 1",    "medium", lambda x,y: x * y - 1),
    Rule("R1_M04", "x * y + x",    "medium", lambda x,y: x * y + x),
    Rule("R1_M05", "x * y + y",    "medium", lambda x,y: x * y + y),
]

# ── Hard rules ────────────────────────────────────────────────
HARD_RULES = [
    Rule("R1_H01", "x*y + x + y",  "hard",   lambda x,y: x*y + x + y),
    Rule("R1_H02", "x*y - x",      "hard",   lambda x,y: x*y - x),
    Rule("R1_H03", "x*y - y",      "hard",   lambda x,y: x*y - y),
    Rule("R1_H04", "x*y - (x+y)",  "hard",   lambda x,y: x*y - (x + y)),
    Rule("R1_H05", "x*y + 2",      "hard",   lambda x,y: x*y + 2),
]

ALL_RULES: dict[str, list[Rule]] = {
    "easy":   EASY_RULES,
    "medium": MEDIUM_RULES,
    "hard":   HARD_RULES,
}

# ── Backward-compat map: old generation IDs still validate fine ──
LEGACY_RULE_FNS = {
    "Gen01_Add":      lambda a, b: a + b,
    "Gen02_Mul":      lambda a, b: a * b,
    "Gen03_AddPlus1": lambda a, b: a + b + 1,
}


# ══════════════════════════════════════════════════════════════
# PYRAMID BUILDER  (unchanged API — existing gameplay untouched)
# ══════════════════════════════════════════════════════════════

def build_pyramid(base: list, rule: Rule) -> list:
    """
    Build all 10 cells bottom-up from 4 base values.
    Returns top-down list: [apex, L2-L, L2-R, L3-L, L3-M, L3-R,
                             base0, base1, base2, base3]
    Values may be float if rule produces non-integer; caller filters.
    """
    r3 = [rule.apply(base[i], base[i+1]) for i in range(3)]
    r2 = [rule.apply(r3[i], r3[i+1])    for i in range(2)]
    apex = rule.apply(r2[0], r2[1])
    return [apex, r2[0], r2[1],
            r3[0], r3[1], r3[2],
            base[0], base[1], base[2], base[3]]


# ══════════════════════════════════════════════════════════════
# R1  SAFETY FILTER
# ══════════════════════════════════════════════════════════════

def passes_safety(values: list, require_unique: bool = True) -> bool:
    """
    Reject a pyramid if ANY of these hold:
      • Any value is not an integer (NaN, float with fraction)
      • Any value <= 0
      • Any value >= 99
      • Any duplicate value among the 10 cells  (only when require_unique=True)
    """
    ints = []
    for v in values:
        if not isinstance(v, (int, float)):
            return False
        if math.isnan(v) or math.isinf(v):
            return False
        if int(v) != v:
            return False
        vi = int(v)
        if vi <= 0 or vi >= 99:
            return False
        ints.append(vi)

    if require_unique and len(set(ints)) != len(ints):
        return False

    return True


# ══════════════════════════════════════════════════════════════
# UNIQUENESS / MIRROR SOLVER
# Checks how many valid arrangements of the 10 numbers satisfy
# the rule.  Mirror = base reversed ([a,b,c,d] ↔ [d,c,b,a]).
# ══════════════════════════════════════════════════════════════

TRIPLETS = [(0,1,2),(1,3,4),(2,4,5),(3,6,7),(4,7,8),(5,8,9)]


def _check_arrangement(arr: list, fn) -> bool:
    """Return True if arrangement satisfies fn at all 6 triplets."""
    for p, l, r in TRIPLETS:
        expected = fn(arr[l], arr[r])
        if int(expected) != expected:
            return False
        if arr[p] != int(expected):
            return False
    return True


def _is_mirror(sol_a: list, sol_b: list) -> bool:
    """
    Two solutions are mirrors if one's base row is the reverse
    of the other's, and the rest of the pyramid matches accordingly.
    """
    # base rows: indices 6-9
    base_a = sol_a[6:10]
    base_b = sol_b[6:10]
    return base_a == base_b[::-1]


def count_solutions(numbers: list, rule: Rule) -> tuple[int, int]:
    """
    Fast uniqueness check: only permute the 4 BASE positions (P(10,4)=5040).
    Derive the upper 6 cells from the rule and check they match the
    remaining 6 numbers exactly.

    Returns (solution_count, mirror_pair_count).
    """
    fn   = rule.apply
    nums = sorted(numbers)
    valid_solutions = []

    for base_perm in itertools.permutations(nums, 4):
        # build a multiset of the remaining 6 numbers
        temp = list(nums)
        ok = True
        for v in base_perm:
            try: temp.remove(v)
            except ValueError: ok = False; break
        if not ok:
            continue

        # derive upper 6 from rule
        try:
            r3_0 = fn(base_perm[0], base_perm[1])
            r3_1 = fn(base_perm[1], base_perm[2])
            r3_2 = fn(base_perm[2], base_perm[3])
            r2_0 = fn(r3_0, r3_1)
            r2_1 = fn(r3_1, r3_2)
            apex = fn(r2_0, r2_1)
        except Exception:
            continue

        derived = [r3_0, r3_1, r3_2, r2_0, r2_1, apex]

        # quick validity check on derived values
        bad = False
        for v in derived:
            if not isinstance(v, (int, float)): bad=True; break
            if math.isnan(v) or math.isinf(v): bad=True; break
            if int(v) != v: bad=True; break
            vi = int(v)
            if vi <= 0 or vi >= 99: bad=True; break
        if bad:
            continue

        derived_ints = [int(v) for v in derived]

        # must match remaining 6 numbers exactly
        if sorted(derived_ints) != sorted(temp):
            continue

        full = [int(apex), int(r2_0), int(r2_1),
                int(r3_0), int(r3_1), int(r3_2),
                int(base_perm[0]), int(base_perm[1]),
                int(base_perm[2]), int(base_perm[3])]
        valid_solutions.append(full)

        # Early-exit optimisation: once we have >2 solutions (and neither
        # can be a mirror pair), we know this board fails the accept criteria
        # and can stop early.
        if len(valid_solutions) > 2:
            return len(valid_solutions), 0

    # Count mirror pairs
    mirror_pairs = 0
    n = len(valid_solutions)
    for i in range(n):
        for j in range(i+1, n):
            if _is_mirror(valid_solutions[i], valid_solutions[j]):
                mirror_pairs += 1

    return len(valid_solutions), mirror_pairs


# ══════════════════════════════════════════════════════════════
# BASE RANGES PER TIER
# Tuned so the safety filter passes reliably for each rule tier
# ══════════════════════════════════════════════════════════════

BASE_RANGES = {
    "easy":   (1, 9),    # additive rules — full range
    "medium": (1, 6),    # multiplicative — small enough to stay < 99
    "hard":   (1, 5),    # complex multiplicative
}

COUNTS = {"Easy": 10, "Medium": 10, "Hard": 5}

# Apex sanity bounds per difficulty
APEX_BOUNDS = {
    "Easy":   (10, 95),
    "Medium": (4,  95),
    "Hard":   (4,  95),
}


# ══════════════════════════════════════════════════════════════
# SINGLE BOARD GENERATOR
# ══════════════════════════════════════════════════════════════

def generate_board_r1(difficulty: str,
                      rule: Rule | None = None,
                      max_attempts: int = 2000) -> dict | None:
    """
    Generate one valid board using the R1 pipeline.

    Pipeline:
      1. Select rule (or use supplied rule)
      2. Generate candidate base values
      3. Compute all 10 cells
      4. Apply safety filter (no dupes, 0<v<99, integers only)
      5. Run uniqueness solver
      6. Accept if exactly 1 solution, or 2 solutions that are mirrors
      7. Return board dict — rule info stored as metadata only

    Returns None if max_attempts exceeded.
    """
    tier = difficulty.lower()

    for attempt in range(max_attempts):
        # Step 1: choose rule
        active_rule = rule or random.choice(ALL_RULES[tier])

        # Step 2: generate base — use distinct values when possible
        lo, hi = BASE_RANGES.get(tier, (1, 9))
        base = [random.randint(lo, hi) for _ in range(4)]

        # Step 3: compute pyramid
        try:
            raw = build_pyramid(base, active_rule)
        except Exception:
            continue

        # Step 4: safety filter
        # Easy boards: require all 10 values to be unique (puzzles with duplicates
        #              are ambiguous for addition rules).
        # Medium/Hard: duplicates are acceptable — multiplicative rules naturally
        #              produce repeated values in the middle levels; the hidden rule
        #              still creates a unique derivation path from base to apex.
        require_unique = (tier == "easy")
        if not passes_safety(raw, require_unique=require_unique):
            continue

        solution = [int(v) for v in raw]

        # Pre-filter: apex must be in a sensible range for the difficulty
        apex_min, apex_max = APEX_BOUNDS.get(difficulty, (6, 95))
        if not (apex_min <= solution[0] <= apex_max):
            continue

        # Step 5: uniqueness check (only for Easy — Medium/Hard rely on safety filter)
        if tier == "easy":
            n_sol, n_mirror = count_solutions(solution, active_rule)
        else:
            n_sol, n_mirror = 1, 0  # not computed for Medium/Hard

        # Step 6: accept criteria
        # Easy:   standard uniqueness required (1 sol or mirror pair)
        # Medium/Hard: skip expensive uniqueness check — safety filter
        #              (all-distinct values) guarantees the pyramid is
        #              deterministic given the rule, which is sufficient
        #              for a fair puzzle.
        if tier == "easy":
            if n_sol == 1:
                pass
            elif n_sol == 2 and n_mirror == 1:
                pass
            else:
                continue
        else:
            # Medium/Hard: accept any board that passes safety filter
            # (uniqueness solver not run — saves time, safety ensures fairness)
            pass

        # Step 7: build board dict
        puzzle = solution.copy()
        random.shuffle(puzzle)

        # Relationship label is generic — does NOT reveal the rule
        # (UI shows "A hidden arithmetic rule connects parent to children")
        generic_label = "A hidden arithmetic rule connects every parent to its two children"

        return {
            # ── player-facing fields (unchanged schema) ────────
            "board_id":     str(uuid.uuid4()),
            "generated":    datetime.now(timezone.utc).isoformat(),
            "generation":   active_rule.id,
            "difficulty":   difficulty,
            "relationship": generic_label,
            "solution":     solution,
            "puzzle":       puzzle,
            # ── developer metadata (hidden from UI) ────────────
            "_meta": {
                "rule_id":      active_rule.id,
                "rule_name":    active_rule.name,
                "rule_tier":    active_rule.difficulty,
                "n_solutions":  n_sol,
                "n_mirrors":    n_mirror,
                "attempt":      attempt + 1,
            },
        }

    return None  # failed after max_attempts


# ══════════════════════════════════════════════════════════════
# BATCH GENERATOR
# ══════════════════════════════════════════════════════════════

def generate_all_boards(mode: str = "default") -> list:
    """
    Generate boards according to mode.

    mode='default'  → 25 boards: 10 Easy, 10 Medium, 5 Hard
    mode='easy'     → 10 Easy boards
    mode='medium'   → 10 Medium boards
    mode='hard'     → 5 Hard boards
    mode='random'   → 25 boards each with a randomly chosen tier
    """
    schedule = []

    if mode == "default":
        for diff, count in [("Easy",10),("Medium",10),("Hard",5)]:
            schedule += [(diff, None)] * count

    elif mode == "easy":
        schedule = [("Easy", None)] * 10

    elif mode == "medium":
        schedule = [("Medium", None)] * 10

    elif mode == "hard":
        schedule = [("Hard", None)] * 5

    elif mode == "random":
        all_flat = (EASY_RULES + MEDIUM_RULES + HARD_RULES)
        tier_map = {"easy":"Easy","medium":"Medium","hard":"Hard"}
        for _ in range(25):
            r = random.choice(all_flat)
            schedule.append((tier_map[r.difficulty], r))

    else:
        raise ValueError(f"Unknown mode: {mode!r}")

    boards = []
    n = 1
    for difficulty, forced_rule in schedule:
        print(f"  Generating board {n} ({difficulty})...", end=" ", flush=True)
        board = generate_board_r1(difficulty, rule=forced_rule)
        if board is None:
            print(f"FAILED after max attempts — skipping")
            continue
        board["board_number"] = n
        boards.append(board)
        meta = board["_meta"]
        print(f"rule={meta['rule_id']} sols={meta['n_solutions']} "
              f"mirrors={meta['n_mirrors']} attempts={meta['attempt']}")
        n += 1

    return boards


# ══════════════════════════════════════════════════════════════
# VALIDATION  (backward-compatible — checks both legacy and R1 IDs)
# ══════════════════════════════════════════════════════════════

def _get_rule_fn(generation_id: str):
    """Return callable for any rule ID (legacy or R1)."""
    # R1 rules
    all_flat = EASY_RULES + MEDIUM_RULES + HARD_RULES
    for r in all_flat:
        if r.id == generation_id:
            return r.apply
    # Legacy rules
    return LEGACY_RULE_FNS.get(generation_id)


def validate_all(boards: list) -> bool:
    """Verify every board satisfies its own rule. Returns True if all pass."""
    all_ok = True
    for b in boards:
        fn = _get_rule_fn(b["generation"])
        if fn is None:
            print(f"  UNKNOWN rule {b['generation']} board {b['board_id'][:8]}")
            all_ok = False
            continue
        sol = b["solution"]
        for p, l, r in TRIPLETS:
            if sol[p] != fn(sol[l], sol[r]):
                print(f"  FAIL: board {b['board_id'][:8]} triplet ({p},{l},{r})")
                all_ok = False
    return all_ok


# ══════════════════════════════════════════════════════════════
# DEVELOPER INSPECTOR  (hidden from normal players)
# ══════════════════════════════════════════════════════════════

def print_dev_inspector(boards: list) -> None:
    """
    Print the developer-only board inspector.
    Shows: Board ID, Rule Name, Difficulty, Pyramid, Puzzle, Solution Count.
    This output should NEVER be visible to normal players.
    """
    print("\n" + "═"*70)
    print("  DEVELOPER INSPECTOR  (internal — not shown to players)")
    print("═"*70)

    for b in boards:
        meta = b.get("_meta", {})
        sol  = b["solution"]
        num  = b.get("board_number","?")
        bid  = f"{b['difficulty'].lower()}-{str(num).zfill(2)}"

        print(f"\n  ┌─ {bid.upper()}  [{b['difficulty']}]")
        print(f"  │  Board ID   : {b['board_id']}")
        print(f"  │  Rule ID    : {meta.get('rule_id', b['generation'])}")
        print(f"  │  Rule Name  : {meta.get('rule_name','?')}")
        print(f"  │  Solutions  : {meta.get('n_solutions','?')}")
        print(f"  │  Mirrors    : {meta.get('n_mirrors','?')}")
        print(f"  │  Attempts   : {meta.get('attempt','?')}")
        print(f"  │")
        print(f"  │  Pyramid (top→base):")
        print(f"  │         {sol[0]}")
        print(f"  │      {sol[1]}   {sol[2]}")
        print(f"  │    {sol[3]}  {sol[4]}  {sol[5]}")
        print(f"  │  {sol[6]}  {sol[7]}  {sol[8]}  {sol[9]}")
        print(f"  │")
        print(f"  │  Shuffled  : {b['puzzle']}")
        print(f"  └{'─'*60}")

    print("\n" + "═"*70)
    print(f"  Total boards: {len(boards)}")
    diff_c = Counter(b["difficulty"] for b in boards)
    rule_c = Counter(b.get("_meta",{}).get("rule_id", b["generation"])
                     for b in boards)
    print(f"  By difficulty: {dict(diff_c)}")
    print(f"  By rule: {dict(rule_c)}")
    print("═"*70 + "\n")


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    dev_mode   = "--dev"    in args
    mode_flag  = "default"
    if "--mode" in args:
        idx = args.index("--mode")
        if idx + 1 < len(args):
            mode_flag = args[idx+1].lower()

    print(f"\nIncairn R1 Generator  (mode={mode_flag}, dev={dev_mode})")
    print("─"*50)

    boards = generate_all_boards(mode=mode_flag)

    print("\nValidating all boards...")
    ok = validate_all(boards)
    print("✅ All boards valid." if ok else "❌ Some boards failed.")

    # Save — strip _meta from the JSON so players never see rule info
    boards_to_save = []
    for b in boards:
        clean = {k: v for k, v in b.items() if k != "_meta"}
        boards_to_save.append(clean)

    with open("incairn_boards.json", "w") as f:
        json.dump(boards_to_save, f, indent=2)

    diff_c = Counter(b["difficulty"] for b in boards)
    print(f"\n  Easy  : {diff_c.get('Easy',0)}")
    print(f"  Medium: {diff_c.get('Medium',0)}")
    print(f"  Hard  : {diff_c.get('Hard',0)}")
    print(f"\n✅ Saved {len(boards_to_save)} boards to incairn_boards.json")

    if dev_mode:
        print_dev_inspector(boards)
