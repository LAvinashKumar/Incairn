"""
review.py — Private Creator Review Tool
========================================
Run this locally in your terminal to walk through every board
grouped by generation logic. No Streamlit, no browser, no one
else can see or use this.

Usage:
    python review.py                  # review all generations
    python review.py Gen01_Add        # review one specific logic
    python review.py Gen01_Add --auto # auto-walk, no key presses

What it does for each board:
  • Prints the full solution pyramid visually
  • Verifies every parent-child triplet against the rule
  • Highlights any broken cells with ✗ in red
  • Shows the shuffled puzzle numbers
  • Lets you mark boards as OK / broken / needs-regen
  • Saves your review notes to creator_review.json
  • Prints a final summary report
"""

import json
import sys
import os
from datetime import datetime, timezone
from collections import defaultdict, Counter

# ── Terminal colours (works on macOS/Linux) ──────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

BOARDS_FILE = "incairn_boards.json"
REVIEW_FILE = "creator_review.json"

# ── Rule functions ────────────────────────────────────────────
RULE_FNS = {
    "Gen01_Add":      lambda a, b: a + b,
    "Gen02_Mul":      lambda a, b: a * b,
    "Gen03_AddPlus1": lambda a, b: a + b + 1,
}

RULE_DESCRIPTIONS = {
    "Gen01_Add":      "Parent = Left + Right          (Easy/Medium)",
    "Gen02_Mul":      "Parent = Left × Right          (Hard)",
    "Gen03_AddPlus1": "Parent = Left + Right + 1      (Medium/Hard)",
}

# Pyramid parent→(left, right) relationships
TRIPLETS = [
    (0, 1, 2),   # apex   ← L2-left,  L2-right
    (1, 3, 4),   # L2-L   ← L3-left,  L3-mid
    (2, 4, 5),   # L2-R   ← L3-mid,   L3-right
    (3, 6, 7),   # L3-L   ← base[0],  base[1]
    (4, 7, 8),   # L3-M   ← base[1],  base[2]
    (5, 8, 9),   # L3-R   ← base[2],  base[3]
]


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def load_boards() -> list[dict]:
    with open(BOARDS_FILE) as f:
        return json.load(f)


def load_reviews() -> dict:
    """Load existing creator review notes keyed by board_id."""
    if not os.path.exists(REVIEW_FILE):
        return {}
    with open(REVIEW_FILE) as f:
        return json.load(f)


def save_reviews(reviews: dict) -> None:
    with open(REVIEW_FILE, "w") as f:
        json.dump(reviews, f, indent=2)


def validate_board(board: dict) -> tuple[bool, list[str]]:
    """
    Check every triplet in the board's solution against its rule.
    Returns (all_ok, list_of_violation_strings).
    """
    fn  = RULE_FNS.get(board["generation"])
    sol = board["solution"]
    violations = []

    if fn is None:
        return False, [f"Unknown generation: {board['generation']}"]

    for p, l, r in TRIPLETS:
        expected = fn(sol[l], sol[r])
        if sol[p] != expected:
            violations.append(
                f"  cell[{p}]={sol[p]}  ←  "
                f"cell[{l}]({sol[l]}) ⊕ cell[{r}]({sol[r]}) = {expected}  ✗ MISMATCH"
            )

    return len(violations) == 0, violations


def print_pyramid(sol: list[int], violations: list[str]) -> None:
    """
    Print a visual pyramid. Cells involved in a violation are
    highlighted in red, correct ones in green.
    """
    # Find which cell indices are broken
    bad_indices = set()
    for v in violations:
        # parse out the cell index from the violation string e.g. "cell[0]=..."
        import re
        for match in re.finditer(r"cell\[(\d+)\]", v):
            bad_indices.add(int(match.group(1)))

    def fmt(idx: int) -> str:
        val = str(sol[idx]).rjust(4)
        if idx in bad_indices:
            return f"{RED}{BOLD}{val}{RESET}"
        return f"{GREEN}{val}{RESET}"

    print()
    print(f"         {fmt(0)}")
    print(f"      {fmt(1)}  {fmt(2)}")
    print(f"    {fmt(3)}  {fmt(4)}  {fmt(5)}")
    print(f"  {fmt(6)}  {fmt(7)}  {fmt(8)}  {fmt(9)}")
    print()


def print_separator(char="─", width=60):
    print(f"{DIM}{char * width}{RESET}")


def print_header(text: str):
    print()
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}")


# ─────────────────────────────────────────────────────────────
# CORE REVIEW LOOP
# ─────────────────────────────────────────────────────────────

