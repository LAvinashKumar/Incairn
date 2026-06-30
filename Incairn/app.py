"""
app.py — Incairn  (Single-component full-page UI)
===================================================
The entire game UI lives in one components.html call.
JavaScript handles all screen navigation (show/hide divs).
Python only injects board data and handles feedback saves.

Run:  streamlit run app.py
"""
import json, os, hashlib, random, time, base64
from pathlib import Path

BASE_DIR = Path(__file__).parent
from datetime import date, datetime, timezone
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Incairn · Daily Cairn",
    page_icon="🗿",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Strip ALL Streamlit chrome — the HTML component IS the entire UI
st.markdown("""
<style>
  #MainMenu,footer,header{visibility:hidden}
  .block-container{
    padding:0!important;max-width:100%!important;
    margin:0!important;
  }
  section[data-testid="stSidebar"]{display:none}
  iframe{border:none!important;display:block!important}
  div[data-testid="stVerticalBlock"]{gap:0!important}
</style>
""", unsafe_allow_html=True)

# ── Board data ────────────────────────────────────────────────
@st.cache_data
def load_boards():
    with open(BASE_DIR / "incairn_boards.json") as f:
        return json.load(f)

def save_feedback(entry):
    path = BASE_DIR / "feedback.json"
    data = []
    if os.path.exists(path):
        with open(path) as f:
            try: data = json.load(f)
            except: data = []
    data.append(entry)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_daily_num(boards):
    seed = int(hashlib.md5(date.today().isoformat().encode()).hexdigest(), 16)
    return (seed % len(boards)) + 1

def today_label():
    return date.today().strftime("%A, %d %B %Y").upper()

boards = load_boards()
daily_num = get_daily_num(boards)

# Prepare slim board objects for JS injection
def slim(b):
    num = b.get("board_number", 0)
    # R2 boards use board_id as a readable slug (e.g. "R2-E01-0048")
    # R1 boards use a UUID + a separate board_number field
    bid = b["board_id"] if b["board_id"].startswith("R2-") else \
          f"{b['difficulty'].lower()}-{str(num).zfill(2)}"
    return {
        "id":   b["board_id"],
        "num":  num,
        "bid":  bid,
        "diff": b["difficulty"],
        "gen":  b.get("generation", ""),
        "rel":  b.get("relationship", ""),
        "sol":  b["solution"],
        "puz":  b["puzzle"],
    }

boards_js = json.dumps([slim(b) for b in boards])
today_js  = today_label()
daily_js  = daily_num

# ── Maze logo ─────────────────────────────────────────────────
_MAZE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
<rect width="200" height="200" fill="#1a1714" rx="10"/>
<rect x="6" y="6" width="188" height="188" fill="none" stroke="#c9a84c" stroke-width="6"/>
<g fill="none" stroke="#c9a84c" stroke-width="5" stroke-linecap="square">
<polyline points="20,6 20,40 60,40 60,20 100,20 100,6"/>
<polyline points="140,6 140,20 160,20 160,40 120,40 120,60 140,60 140,80 100,80 100,60 80,60 80,40"/>
<polyline points="180,20 180,60 160,60 160,100 180,100"/>
<polyline points="6,60 40,60 40,80 20,80 20,100 60,100 60,80 80,80"/>
<polyline points="20,120 20,140 60,140 60,120 80,120 80,100 100,100 100,120 120,120 120,100 140,100 140,120 180,120 180,140"/>
<polyline points="40,140 40,160 60,160 60,140"/>
<polyline points="80,140 80,160 100,160 100,140"/>
<polyline points="100,160 100,180 120,180 120,160 140,160 140,180 160,180 160,160 180,160 180,194"/>
<polyline points="20,160 20,180 60,180 60,194"/>
<line x1="40" y1="6" x2="40" y2="40"/>
<line x1="60" y1="40" x2="60" y2="60"/>
<line x1="100" y1="80" x2="100" y2="100"/>
<line x1="120" y1="40" x2="120" y2="80"/>
<line x1="140" y1="60" x2="140" y2="100"/>
<line x1="40" y1="100" x2="40" y2="140"/>
<line x1="60" y1="100" x2="60" y2="120"/>
<line x1="80" y1="160" x2="80" y2="194"/>
</g></svg>"""
LOGO_B64 = base64.b64encode(_MAZE.encode()).decode()
LOGO_URL  = f"data:image/svg+xml;base64,{LOGO_B64}"

# ── Feedback form state ───────────────────────────────────────
for k, v in {
    "fb_pending": False,
    "fb_data": {},
    "show_fb_form": False,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════
# THE ENTIRE GAME — one HTML component, JS-driven screens
# ══════════════════════════════════════════════════════════════
GAME_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
/* ════════════════════════════════════════════
   GLOBAL RESET & TOKENS
════════════════════════════════════════════ */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:      #0e0c09;
  --bg2:     #181410;
  --bg3:     #221d16;
  --bg4:     #2c261e;
  --border:  #3a3228;
  --border2: #524840;
  --border3: #6b5a48;
  --gold:    #d4a843;
  --goldD:   #a07830;
  --stone:   #8b7355;
  --stoneL:  #b09070;
  --cream:   #ece4d6;
  --sub:     #9a8e7a;
  --muted:   #5c5040;
  --green:   #4a7040;
  --greenL:  #86c97a;
  --amber:   #c08820;
  --wrong:   #3a2e24;
  --wrongB:  #7a4030;
  --r:       16px;  /* border-radius default */
}}
html,body{{
  background:var(--bg);
  color:var(--cream);
  font-family:'Georgia','Times New Roman',serif;
  min-height:100vh;
  overflow-x:hidden;
}}

/* ════════════════════════════════════════════
   SCREEN SYSTEM — show/hide
════════════════════════════════════════════ */
.screen{{display:none;flex-direction:column;align-items:center;
  min-height:100vh;padding:0;animation:fadeIn .25s ease}}
.screen.active{{display:flex}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}

/* ════════════════════════════════════════════
   HOME SCREEN
════════════════════════════════════════════ */
#home{{
  justify-content:center;
  padding:32px 20px 40px;
  gap:18px;
  text-align:center;
  background:
    radial-gradient(ellipse at 50% 0%, #2a2010 0%, transparent 65%),
    var(--bg);
}}
.logo-ring{{
  width:72px;height:72px;border-radius:50%;
  border:1.5px solid var(--border2);
  display:flex;align-items:center;justify-content:center;
  background:var(--bg2);
  overflow:hidden;
}}
.logo-ring img{{width:54px;height:54px;border-radius:6px}}
.h-pill-row{{display:flex;gap:8px;justify-content:center;align-items:center}}
.h-pill{{
  font-size:.6rem;letter-spacing:.18em;text-transform:uppercase;
  padding:4px 14px;border-radius:20px;border:1px solid var(--border2);
  color:var(--sub);background:var(--bg2)
}}
.h-pill.gold{{color:var(--gold);border-color:var(--goldD)}}
.game-title{{
  font-size:clamp(2rem,8vw,3.5rem);
  letter-spacing:.35em;text-transform:uppercase;
  color:var(--cream);line-height:1;
  text-shadow:0 2px 20px rgba(212,168,67,.15)
}}
.game-sub{{
  font-size:.85rem;color:var(--sub);
  font-style:italic;letter-spacing:.04em
}}
.home-divider{{
  width:100%;max-width:360px;height:1px;
  background:linear-gradient(90deg,transparent,var(--border2),transparent)
}}
/* Daily card */
.daily-card{{
  width:100%;max-width:400px;
  background:var(--bg2);
  border:1px solid var(--border2);
  border-radius:var(--r);
  padding:20px 24px;
  text-align:left;
  position:relative;
  overflow:hidden;
}}
.daily-card::before{{
  content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse at 80% 20%, #3a2e0033, transparent 60%);
  pointer-events:none
}}
.dc-eyebrow{{
  font-size:.55rem;letter-spacing:.2em;text-transform:uppercase;
  color:var(--stone);margin-bottom:8px
}}
.dc-date{{font-size:.72rem;color:var(--sub);margin-bottom:10px}}
.dc-diff{{
  display:inline-block;padding:3px 12px;border-radius:20px;
  font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;
  margin-bottom:12px
}}
.dc-desc{{font-size:.78rem;color:var(--sub);font-style:italic;line-height:1.65}}
/* Stats row */
.stats-row{{
  display:flex;gap:8px;justify-content:center;
  width:100%;max-width:400px
}}
.stat-box{{
  flex:1;background:var(--bg2);border:1px solid var(--border);
  border-radius:12px;padding:12px 8px;text-align:center
}}
.stat-val{{font-size:1.2rem;color:var(--gold)}}
.stat-lbl{{
  font-size:.5rem;color:var(--muted);text-transform:uppercase;
  letter-spacing:.1em;margin-top:3px
}}
/* CTA buttons */
.btn-primary{{
  width:100%;max-width:340px;
  background:linear-gradient(135deg,#6b5238,var(--goldD));
  color:var(--cream);border:none;border-radius:24px;
  padding:15px 24px;font-size:.88rem;
  font-family:'Georgia',serif;letter-spacing:.12em;
  text-transform:uppercase;cursor:pointer;
  box-shadow:0 4px 20px rgba(160,120,48,.3);
  transition:filter .15s,transform .1s
}}
.btn-primary:hover{{filter:brightness(1.12)}}
.btn-primary:active{{transform:scale(.97)}}
.btn-ghost-row{{
  display:flex;gap:10px;justify-content:center;
  width:100%;max-width:340px
}}
.btn-ghost{{
  flex:1;
  background:var(--bg2);color:var(--stone);
  border:1px solid var(--border2);border-radius:20px;
  padding:10px 14px;font-size:.7rem;
  font-family:'Georgia',serif;letter-spacing:.08em;
  text-transform:uppercase;cursor:pointer;
  transition:border-color .15s,color .15s,background .15s
}}
.btn-ghost:hover{{
  border-color:var(--stone);color:var(--cream);
  background:var(--bg3)
}}

/* ════════════════════════════════════════════
   DIFFICULTY SCREEN
════════════════════════════════════════════ */
#difficulty{{
  padding:28px 20px 40px;gap:20px;text-align:center;
  background:var(--bg)
}}
.screen-title{{
  font-size:1.6rem;letter-spacing:.22em;text-transform:uppercase;
  color:var(--cream)
}}
.screen-sub{{
  font-size:.75rem;color:var(--sub);font-style:italic;margin-top:-8px
}}
.diff-grid{{
  display:grid;grid-template-columns:repeat(3,1fr);
  gap:12px;width:100%;max-width:640px
}}
.diff-card{{
  border-radius:14px;padding:22px 12px 0;
  display:flex;flex-direction:column;align-items:center;
  gap:8px;cursor:pointer;
  transition:transform .15s,box-shadow .15s;
  border:2px solid
}}
.diff-card:hover{{transform:translateY(-3px)}}
.diff-icon{{font-size:1.8rem}}
.diff-name{{
  font-size:.9rem;letter-spacing:.2em;text-transform:uppercase;
  font-family:'Georgia',serif
}}
.diff-desc{{
  font-size:.68rem;color:var(--sub);font-style:italic;
  line-height:1.45;text-align:center
}}
.diff-pill{{
  font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;
  border:1px solid;border-radius:12px;padding:3px 10px;
  background:var(--bg);margin-top:4px;margin-bottom:16px
}}
.btn-back{{
  background:transparent;color:var(--muted);
  border:1px solid var(--border);border-radius:20px;
  padding:9px 22px;font-size:.7rem;
  font-family:'Georgia',serif;letter-spacing:.08em;
  text-transform:uppercase;cursor:pointer;
  transition:color .15s,border-color .15s
}}
.btn-back:hover{{color:var(--sub);border-color:var(--border2)}}
</style>
</head>
<body>
"""

GAME_HTML += f"""
<!-- ══ SCREEN: HOME ══ -->
<div id="home" class="screen active">
  <div class="logo-ring">
    <img src="{LOGO_URL}" alt="Incairn"/>
  </div>

  <div class="h-pill-row">
    <div class="h-pill" id="h-pnum">Puzzle #—</div>
    <div class="h-pill gold" id="h-streak">🔥 Start your streak</div>
  </div>

  <div class="game-title">INCAIRN</div>
  <div class="game-sub">Arrange the numbers. Discover the rule.</div>
  <div class="home-divider"></div>

  <div class="daily-card" id="daily-card">
    <div class="dc-eyebrow">Today's Cairn</div>
    <div class="dc-date">{today_js}</div>
    <div class="dc-diff" id="daily-diff-pill">—</div>
    <div class="dc-desc">
      Ten stones, one cairn. Every parent stone conceals a
      relationship with the two beneath it. Find the pattern
      and rebuild the pyramid.
    </div>
  </div>

  <div class="stats-row">
    <div class="stat-box">
      <div class="stat-val" id="st-played">—</div>
      <div class="stat-lbl">Solved</div>
    </div>
    <div class="stat-box">
      <div class="stat-val" id="st-streak">—</div>
      <div class="stat-lbl">Streak</div>
    </div>
    <div class="stat-box">
      <div class="stat-val" id="st-best">—</div>
      <div class="stat-lbl">Best Time</div>
    </div>
  </div>

  <button class="btn-primary" onclick="startDailyGame()">
    ▶&nbsp; Play Today's Cairn
  </button>

  <div class="btn-ghost-row">
    <button class="btn-ghost" onclick="showScreen('difficulty')">
      🎯 Practice
    </button>
    <button class="btn-ghost" onclick="showScreen('history')">
      📊 History
    </button>
  </div>
</div>

<!-- ══ SCREEN: DIFFICULTY ══ -->
<div id="difficulty" class="screen">
  <div class="h-pill-row" style="margin-top:28px">
    <div class="h-pill">Practice Mode</div>
  </div>
  <div class="screen-title">Choose Your Stone</div>
  <div class="screen-sub">Each difficulty hides a different arithmetic rule</div>

  <div class="diff-grid">
    <div class="diff-card"
         style="background:#1a2a14;border-color:#3a6028"
         onclick="startPractice('Easy')">
      <div class="diff-icon">＋</div>
      <div class="diff-name" style="color:#7ab06a">Easy</div>
      <div class="diff-desc">Simple addition<br>Great for beginners</div>
      <div class="diff-pill" style="color:#3a6028;border-color:#3a6028">
        10 boards
      </div>
    </div>
    <div class="diff-card"
         style="background:#2a2210;border-color:#6a5218"
         onclick="startPractice('Medium')">
      <div class="diff-icon">≈</div>
      <div class="diff-name" style="color:#d4a843">Medium</div>
      <div class="diff-desc">Hidden offset<br>Pattern thinking</div>
      <div class="diff-pill" style="color:#6a5218;border-color:#6a5218">
        10 boards
      </div>
    </div>
    <div class="diff-card"
         style="background:#2a1e14;border-color:#6a3818"
         onclick="startPractice('Hard')">
      <div class="diff-icon">×</div>
      <div class="diff-name" style="color:#c08860">Hard</div>
      <div class="diff-desc">Multiplication<br>Challenging</div>
      <div class="diff-pill" style="color:#6a3818;border-color:#6a3818">
        5 boards
      </div>
    </div>
  </div>

  <button class="btn-back" onclick="showScreen('home')">← Home</button>
</div>
"""