def review_generation(gen_id: str, boards: list[dict],
                      reviews: dict, auto: bool = False) -> None:
    """
    Walk through all boards for a single generation logic,
    one at a time. For each board the creator can mark it
    OK, broken, or needs regeneration, and leave a note.
    """
    gen_boards = [b for b in boards if b["generation"] == gen_id]

    print_header(f"Generation Logic: {gen_id}")
    print(f"  Rule  : {BOLD}{RULE_DESCRIPTIONS.get(gen_id, gen_id)}{RESET}")
    print(f"  Boards: {len(gen_boards)}")
    print()

    # Quick validity pre-scan
    all_valid   = [b for b in gen_boards if validate_board(b)[0]]
    all_invalid = [b for b in gen_boards if not validate_board(b)[0]]
    print(f"  Pre-scan → {GREEN}{len(all_valid)} valid{RESET}  "
          f"{RED}{len(all_invalid)} invalid{RESET}")
    print_separator()

    for i, board in enumerate(gen_boards, 1):
        ok, violations = validate_board(board)
        already_reviewed = board["board_id"] in reviews

        print()
        print(f"{BOLD}Board {i}/{len(gen_boards)}{RESET}  "
              f"ID: {CYAN}{board['board_id'][:16]}…{RESET}  "
              f"Difficulty: {_diff_fmt(board['difficulty'])}")
        print(f"Rule applied: {board['relationship']}")

        # ── Validation status ──
        if ok:
            print(f"  Validation : {GREEN}✅  All {len(TRIPLETS)} triplets PASS{RESET}")
        else:
            print(f"  Validation : {RED}❌  {len(violations)} triplet(s) FAIL{RESET}")
            for v in violations:
                print(f"  {RED}{v}{RESET}")

        # ── Visual pyramid ──
        print_pyramid(board["solution"], violations)

        # ── Puzzle chips ──
        chips = "  ".join(str(n).rjust(3) for n in board["puzzle"])
        print(f"  Puzzle (shuffled) : {YELLOW}{chips}{RESET}")

        # ── Full triplet table ──
        fn = RULE_FNS[gen_id]
        sol = board["solution"]
        print(f"\n  {BOLD}Triplet check:{RESET}")
        for p, l, r in TRIPLETS:
            expected = fn(sol[l], sol[r])
            match    = sol[p] == expected
            symbol   = f"{GREEN}✓{RESET}" if match else f"{RED}✗{RESET}"
            print(f"    {symbol}  cell[{p}]={str(sol[p]).rjust(4)}  "
                  f"←  [{l}]({sol[l]}) ⊕ [{r}]({sol[r]}) = {expected}")

        # ── Previous review note ──
        if already_reviewed:
            rev = reviews[board["board_id"]]
            print(f"\n  {DIM}Previously marked: "
                  f"[{rev['status'].upper()}] {rev.get('note','')} "
                  f"({rev['timestamp'][:10]}){RESET}")

        # ── Creator input ──
        if auto:
            # Auto mode: just record validity, no prompts
            if not already_reviewed:
                reviews[board["board_id"]] = {
                    "board_id":   board["board_id"],
                    "generation": gen_id,
                    "difficulty": board["difficulty"],
                    "status":     "ok" if ok else "broken",
                    "note":       "auto-reviewed",
                    "timestamp":  datetime.now(timezone.utc).isoformat(),
                }
            print_separator()
            continue

        print()
        print(f"  {BOLD}Your verdict:{RESET}")
        print(f"    [o] OK — board is good")
        print(f"    [b] Broken — this board has a logic error")
        print(f"    [r] Needs regen — rule is ok but puzzle feels wrong")
        print(f"    [s] Skip — review later")
        print(f"    [q] Quit this generation")

        while True:
            try:
                choice = input(f"\n  Enter choice (o/b/r/s/q): ").strip().lower()
            except EOFError:
                choice = "s"

            if choice in ("o", "b", "r", "s", "q"):
                break
            print("  Please enter o, b, r, s, or q.")

        if choice == "q":
            print(f"\n{YELLOW}  Stopped reviewing {gen_id} early.{RESET}")
            break

        if choice == "s":
            print_separator()
            continue

        # Get optional note
        try:
            note = input("  Optional note (press Enter to skip): ").strip()
        except EOFError:
            note = ""

        status_map = {"o": "ok", "b": "broken", "r": "needs_regen"}
        reviews[board["board_id"]] = {
            "board_id":   board["board_id"],
            "generation": gen_id,
            "difficulty": board["difficulty"],
            "status":     status_map[choice],
            "note":       note,
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }
        save_reviews(reviews)   # save after every board so nothing is lost

        print_separator()


def _diff_fmt(d: str) -> str:
    colors = {"Easy": GREEN, "Medium": YELLOW, "Hard": RED}
    return f"{colors.get(d, '')}{BOLD}{d}{RESET}"