GAME_HTML += """
<!-- ══ SCREEN: GAME ══ -->
<div id="game" class="screen">
<style>
#game{
  padding:10px 12px 28px;gap:0;
  background:
    radial-gradient(ellipse at 50% -10%, #2a1f0e22, transparent 55%),
    var(--bg);
}
/* top bar */
.g-bar{
  width:100%;max-width:520px;
  display:flex;align-items:center;justify-content:space-between;
  padding:0 2px 10px;
  border-bottom:1px solid var(--border);
  margin-bottom:10px
}
.g-title{
  font-size:.9rem;letter-spacing:.2em;text-transform:uppercase;
  color:var(--stoneL)
}
.g-stat{
  text-align:center;min-width:52px;
  background:var(--bg2);border:1px solid var(--border);
  border-radius:10px;padding:5px 10px
}
.g-sv{font-size:.9rem;color:var(--gold)}
.g-sl{font-size:.5rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}

/* board info */
.g-info{
  font-size:.62rem;color:var(--sub);text-align:center;
  letter-spacing:.1em;text-transform:uppercase;margin-bottom:8px
}
.badge{
  display:inline-block;padding:2px 10px;border-radius:12px;
  font-size:.58rem;text-transform:uppercase;letter-spacing:.08em
}
.easy  {background:#1a2a14;color:#7ab06a;border:1px solid #3a6028}
.medium{background:#2a2210;color:#d4a843;border:1px solid #6a5218}
.hard  {background:#2a1e14;color:#c08860;border:1px solid #6a3818}

/* progress bar */
.prog-wrap{
  width:100%;max-width:520px;
  height:3px;background:var(--border);
  border-radius:2px;margin-bottom:10px;overflow:hidden
}
.prog-fill{
  height:100%;
  background:linear-gradient(90deg,var(--stone),var(--gold));
  border-radius:2px;width:0%;transition:width .3s ease
}

/* PYRAMID — hero 70% */
.pyr{
  display:flex;flex-direction:column;align-items:center;
  gap:9px;margin-bottom:16px;padding:4px 0;
  width:100%;max-width:520px
}
.prow{display:flex;gap:9px;justify-content:center}

/* Stone tiles */
.cell{
  width:76px;height:76px;
  border:2px dashed var(--border);
  background:radial-gradient(ellipse at 35% 35%, var(--bg3), var(--bg2));
  display:flex;align-items:center;justify-content:center;
  font-size:1.2rem;color:var(--sub);
  font-family:'Georgia',serif;
  position:relative;cursor:default;
  border-radius:50%;
  transition:border-color .12s,background .15s,transform .1s,box-shadow .12s
}
.cell.over{
  border-style:solid!important;border-color:var(--gold)!important;
  background:radial-gradient(ellipse at 35% 35%, var(--bg4), var(--bg3))!important;
  transform:scale(1.08);box-shadow:0 0 18px rgba(212,168,67,.35)
}
.cell.full{
  border-style:solid;border-color:var(--border3);
  background:radial-gradient(ellipse at 30% 30%, var(--bg4), var(--bg3));
  color:var(--cream);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.05),0 2px 8px rgba(0,0,0,.5)
}
.cell.snap{animation:snap-in .22s cubic-bezier(.34,1.56,.64,1) forwards}
@keyframes snap-in{
  0%{transform:scale(1.18);box-shadow:0 0 22px rgba(212,168,67,.6)}
  100%{transform:scale(1);box-shadow:0 2px 8px rgba(0,0,0,.5)}
}
.cell.row-flash{animation:row-flash .5s ease forwards}
@keyframes row-flash{
  0%{box-shadow:0 0 0 0 rgba(212,168,67,.4)}
  50%{box-shadow:0 0 0 8px rgba(212,168,67,.15)}
  100%{box-shadow:0 2px 8px rgba(0,0,0,.5)}
}
.cell.ok{
  border-color:var(--green)!important;border-style:solid!important;
  background:radial-gradient(ellipse at 35% 35%,#2e5428,#1e3818)!important;
  color:var(--greenL)!important;
  box-shadow:0 0 14px rgba(74,112,64,.5)!important;
  animation:ok-pop .35s ease
}
@keyframes ok-pop{0%{transform:scale(.93)}60%{transform:scale(1.06)}100%{transform:scale(1)}}
.cell.bad{
  border-color:var(--wrongB)!important;border-style:solid!important;
  background:radial-gradient(ellipse at 35% 35%,var(--wrong),#1a0a06)!important;
  color:#c07050!important;animation:shake .28s ease
}
@keyframes shake{0%,100%{transform:translateX(0)}30%{transform:translateX(-5px)}70%{transform:translateX(5px)}}
.cell.hint{
  border-color:var(--amber)!important;border-style:solid!important;
  animation:hint-pulse 1s ease-in-out infinite
}
@keyframes hint-pulse{
  0%,100%{box-shadow:0 0 0 0 rgba(192,136,32,.3)}
  50%{box-shadow:0 0 0 8px rgba(192,136,32,.1)}
}
.rm{
  position:absolute;top:3px;right:4px;
  font-size:.5rem;color:var(--muted);cursor:pointer;
  opacity:0;background:none;border:none;padding:0;transition:opacity .1s
}
.cell:hover .rm{opacity:.8}

/* Number tray */
.tray-lbl{
  font-size:.58rem;color:var(--muted);text-transform:uppercase;
  letter-spacing:.14em;margin-bottom:7px;font-style:italic;text-align:center
}
.tray{
  display:flex;flex-wrap:wrap;gap:8px;justify-content:center;
  background:var(--bg2);border:1px solid var(--border);
  border-radius:18px;padding:11px 12px;margin-bottom:14px;
  min-height:56px;width:100%;max-width:520px
}
.chip{
  width:54px;height:54px;
  background:radial-gradient(ellipse at 35% 35%, var(--bg4), var(--bg3));
  border:1.5px solid var(--border3);border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:1rem;color:var(--cream);
  font-family:'Georgia',serif;cursor:grab;
  transition:transform .1s,box-shadow .1s,opacity .12s,border-color .1s;
  box-shadow:0 2px 8px rgba(0,0,0,.5),inset 0 1px 0 rgba(255,255,255,.05)
}
.chip:hover{
  transform:translateY(-3px) scale(1.08);
  border-color:var(--gold);
  box-shadow:0 6px 18px rgba(0,0,0,.6),0 0 10px rgba(212,168,67,.2)
}
.chip:active{cursor:grabbing}
.chip.dragging{opacity:.15;transform:scale(.88)}
.chip.used{opacity:0;pointer-events:none}
.chip-ghost{
  position:fixed;pointer-events:none;z-index:9990;
  border-radius:50%;opacity:.85;
  box-shadow:0 14px 32px rgba(0,0,0,.7),0 0 18px rgba(212,168,67,.4);
  transform:scale(1.14);border:2px solid var(--gold)
}

/* Action row */
.act-row{display:flex;gap:8px;width:100%;max-width:520px;margin-bottom:6px}
.btn-hint{
  flex:1;background:var(--bg2);color:var(--gold);
  border:1.5px solid var(--goldD);border-radius:24px;
  padding:12px 6px;font-size:.7rem;cursor:pointer;
  text-transform:uppercase;letter-spacing:.08em;
  font-family:'Georgia',serif;transition:background .1s
}
.btn-hint:hover{background:var(--bg3)}
.btn-hint:disabled{opacity:.3;cursor:not-allowed}
.btn-check{
  flex:2.4;
  background:linear-gradient(135deg,var(--stone),var(--goldD));
  color:var(--cream);border:none;border-radius:24px;
  padding:12px;font-size:.78rem;cursor:pointer;
  text-transform:uppercase;letter-spacing:.12em;
  font-family:'Georgia',serif;
  box-shadow:0 3px 12px rgba(139,115,85,.35);
  transition:filter .1s
}
.btn-check:hover{filter:brightness(1.12)}
.btn-reset{
  flex:.5;background:var(--bg2);color:var(--muted);
  border:1px solid var(--border);border-radius:24px;
  padding:12px;font-size:.85rem;cursor:pointer;
  transition:color .1s
}
.btn-reset:hover{color:var(--sub)}

/* Footer */
.g-foot{
  display:flex;justify-content:space-between;
  width:100%;max-width:520px;
  font-size:.58rem;color:var(--muted);margin-top:4px;
  text-transform:uppercase;letter-spacing:.08em
}
.btn-exit{
  background:transparent;color:var(--muted);
  border:none;font-size:.58rem;cursor:pointer;
  text-decoration:underline;text-underline-offset:2px;
  font-family:'Georgia',serif;letter-spacing:.06em;
  text-transform:uppercase;padding:0
}
.btn-exit:hover{color:var(--sub)}

/* Toast */
.toast{
  position:fixed;top:16px;left:50%;transform:translateX(-50%);
  padding:11px 24px;border-radius:24px;font-size:.78rem;
  z-index:9999;opacity:0;transition:opacity .22s;
  pointer-events:none;text-align:center;max-width:90vw;
  text-transform:uppercase;letter-spacing:.08em;font-family:'Georgia',serif
}
.toast.show{opacity:1}
.toast.win{background:var(--green);color:#b0e8a0;border:1px solid var(--green)}
.toast.err{background:var(--wrong);color:#c08060;border:1px solid var(--wrongB)}
.toast.info{background:var(--bg3);color:var(--gold);border:1px solid var(--goldD)}
#cv{position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9998}
</style>

<canvas id="cv"></canvas>
<div class="toast" id="toast"></div>

<!-- top bar -->
<div class="g-bar">
  <div class="g-stat"><div class="g-sv" id="g-tmr">0:00</div><div class="g-sl">time</div></div>
  <div class="g-title" id="g-mode-label">Incairn</div>
  <div class="g-stat"><div class="g-sv" id="g-mvc">0</div><div class="g-sl">moves</div></div>
</div>

<!-- board info -->
<div class="g-info">
  <span id="g-bid">—</span> &nbsp;·&nbsp;
  <span class="badge" id="g-diff-badge">—</span>
</div>

<!-- progress bar -->
<div class="prog-wrap"><div class="prog-fill" id="g-prog"></div></div>

<!-- PYRAMID -->
<div class="pyr" id="pyr">
  <div class="prow"><div class="cell" data-i="0"></div></div>
  <div class="prow">
    <div class="cell" data-i="1"></div><div class="cell" data-i="2"></div>
  </div>
  <div class="prow">
    <div class="cell" data-i="3"></div>
    <div class="cell" data-i="4"></div>
    <div class="cell" data-i="5"></div>
  </div>
  <div class="prow">
    <div class="cell" data-i="6"></div><div class="cell" data-i="7"></div>
    <div class="cell" data-i="8"></div><div class="cell" data-i="9"></div>
  </div>
</div>

<!-- tray -->
<div class="tray-lbl">Ten stones — drag into the cairn</div>
<div class="tray" id="tray"></div>

<!-- action row -->
<div class="act-row">
  <button class="btn-hint" id="hbtn" onclick="doHint()">💡 Hint (3)</button>
  <button class="btn-check" onclick="doCheck()">Check the Cairn</button>
  <button class="btn-reset" onclick="doReset()">↺</button>
</div>
<div class="g-foot">
  <span id="g-placed">0 / 10 placed</span>
  <button class="btn-exit" onclick="showScreen('home')">✕ Exit</button>
</div>
</div>
"""

GAME_HTML += """
<!-- ══ SCREEN: WIN ══ -->
<div id="win" class="screen">
<style>
#win{
  padding:32px 20px 40px;gap:16px;text-align:center;
  justify-content:center;
  background:
    radial-gradient(ellipse at 50% 0%, #1a3010 0%, transparent 60%),
    var(--bg)
}
.win-icon{font-size:3.5rem;animation:drop-in .5s cubic-bezier(.34,1.56,.64,1)}
@keyframes drop-in{0%{transform:translateY(-28px);opacity:0}100%{transform:none;opacity:1}}
.win-title{font-size:2rem;letter-spacing:.2em;text-transform:uppercase;color:var(--cream)}
.win-sub{font-size:.8rem;color:var(--sub);font-style:italic;margin-top:-8px}
.win-divider{
  width:100%;max-width:380px;height:1px;
  background:linear-gradient(90deg,transparent,var(--border2),transparent)
}
.win-stats{
  display:grid;grid-template-columns:repeat(3,1fr);
  gap:10px;width:100%;max-width:380px
}
.wsc{
  background:var(--bg2);border:1px solid var(--border);
  border-radius:12px;padding:14px 8px;text-align:center
}
.wsv{font-size:1.2rem;color:var(--gold)}
.wsl{font-size:.52rem;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;margin-top:4px}
/* rule reveal */
.rule-reveal{
  width:100%;max-width:380px;
  background:linear-gradient(135deg,var(--bg4),var(--bg3));
  border:1px solid var(--goldD);border-radius:14px;
  padding:18px 20px;text-align:center;
  animation:reveal-in .5s ease .3s both
}
@keyframes reveal-in{0%{opacity:0;transform:translateY(10px)}100%{opacity:1;transform:none}}
.rr-label{
  font-size:.58rem;letter-spacing:.18em;text-transform:uppercase;
  color:var(--stone);margin-bottom:8px
}
.rr-rule{font-size:1.05rem;color:var(--gold);font-style:italic}
.rr-note{font-size:.7rem;color:var(--sub);margin-top:8px;font-style:italic}
.streak-row{display:flex;gap:10px;justify-content:center}
.streak-chip{
  background:var(--bg2);border:1px solid var(--border);
  border-radius:10px;padding:10px 16px;font-size:.75rem;color:var(--gold)
}
.win-actions{
  display:flex;gap:10px;justify-content:center;
  flex-wrap:wrap;width:100%;max-width:380px
}
.btn-win-primary{
  flex:1;min-width:140px;
  background:linear-gradient(135deg,#4a7040,#3a6028);
  color:#c8e6c0;border:none;border-radius:20px;
  padding:12px 16px;font-size:.75rem;cursor:pointer;
  font-family:'Georgia',serif;letter-spacing:.08em;
  text-transform:uppercase;transition:filter .1s
}
.btn-win-primary:hover{filter:brightness(1.12)}
.btn-win-ghost{
  flex:1;min-width:120px;
  background:var(--bg2);color:var(--sub);
  border:1px solid var(--border);border-radius:20px;
  padding:12px 16px;font-size:.72rem;cursor:pointer;
  font-family:'Georgia',serif;letter-spacing:.08em;
  text-transform:uppercase;transition:border-color .1s,color .1s
}
.btn-win-ghost:hover{border-color:var(--stone);color:var(--cream)}
</style>

<div class="win-icon">🗿</div>
<div class="win-title">Cairn Complete</div>
<div class="win-sub">You discovered the hidden rule</div>
<div class="win-divider"></div>

<div class="win-stats">
  <div class="wsc"><div class="wsv" id="w-time">—</div><div class="wsl">Time</div></div>
  <div class="wsc">
    <div class="wsv" id="w-bid" style="font-size:.85rem;letter-spacing:.08em">—</div>
    <div class="wsl">Board</div>
  </div>
  <div class="wsc">
    <div class="wsv"><span class="badge" id="w-diff">—</span></div>
    <div class="wsl" style="margin-top:8px">Difficulty</div>
  </div>
</div>

<div class="rule-reveal">
  <div class="rr-label">◈ The Hidden Rule Was</div>
  <div class="rr-rule" id="w-rule">—</div>
  <div class="rr-note">Every parent stone was derived from its two children using this rule.</div>
</div>

<div class="streak-row">
  <div class="streak-chip" id="w-streak">🔥 —</div>
  <div class="streak-chip" id="w-played">— puzzles solved</div>
</div>

<div class="win-actions">
  <button class="btn-win-primary" onclick="onWinPlayAgain()">▶ Play Again</button>
  <button class="btn-win-ghost" onclick="showFeedback()">📝 Rate Puzzle</button>
  <button class="btn-win-ghost" onclick="showScreen('history')">📊 History</button>
  <button class="btn-win-ghost" onclick="showScreen('home')">🏠 Home</button>
</div>
</div>
"""

GAME_HTML += """
<!-- ══ SCREEN: HISTORY ══ -->
<div id="history" class="screen">
<style>
#history{padding:24px 16px 40px;gap:14px;background:var(--bg)}
.hist-stats{display:flex;gap:8px;justify-content:center;width:100%;max-width:460px}
.cal-grid{
  display:grid;grid-template-columns:repeat(7,1fr);
  gap:5px;width:100%;max-width:360px
}
.cal-day{
  aspect-ratio:1;border-radius:6px;
  border:1px solid var(--border);background:var(--bg2);
  display:flex;align-items:center;justify-content:center;
  flex-direction:column;gap:1px
}
.cal-day.solved{background:var(--green);border-color:var(--green);color:#b0e8a0}
.cal-day.today{border-color:var(--gold)!important;color:var(--gold)}
.cal-num{font-size:.58rem}
.cal-dot{width:4px;height:4px;border-radius:50%;background:currentColor;opacity:.7}
.hist-list{width:100%;max-width:460px;display:flex;flex-direction:column;gap:8px}
.hist-row{
  background:var(--bg2);border:1px solid var(--border);
  border-radius:10px;padding:11px 14px;
  display:flex;align-items:center;justify-content:space-between
}
.hist-bid{font-size:.78rem;color:var(--cream);letter-spacing:.08em;text-transform:uppercase}
.hist-date{font-size:.65rem;color:var(--sub);margin-top:2px}
.hist-meta{display:flex;gap:8px;align-items:center}
.hist-time{font-size:.72rem;color:var(--gold)}
.hist-empty{font-size:.78rem;color:var(--muted);font-style:italic;text-align:center;padding:24px 0}
.sec-label{
  font-size:.58rem;letter-spacing:.18em;text-transform:uppercase;
  color:var(--stone);width:100%;max-width:460px;
  padding-bottom:6px;border-bottom:1px solid var(--border)
}
</style>

<div class="h-pill-row" style="margin-top:4px">
  <div class="h-pill">Your Cairns</div>
</div>
<div class="screen-title" style="font-size:1.4rem">Completion History</div>

<div class="hist-stats">
  <div class="stat-box"><div class="stat-val" id="hs-p">—</div><div class="stat-lbl">Solved</div></div>
  <div class="stat-box"><div class="stat-val" id="hs-s">—</div><div class="stat-lbl">Streak</div></div>
  <div class="stat-box"><div class="stat-val" id="hs-b">—</div><div class="stat-lbl">Best</div></div>
</div>

<div class="sec-label">Last 28 Days</div>
<div class="cal-grid" id="cal"></div>

<div class="sec-label">Recent Solves</div>
<div class="hist-list" id="hist-list">
  <div class="hist-empty">No solves yet. Complete a cairn to begin your history.</div>
</div>

<button class="btn-back" onclick="showScreen('home')" style="margin-top:8px">← Home</button>
</div>

<!-- ══ SCREEN: FEEDBACK ══ -->
<div id="feedback-screen" class="screen">
<style>
#feedback-screen{padding:32px 20px 40px;gap:16px;text-align:center;justify-content:center;background:var(--bg)}
.fb-title{font-size:1.4rem;letter-spacing:.2em;text-transform:uppercase;color:var(--cream)}
.fb-sub{font-size:.75rem;color:var(--sub);font-style:italic;margin-top:-8px}
.star-row{display:flex;gap:8px;justify-content:center}
.star{font-size:1.6rem;cursor:pointer;opacity:.3;transition:opacity .1s,transform .1s}
.star.on{opacity:1}
.star:hover{transform:scale(1.2)}
.fb-label{font-size:.62rem;color:var(--stone);text-transform:uppercase;letter-spacing:.12em;margin-bottom:6px}
textarea.fb-text{
  width:100%;max-width:380px;background:var(--bg2);
  border:1px solid var(--border2);border-radius:10px;
  color:var(--cream);padding:12px;font-size:.85rem;
  resize:none;outline:none;font-family:'Georgia',serif;min-height:80px
}
textarea.fb-text:focus{border-color:var(--goldD)}
.fb-actions{display:flex;gap:10px;justify-content:center;width:100%;max-width:380px}
.btn-fb-submit{
  flex:1;background:linear-gradient(135deg,var(--stone),var(--goldD));
  color:var(--cream);border:none;border-radius:20px;
  padding:12px;font-size:.78rem;cursor:pointer;
  font-family:'Georgia',serif;letter-spacing:.08em;text-transform:uppercase
}
.btn-fb-skip{
  flex:1;background:var(--bg2);color:var(--sub);
  border:1px solid var(--border);border-radius:20px;
  padding:12px;font-size:.75rem;cursor:pointer;
  font-family:'Georgia',serif;letter-spacing:.08em;text-transform:uppercase
}
</style>

<div class="win-icon">📝</div>
<div class="fb-title">Rate This Cairn</div>
<div class="fb-sub" id="fb-bid-label">—</div>

<div>
  <div class="fb-label">Difficulty Feel</div>
  <div class="star-row" id="diff-stars">
    <span class="star" data-g="diff" data-v="1">⭐</span>
    <span class="star" data-g="diff" data-v="2">⭐</span>
    <span class="star" data-g="diff" data-v="3">⭐</span>
    <span class="star" data-g="diff" data-v="4">⭐</span>
    <span class="star" data-g="diff" data-v="5">⭐</span>
  </div>
</div>
<div>
  <div class="fb-label">How Enjoyable</div>
  <div class="star-row" id="fun-stars">
    <span class="star" data-g="fun" data-v="1">⭐</span>
    <span class="star" data-g="fun" data-v="2">⭐</span>
    <span class="star" data-g="fun" data-v="3">⭐</span>
    <span class="star" data-g="fun" data-v="4">⭐</span>
    <span class="star" data-g="fun" data-v="5">⭐</span>
  </div>
</div>

<textarea class="fb-text" id="fb-comments" placeholder="Too easy, great pattern, took 5 minutes…"></textarea>

<div class="fb-actions">
  <button class="btn-fb-submit" onclick="submitFeedback()">Submit</button>
  <button class="btn-fb-skip" onclick="showScreen('win')">Skip</button>
</div>
</div>
"""