# ─────────────────────────────────────────────────────────────
# SUMMARY REPORT
# ─────────────────────────────────────────────────────────────

def print_summary(boards: list[dict], reviews: dict) -> None:
    print_header("Creator Review Summary")

    all_gens = sorted(set(b["generation"] for b in boards))

    total_ok      = sum(1 for r in reviews.values() if r["status"] == "ok")
    total_broken  = sum(1 for r in reviews.values() if r["status"] == "broken")
    total_regen   = sum(1 for r in reviews.values() if r["status"] == "needs_regen")
    total_reviewed = len(reviews)
    total_boards   = len(boards)

    print(f"\n  Total boards    : {total_boards}")
    print(f"  Reviewed so far : {total_reviewed} / {total_boards}")
    print(f"  ✅ OK           : {GREEN}{total_ok}{RESET}")
    print(f"  ❌ Broken       : {RED}{total_broken}{RESET}")
    print(f"  🔄 Needs regen  : {YELLOW}{total_regen}{RESET}")

    print(f"\n  {BOLD}By Generation Logic:{RESET}")
    for gen in all_gens:
        gen_boards  = [b for b in boards if b["generation"] == gen]
        valid_count = sum(1 for b in gen_boards if validate_board(b)[0])
        rev_for_gen = [r for r in reviews.values() if r["generation"] == gen]
        ok_count    = sum(1 for r in rev_for_gen if r["status"] == "ok")
        bad_count   = sum(1 for r in rev_for_gen if r["status"] == "broken")

        print(f"\n  ┌─ {CYAN}{BOLD}{gen}{RESET}")
        print(f"  │  Boards          : {len(gen_boards)}")
        print(f"  │  Auto-valid (code): {GREEN}{valid_count}{RESET} / {len(gen_boards)}")
        print(f"  │  Creator marked OK: {GREEN}{ok_count}{RESET}")
        print(f"  │  Creator flagged  : {RED}{bad_count}{RESET}")

        # Difficulty breakdown within this gen
        diff_c = Counter(b["difficulty"] for b in gen_boards)
        for d, cnt in sorted(diff_c.items()):
            print(f"  │  {_diff_fmt(d)}: {cnt}")

    # List broken / regen boards
    flagged = [r for r in reviews.values() if r["status"] in ("broken", "needs_regen")]
    if flagged:
        print(f"\n  {RED}{BOLD}Flagged boards:{RESET}")
        for r in flagged:
            print(f"    [{r['status'].upper()}] {r['board_id'][:16]}… "
                  f"({r['generation']}, {r['difficulty']}) — {r.get('note','')}")

    # Unreviewed boards
    reviewed_ids = set(reviews.keys())
    unreviewed   = [b for b in boards if b["board_id"] not in reviewed_ids]
    if unreviewed:
        print(f"\n  {YELLOW}Unreviewed boards ({len(unreviewed)}):{RESET}")
        for b in unreviewed:
            print(f"    {b['board_id'][:16]}… ({b['generation']}, {b['difficulty']})")

    print()
    print_separator("═")


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

def main():
    # Parse simple CLI args
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    auto_mode = "--auto" in flags

    boards  = load_boards()
    reviews = load_reviews()

    all_gens = sorted(set(b["generation"] for b in boards))

    # Determine which generations to review
    if args:
        target_gen = args[0]
        if target_gen not in all_gens:
            print(f"{RED}Unknown generation '{target_gen}'. "
                  f"Available: {', '.join(all_gens)}{RESET}")
            sys.exit(1)
        gens_to_review = [target_gen]
    else:
        gens_to_review = all_gens

    # Welcome banner
    print()
    print(f"{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  INCAIRN — Creator Review Tool{RESET}")
    print(f"{BOLD}{'═'*60}{RESET}")
    print(f"  Boards loaded : {len(boards)}")
    print(f"  Generations   : {', '.join(all_gens)}")
    print(f"  Reviewing     : {', '.join(gens_to_review)}")
    print(f"  Mode          : {'AUTO (no prompts)' if auto_mode else 'INTERACTIVE'}")
    print(f"{'═'*60}")

    if not auto_mode and len(gens_to_review) > 1:
        print(f"\n  {DIM}Tip: run   python review.py Gen01_Add   to review one logic only{RESET}")
        print(f"  {DIM}     run   python review.py --auto       to skip all prompts{RESET}")

    # Review each generation
    for gen in gens_to_review:
        review_generation(gen, boards, reviews, auto=auto_mode)

    # Final summary
    print_summary(boards, reviews)
    print(f"  Review data saved to: {CYAN}{REVIEW_FILE}{RESET}\n")


if __name__ == "__main__":
    main()