GAME_HTML += f"""
<script>
// ═══════════════════════════════════════════════════════
// DATA
// ═══════════════════════════════════════════════════════
const BOARDS     = {boards_js};
const DAILY_NUM  = {daily_js};
const TODAY_STR  = new Date().toISOString().split('T')[0];
const RULE_NAMES = {{
  // ── R1 (original boards) ────────────────────────────────
  Gen01_Add:'Left + Right', Gen02_Mul:'Left × Right', Gen03_AddPlus1:'Left + Right + 1',
  R1_E01:'Left + Right', R1_E02:'Left + Right + 1', R1_E03:'Left + Right − 1',
  R1_E04:'2 × Left + Right', R1_E05:'Left + 2 × Right',
  R1_E06:'|Left − Right|', R1_E07:'Max(Left, Right)', R1_E08:'Min(Left, Right)',
  R1_M01:'Left × Right', R1_M02:'Left × Right + 1', R1_M03:'Left × Right − 1',
  R1_M04:'Left × Right + Left', R1_M05:'Left × Right + Right',
  R1_H01:'Left × Right + Left + Right', R1_H02:'Left × Right − Left',
  R1_H03:'Left × Right − Right', R1_H04:'Left × Right − (Left+Right)', R1_H05:'Left × Right + 2',
  // ── R2 (new boards) ─────────────────────────────────────
  R2_E01:'Left + Right + a',      // z=x+y+a
  R2_E02:'2 × Left + Right',      // z=2x+y
  R2_E03:'Left + 2 × Right',      // z=x+2y
  R2_E04:'Left + Right − a',      // z=x+y-a
  R2_E09:'Min(Left, Right)',       // z=min(x,y)
  R2_E10:'Max(Left, Right)',       // z=max(x,y)
  R2_M02:'Left × Right − a',      // z=x*y-a
  R2_M04:'Left × Right − Left',   // z=x*y-x
  R2_M06:'Left × Right − Right',  // z=x*y-y
  R2_M07:'(Left + Right) / 2 + a',// z=(x+y)/2+a
  R2_M08:'(Left + Right) / 2 − a',// z=(x+y)/2-a
  R2_H04:'Left × Right − a',      // z=x*y-a
  R2_H08:'(Left × Right) / 2',    // z=(x*y)/2
  R2_H09:'(Left × Right) / 3',    // z=(x*y)/3
}};

// Rule functions — used by doCheck() to verify the cairn.
// For R2 boards the relationship string (b.rel) is shown on the win screen
// instead of deriving a human label, so the RF function just needs to
// compute the correct value.  Where a rule has a parameter (a) we parse
// it from the relationship string at board-load time (see parseA below).
function parseA(rel) {{
  // Extract the constant from strings like "z=x+y+3", "z=x*y-7", "z=(x+y)/2+8"
  const m = rel.match(/[+\-](\d+)$/);
  return m ? parseInt(m[1]) * (rel.includes('-') && rel.lastIndexOf('-') > rel.lastIndexOf('+') ? -1 : 1) : 0;
}}

const RF = {{
  // ── R1 ──
  Gen01_Add:(a,b)=>a+b, Gen02_Mul:(a,b)=>a*b, Gen03_AddPlus1:(a,b)=>a+b+1,
  R1_E01:(a,b)=>a+b, R1_E02:(a,b)=>a+b+1, R1_E03:(a,b)=>a+b-1,
  R1_E04:(a,b)=>2*a+b, R1_E05:(a,b)=>a+2*b,
  R1_E06:(a,b)=>Math.abs(a-b), R1_E07:(a,b)=>Math.max(a,b), R1_E08:(a,b)=>Math.min(a,b),
  R1_M01:(a,b)=>a*b, R1_M02:(a,b)=>a*b+1, R1_M03:(a,b)=>a*b-1,
  R1_M04:(a,b)=>a*b+a, R1_M05:(a,b)=>a*b+b,
  R1_H01:(a,b)=>a*b+a+b, R1_H02:(a,b)=>a*b-a, R1_H03:(a,b)=>a*b-b,
  R1_H04:(a,b)=>a*b-(a+b), R1_H05:(a,b)=>a*b+2,
  // ── R2 — these are generated dynamically from the relationship string ──
  // Stubs are replaced at game-start time by buildRF()
}};

// Build a live rule function from a relationship string like "z=x+y+3"
function buildRF(rel) {{
  const r = rel.replace(/\s/g,'').toLowerCase();
  if(r==='z=x+y'||r==='z=y+x')   return (x,y)=>x+y;
  if(r==='z=2x+y')                return (x,y)=>2*x+y;
  if(r==='z=x+2y')                return (x,y)=>x+2*y;
  if(r==='z=max(x,y)')            return (x,y)=>Math.max(x,y);
  if(r==='z=min(x,y)')            return (x,y)=>Math.min(x,y);
  if(r==='z=x*y')                 return (x,y)=>x*y;
  if(r==='z=x*y-x')               return (x,y)=>x*y-x;
  if(r==='z=x*y-y')               return (x,y)=>x*y-y;
  // z=x+y+N  /  z=x+y-N
  let m=r.match(/^z=x\+y([+\-]\d+)$/);
  if(m) {{ const k=parseInt(m[1]); return (x,y)=>x+y+k; }}
  // z=x*y+N  /  z=x*y-N
  m=r.match(/^z=x\*y([+\-]\d+)$/);
  if(m) {{ const k=parseInt(m[1]); return (x,y)=>x*y+k; }}
  // z=(x+y)/2+N  /  z=(x+y)/2-N  /  z=(x+y)/2
  m=r.match(/^z=\(x\+y\)\/2([+\-]\d+)?$/);
  if(m) {{ const k=m[1]?parseInt(m[1]):0; return (x,y)=>(x+y)/2+k; }}
  // z=(x*y)/2  /  z=(x*y)/3
  m=r.match(/^z=\(x\*y\)\/(\d+)$/);
  if(m) {{ const d=parseInt(m[1]); return (x,y)=>(x*y)/d; }}
  // fallback: eval-based (safe — only board data)
  return null;
}}
const TR=[[0,1,2],[1,3,4],[2,4,5],[3,6,7],[4,7,8],[5,8,9]];
const ROWS=[[0],[1,2],[3,4,5],[6,7,8,9]];

// ═══════════════════════════════════════════════════════
// SCREEN NAVIGATION
// ═══════════════════════════════════════════════════════
function showScreen(id) {{
  document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));
  const el = document.getElementById(id) || document.getElementById(id+'-screen');
  if(el) el.classList.add('active');
  window.scrollTo(0,0);
  if(id==='home')     loadHomeStats();
  if(id==='history')  buildHistory();
  if(id==='feedback-screen') buildFeedback();
}}

// ═══════════════════════════════════════════════════════
// HOME
// ═══════════════════════════════════════════════════════
function loadHomeStats() {{
  try {{
    const daily = BOARDS.find(b=>b.num===DAILY_NUM)||BOARDS[0];
    const dc = daily.diff.toLowerCase();
    const diffColors = {{easy:'#7ab06a',medium:'#d4a843',hard:'#c08860'}};
    const diffBg = {{easy:'#1a2a14',medium:'#2a2210',hard:'#2a1e14'}};
    const diffBdr = {{easy:'#3a6028',medium:'#6a5218',hard:'#6a3818'}};
    const pill = document.getElementById('daily-diff-pill');
    if(pill) {{
      pill.textContent = daily.diff;
      pill.style.background = diffBg[dc];
      pill.style.color = diffColors[dc];
      pill.style.border = '1px solid '+diffBdr[dc];
    }}
    document.getElementById('h-pnum').textContent = 'Puzzle #'+DAILY_NUM;
    const s = JSON.parse(localStorage.getItem('incairn_stats')||'{{}}');
    document.getElementById('st-played').textContent = s.played||'—';
    document.getElementById('st-streak').textContent = s.streak||'—';
    document.getElementById('h-streak').textContent =
      (s.streak||0)>0?'🔥 '+s.streak+' day streak':'🔥 Start your streak';
    const b=s.bestTime||0,m=Math.floor(b/60),sec=b%60;
    document.getElementById('st-best').textContent =
      b>0?(m>0?m+'m '+sec+'s':sec+'s'):'—';
  }} catch(e) {{}}
}}

// ═══════════════════════════════════════════════════════
// GAME STATE
// ═══════════════════════════════════════════════════════
let G = {{
  board:null, mode:'daily',
  C:Array(10).fill(null), CID:{{}}, CS:{{}},
  drag:null, moves:0, solved:false,
  elapsed:0, t0:0, timerRef:null, hintsLeft:3
}};

function startDailyGame() {{
  const b = BOARDS.find(b=>b.num===DAILY_NUM)||BOARDS[0];
  startGame(b, 'daily');
}}

function startPractice(diff) {{
  const pool = BOARDS.filter(b=>b.diff===diff);
  const b = pool[Math.floor(Math.random()*pool.length)];
  startGame(b, 'practice');
}}

function startGame(board, mode) {{
  G.board=board; G.mode=mode;
  G.C=Array(10).fill(null); G.CID={{}}; G.CS={{}};
  G.drag=null; G.moves=0; G.solved=false;
  G.elapsed=0; G.t0=Date.now(); G.hintsLeft=3;
  if(G.timerRef)clearInterval(G.timerRef);
  G.timerRef=setInterval(()=>{{
    G.elapsed=Math.floor((Date.now()-G.t0)/1000);
    const m=Math.floor(G.elapsed/60),s=G.elapsed%60;
    document.getElementById('g-tmr').textContent=m+':'+(s<10?'0':'')+s;
  }},1000);
  // Set UI labels
  document.getElementById('g-bid').textContent=board.bid.toUpperCase();
  const dc=board.diff.toLowerCase();
  const badge=document.getElementById('g-diff-badge');
  badge.textContent=board.diff; badge.className='badge '+dc;
  document.getElementById('g-mode-label').textContent =
    mode==='daily'?"Today's Cairn":"Practice · "+board.diff;
  document.getElementById('g-mvc').textContent='0';
  document.getElementById('g-tmr').textContent='0:00';
  document.getElementById('g-placed').textContent='0 / 10 placed';
  document.getElementById('g-prog').style.width='0%';
  document.getElementById('hbtn').textContent='💡 Hint (3)';
  document.getElementById('hbtn').disabled=false;
  initTray();
  renderCells();
  showScreen('game');
}}

// ═══════════════════════════════════════════════════════
// TRAY & DRAG
// ═══════════════════════════════════════════════════════
function initTray(){{
  const tray=document.getElementById('tray'); tray.innerHTML='';
  document.querySelectorAll('.cell').forEach(el=>{{
    el.innerHTML='';
    el.ondragover=e=>{{e.preventDefault();el.classList.add('over');}};
    el.ondragleave=()=>el.classList.remove('over');
    el.ondrop=onDrop;
  }});
  G.board.puz.forEach((v,i)=>{{
    const id='p'+i; G.CS[id]={{v,placed:false}};
    const d=document.createElement('div');
    d.className='chip'; d.id=id; d.textContent=v; d.draggable=true;
    d.addEventListener('dragstart',e=>{{G.drag={{t:'tray',id}};
      e.dataTransfer.effectAllowed='move'; d.classList.add('dragging');}});
    d.addEventListener('dragend',()=>d.classList.remove('dragging'));
    d.addEventListener('touchstart',tS,{{passive:true}});
    d.addEventListener('touchmove',tM,{{passive:false}});
    d.addEventListener('touchend',tE);
    tray.appendChild(d);
  }});
  tray.ondragover=e=>e.preventDefault();
  tray.ondrop=e=>{{e.preventDefault();
    if(G.drag&&G.drag.t==='cell'){{ret(G.drag.idx);G.drag=null;clrV();}}}};
}}

function onDrop(e){{
  e.preventDefault(); const el=e.currentTarget; el.classList.remove('over');
  const ti=parseInt(el.dataset.i); if(!G.drag)return;
  if(G.drag.t==='tray'){{
    if(G.C[ti]!==null)ret(ti); place(G.drag.id,G.CS[G.drag.id].v,ti,true);
  }} else if(G.drag.t==='cell'&&G.drag.idx!==ti){{
    [G.C[ti],G.C[G.drag.idx]]=[G.C[G.drag.idx],G.C[ti]];
    [G.CID[ti],G.CID[G.drag.idx]]=[G.CID[G.drag.idx],G.CID[ti]];
    G.moves++; document.getElementById('g-mvc').textContent=G.moves;
    renderCells(); updateProg();
  }}
  G.drag=null; clrV();
}}

function place(id,v,i,anim){{
  G.C[i]=v; G.CS[id].placed=true; G.CID[i]=id;
  document.getElementById(id).classList.add('used');
  G.moves++; document.getElementById('g-mvc').textContent=G.moves;
  renderCells();
  if(anim){{const el=document.querySelector('.cell[data-i="'+i+'"]');
    if(el){{el.classList.add('snap');el.addEventListener('animationend',()=>el.classList.remove('snap'),{{once:true}});}};
  }}
  updateProg(); checkRowFlash(i);
}}
function ret(i){{
  const id=G.CID[i]; G.C[i]=null; delete G.CID[i];
  if(id){{G.CS[id].placed=false;const c=document.getElementById(id);if(c)c.classList.remove('used');}}
  renderCells(); updateProg();
}}
function rmCell(i){{ret(i);clrV();}}
function renderCells(){{
  document.querySelectorAll('.cell').forEach(el=>{{
    const i=parseInt(el.dataset.i),v=G.C[i];
    el.textContent=''; el.classList.remove('full','ok','bad','hint');
    if(v!==null){{
      el.textContent=v; el.classList.add('full'); el.draggable=true;
      el.ondragstart=e=>{{G.drag={{t:'cell',idx:i}};e.dataTransfer.effectAllowed='move';}};
      const rm=document.createElement('button');rm.className='rm';rm.textContent='✕';
      rm.onclick=()=>rmCell(i); el.appendChild(rm);
      // Touch listeners for mobile rearranging
      el.ontouchstart=tS;
      el.ontouchmove=tM;
      el.ontouchend=tE;
    }}else{{
      el.draggable=false;el.ondragstart=null;
      el.ontouchstart=null;el.ontouchmove=null;el.ontouchend=null;
    }}
  }});
}}
function updateProg(){{
  const n=G.C.filter(v=>v!==null).length;
  document.getElementById('g-prog').style.width=(n/10*100)+'%';
  document.getElementById('g-placed').textContent=n+' / 10 placed';
}}
function checkRowFlash(pi){{
  ROWS.forEach(row=>{{
    if(!row.includes(pi))return;
    if(row.every(i=>G.C[i]!==null)){{
      row.forEach(i=>{{const el=document.querySelector('.cell[data-i="'+i+'"]');
        if(el){{el.classList.add('row-flash');el.addEventListener('animationend',()=>el.classList.remove('row-flash'),{{once:true}});}};
      }});
    }}
  }});
}}
function doReset(){{
  G.C=Array(10).fill(null); G.CID={{}};
  Object.keys(G.CS).forEach(id=>{{G.CS[id].placed=false;
    const c=document.getElementById(id);if(c)c.classList.remove('used','dragging');}});
  clrV(); renderCells(); updateProg();
}}
function doHint(){{
  // If all cells are filled but wrong: highlight the first wrong cell
  // using the solution, so player knows which stone to swap out.
  const allFilled = G.C.every(v => v !== null);

  if(allFilled){{
    // Find the first cell that has the wrong value
    const order = [6,7,8,9, 3,4,5, 1,2, 0];
    for(const i of order){{
      if(G.C[i] !== G.board.sol[i]){{
        hlt(i, G.board.sol[i]);
        return;
      }}
    }}
    // All cells correct — already solved
    showToast('Every stone is in place!','win');
    return;
  }}

  // Otherwise: find an empty cell whose correct chip is still in the tray
  const unplaced = Object.values(G.CS)
    .filter(c => !c.placed)
    .map(c => c.v);

  const order = [6,7,8,9, 3,4,5, 1,2, 0];
  for(const i of order){{
    if(G.C[i] !== null) continue;
    const correctVal = G.board.sol[i];
    if(unplaced.includes(correctVal)){{
      hlt(i, correctVal);
      return;
    }}
  }}
  // Shouldn't reach here, but fallback
  showToast('Try rearranging the stones already placed','info');
}}
function hlt(i,v){{
  G.hintsLeft=Math.max(0,G.hintsLeft-1);
  document.getElementById('hbtn').textContent='💡 Hint ('+G.hintsLeft+')';
  if(G.hintsLeft===0)document.getElementById('hbtn').disabled=true;
  const el=document.querySelector('.cell[data-i="'+i+'"]');if(!el)return;
  el.classList.add('hint'); showToast('This stone holds '+v,'info');
  setTimeout(()=>el.classList.remove('hint'),3500);
}}
function doCheck(){{
  if(G.solved)return;
  const vals=Array.from({{length:10}},(_,i)=>G.C[i]);
  if(vals.some(v=>v===null)){{showToast('Place all ten stones first','info');return;}}
  // R2 boards: build rule fn from relationship string
  const fn = G.board.gen.startsWith('R2_')
    ? buildRF(G.board.rel)
    : RF[G.board.gen];
  if(!fn){{showToast('Unknown rule — cannot verify','err');return;}}
  let ok=true;
  document.querySelectorAll('.cell').forEach(e=>e.classList.remove('ok','bad'));
  let delay=0;
  TR.forEach(([p,l,r])=>{{
    const good=vals[p]===fn(vals[l],vals[r]); if(!good)ok=false;
    [p,l,r].forEach(idx=>{{
      const el=document.querySelector('.cell[data-i="'+idx+'"]');
      if(el)setTimeout(()=>el.classList.add(good?'ok':'bad'),delay);
      delay+=45;
    }});
  }});
  G.moves++; document.getElementById('g-mvc').textContent=G.moves;
  setTimeout(()=>{{
    if(ok){{G.solved=true;clearInterval(G.timerRef);
      showToast('The cairn is complete ◈','win');
      launchConfetti(); saveProgress(); showWin();}}
    else showToast('The pattern is not right — rearrange the stones','err');
  }},delay+100);
}}
function clrV(){{document.querySelectorAll('.cell').forEach(e=>e.classList.remove('ok','bad'));}}

// ═══════════════════════════════════════════════════════
// WIN
// ═══════════════════════════════════════════════════════
function showWin(){{
  setTimeout(()=>{{
    const b=G.board, t=G.elapsed;
    const m=Math.floor(t/60),s=t%60;
    document.getElementById('w-time').textContent=m>0?m+'m '+s+'s':s+'s';
    document.getElementById('w-bid').textContent=b.bid.toUpperCase();
    const badge=document.getElementById('w-diff');
    badge.textContent=b.diff; badge.className='badge '+b.diff.toLowerCase();
    document.getElementById('w-rule').textContent=
      'Parent = '+(G.board.gen.startsWith('R2_')
        ? G.board.rel                        // e.g. "z=x+y+3"
        : (RULE_NAMES[G.board.gen]||G.board.gen));
    const st=JSON.parse(localStorage.getItem('incairn_stats')||'{{}}');
    document.getElementById('w-streak').textContent=
      (st.streak||0)>0?'🔥 '+st.streak+' day streak':'🔥 Keep going!';
    document.getElementById('w-played').textContent=
      (st.played||1)+' puzzle'+((st.played||1)!==1?'s':'')+' solved';
    showScreen('win');
  }},1200);
}}
function showFeedback(){{
  buildFeedback();
  showScreen('feedback-screen');
}}
function onWinPlayAgain(){{
  if(G.mode==='daily') showScreen('difficulty');
  else startPractice(G.board.diff);
}}

// ═══════════════════════════════════════════════════════
// PROGRESS SAVE
// ═══════════════════════════════════════════════════════
function saveProgress(){{
  try{{
    const st=JSON.parse(localStorage.getItem('incairn_stats')||'{{}}');
    st.played=(st.played||0)+1;
    if(!st.bestTime||G.elapsed<st.bestTime)st.bestTime=G.elapsed;
    const yest=new Date(Date.now()-86400000).toISOString().split('T')[0];
    const last=st.lastSolve||'';
    if(last===yest)st.streak=(st.streak||0)+1;
    else if(last!==TODAY_STR)st.streak=1;
    st.lastSolve=TODAY_STR;
    localStorage.setItem('incairn_stats',JSON.stringify(st));
    const solves=JSON.parse(localStorage.getItem('incairn_solves')||'[]');
    solves.push({{date:new Date().toISOString(),bid:G.board.bid,
      difficulty:G.board.diff,time:G.elapsed,moves:G.moves,gen:G.board.gen}});
    if(solves.length>90)solves.splice(0,solves.length-90);
    localStorage.setItem('incairn_solves',JSON.stringify(solves));
  }}catch(e){{}}
}}

// ═══════════════════════════════════════════════════════
// HISTORY
// ═══════════════════════════════════════════════════════
function buildHistory(){{
  try{{
    const st=JSON.parse(localStorage.getItem('incairn_stats')||'{{}}');
    const slv=JSON.parse(localStorage.getItem('incairn_solves')||'[]');
    document.getElementById('hs-p').textContent=st.played||'—';
    document.getElementById('hs-s').textContent=st.streak||'—';
    const b=st.bestTime||0,m=Math.floor(b/60),s=b%60;
    document.getElementById('hs-b').textContent=b>0?(m>0?m+'m '+s+'s':s+'s'):'—';
    const solved=new Set(slv.map(s=>s.date.slice(0,10)));
    if(st.lastSolve===TODAY_STR)solved.add(TODAY_STR);
    const cal=document.getElementById('cal'); cal.innerHTML='';
    for(let i=27;i>=0;i--){{
      const d=new Date(); d.setDate(d.getDate()-i);
      const iso=d.toISOString().split('T')[0];
      const div=document.createElement('div');div.className='cal-day';
      if(solved.has(iso))div.classList.add('solved');
      if(iso===TODAY_STR)div.classList.add('today');
      div.innerHTML='<span class="cal-num">'+d.getDate()+'</span>'+
        (solved.has(iso)?'<span class="cal-dot"></span>':'');
      cal.appendChild(div);
    }}
    const list=document.getElementById('hist-list');
    if(slv.length>0){{
      list.innerHTML='';
      [...slv].reverse().slice(0,20).forEach(sv=>{{
        const row=document.createElement('div');row.className='hist-row';
        const t=sv.time||0,m=Math.floor(t/60),s=t%60;
        const dc=(sv.difficulty||'easy').toLowerCase();
        row.innerHTML='<div><div class="hist-bid">'+(sv.bid||'—').toUpperCase()+
          '</div><div class="hist-date">'+new Date(sv.date).toLocaleDateString('en-GB',
          {{day:'numeric',month:'short',year:'numeric'}})+'</div></div>'+
          '<div class="hist-meta"><span class="hist-time">'+(t>0?(m>0?m+'m '+s+'s':s+'s'):'—')+
          '</span><span class="badge '+dc+'">'+(sv.difficulty||'—')+'</span></div>';
        list.appendChild(row);
      }});
    }}else{{list.innerHTML='<div class="hist-empty">No solves yet. Complete a cairn to begin.</div>';}}
  }}catch(e){{}}
}}

// ═══════════════════════════════════════════════════════
// FEEDBACK
// ═══════════════════════════════════════════════════════
let fbRatings={{diff:0,fun:0}};
function buildFeedback(){{
  fbRatings={{diff:0,fun:0}};
  document.getElementById('fb-bid-label').textContent=
    G.board?G.board.bid.toUpperCase()+' · '+G.board.diff:'—';
  document.querySelectorAll('.star').forEach(s=>s.classList.remove('on'));
  document.getElementById('fb-comments').value='';
}}
document.querySelectorAll('.star').forEach(s=>{{
  s.addEventListener('click',()=>{{
    const g=s.dataset.g,v=parseInt(s.dataset.v);fbRatings[g]=v;
    document.querySelectorAll('.star[data-g="'+g+'"]').forEach(x=>
      x.classList.toggle('on',parseInt(x.dataset.v)<=v));
  }});
  s.addEventListener('mouseover',()=>{{
    const g=s.dataset.g,v=parseInt(s.dataset.v);
    document.querySelectorAll('.star[data-g="'+g+'"]').forEach(x=>
      x.style.opacity=parseInt(x.dataset.v)<=v?'.7':'.3');
  }});
  s.addEventListener('mouseout',()=>{{
    const g=s.dataset.g;
    document.querySelectorAll('.star[data-g="'+g+'"]').forEach(x=>
      x.style.opacity=parseInt(x.dataset.v)<=(fbRatings[g]||0)?'1':'.3');
  }});
}});
function submitFeedback(){{
  const data={{
    board_id:G.board?G.board.bid:'',
    difficulty:G.board?G.board.diff:'',
    time_taken:G.elapsed+'s',
    difficulty_rating:fbRatings.diff,
    fun_rating:fbRatings.fun,
    comments:document.getElementById('fb-comments').value,
    timestamp:new Date().toISOString()
  }};
  // Store feedback locally in localStorage
  try{{
    const fb=JSON.parse(localStorage.getItem('incairn_feedback')||'[]');
    fb.push(data);
    localStorage.setItem('incairn_feedback',JSON.stringify(fb));
  }}catch(e){{}}
  // Also signal Python via postMessage (best-effort)
  try{{window.parent.postMessage({{type:'incairn_feedback',data}},'*');}}catch(e){{}}
  showToast('Thanks for your feedback!','win');
  setTimeout(()=>showScreen('win'), 800);
}}

// ═══════════════════════════════════════════════════════
// TOAST
// ═══════════════════════════════════════════════════════
let toastTimer=null;
function showToast(m,type){{
  const t=document.getElementById('toast');
  t.textContent=m; t.className='toast '+type+' show';
  if(toastTimer)clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>t.classList.remove('show'),3800);
}}

// ═══════════════════════════════════════════════════════
// CONFETTI
// ═══════════════════════════════════════════════════════
function launchConfetti(){{
  const cv=document.getElementById('cv'),ctx=cv.getContext('2d');
  cv.width=window.innerWidth;cv.height=window.innerHeight;
  const cols=['#d4a843','#8b7355','#ece4d6','#7ab06a','#c9a84c','#b09070'];
  const p=Array.from({{length:130}},()=>{{return{{
    x:Math.random()*cv.width,y:Math.random()*cv.height-cv.height,
    r:Math.random()*5+2,d:Math.random()*80+10,
    col:cols[Math.floor(Math.random()*cols.length)],a:0,ts:Math.random()*.07+.04
  }};}});
  let f=0;(function draw(){{
    ctx.clearRect(0,0,cv.width,cv.height);
    p.forEach(q=>{{q.a+=q.ts;const tl=Math.sin(q.a)*10;q.y+=2.6;q.x+=Math.sin(q.a)*.8;
      ctx.beginPath();ctx.lineWidth=q.r/2;ctx.strokeStyle=q.col;
      ctx.moveTo(q.x+tl+q.r/4,q.y);ctx.lineTo(q.x+tl,q.y+tl+q.r/4);ctx.stroke();}});
    if(++f<200)requestAnimationFrame(draw);else ctx.clearRect(0,0,cv.width,cv.height);
  }})();
}}

// ═══════════════════════════════════════════════════════
// TOUCH DRAG
// Handles three drag sources:
//   tray chip  → empty or occupied cell  (place / swap-back + place)
//   cell stone → other cell              (swap)
//   cell stone → tray                   (return to tray)
// ═══════════════════════════════════════════════════════
let tCh=null,tCl=null,tSrc=null; // tSrc: {{t:'tray',id}} or {{t:'cell',idx}}

function tS(e){{
  const ch=e.currentTarget;
  // Tray chip: skip if already placed (hidden)
  if(ch.classList.contains('used'))return;
  tCh=ch;

  // Determine source type
  const parentCell=ch.closest('.cell');
  if(parentCell){{
    // Dragging a stone already placed in the pyramid
    tSrc={{t:'cell',idx:parseInt(parentCell.dataset.i)}};
  }}else{{
    // Dragging from the tray
    tSrc={{t:'tray',id:ch.id}};
  }}

  // Create floating ghost
  const r=ch.getBoundingClientRect();
  tCl=document.createElement('div');
  tCl.className='chip chip-ghost';
  tCl.textContent=ch.textContent.replace('✕','').trim();
  tCl.style.cssText=`width:${{r.width}}px;height:${{r.height}}px;`+
    `left:${{r.left}}px;top:${{r.top}}px;position:fixed;display:flex;`+
    `align-items:center;justify-content:center;font-family:'Georgia',serif;`+
    `font-size:1rem;color:var(--cream);`;
  document.body.appendChild(tCl);
}}

function tM(e){{
  if(!tCl)return;e.preventDefault();const t=e.touches[0];
  tCl.style.left=(t.clientX-27)+'px';tCl.style.top=(t.clientY-27)+'px';
  document.querySelectorAll('.cell').forEach(c=>c.classList.remove('over'));
  tCl.style.display='none';
  const el=document.elementFromPoint(t.clientX,t.clientY);
  tCl.style.display='';
  const cell=el&&el.closest('.cell');
  if(cell)cell.classList.add('over');
}}

function tE(e){{
  if(!tCl||!tCh)return;
  const t=e.changedTouches[0];
  tCl.remove();tCl=null;
  document.querySelectorAll('.cell').forEach(c=>c.classList.remove('over'));

  const el=document.elementFromPoint(t.clientX,t.clientY);
  const targetCell=el&&el.closest('.cell');
  const onTray=el&&el.closest('#tray');

  if(tSrc.t==='tray'){{
    // ── Tray chip dropped onto a pyramid cell ──
    if(targetCell){{
      const ti=parseInt(targetCell.dataset.i);
      if(G.C[ti]!==null)ret(ti);          // bump existing stone back to tray
      place(tSrc.id,G.CS[tSrc.id].v,ti,true);
      clrV();
    }}
    // Drop back on tray or elsewhere → no-op (stays in tray)
  }}else{{
    // ── Cell stone dragged somewhere ──
    const srcIdx=tSrc.idx;
    if(targetCell){{
      const ti=parseInt(targetCell.dataset.i);
      if(ti!==srcIdx){{
        // Swap the two cells (mirrors desktop ondrop cell→cell logic)
        const tmpV=G.C[ti],tmpId=G.CID[ti];
        G.C[ti]=G.C[srcIdx];   G.CID[ti]=G.CID[srcIdx];
        G.C[srcIdx]=tmpV;       G.CID[srcIdx]=tmpId;
        G.moves++;
        document.getElementById('g-mvc').textContent=G.moves;
        renderCells(); updateProg(); clrV();
      }}
    }}else if(onTray){{
      // Dropped back on the tray → return stone
      ret(srcIdx); clrV();
    }}
    // Drop anywhere else → return stone to tray
    else{{ret(srcIdx);clrV();}}
  }}

  tCh=null;tSrc=null;
}}

// ═══════════════════════════════════════════════════════
// BOOT
// ═══════════════════════════════════════════════════════
loadHomeStats();
</script>
</body></html>
"""

# ══════════════════════════════════════════════════════════════
# RENDER — single component, no Streamlit widgets overlapping
# ══════════════════════════════════════════════════════════════
components.html(GAME_HTML, height=900, scrolling=True)

# Invisible feedback saver — listens for postMessage from iframe
# Uses st.components approach: Streamlit itself can't receive postMessage,
# so we save feedback locally if user submits via the win screen rate button.
# The feedback form is fully in-HTML; we just provide a fallback display.
st.markdown("""
<style>div[data-testid="stHorizontalBlock"]{display:none!important}</style>
""", unsafe_allow_html=True)
