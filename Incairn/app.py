"""
app.py — Incairn  (Streamlit Frontend)
========================================
The entire game UI lives in one components.html call.
JavaScript handles all screen navigation (show/hide divs).

All game data and logic now go through the FastAPI backend (api.py).
This file is responsible for:
  - Rendering the HTML/CSS/JS shell
  - Injecting the API base URL into the JS
  - Injecting today's date label (cosmetic only)
  - Injecting the logo

Run frontend:  streamlit run app.py
Run backend:   uvicorn api:app --reload
"""
import base64
from pathlib import Path
from datetime import date
import streamlit as st
import streamlit.components.v1 as components

BASE_DIR = Path(__file__).parent

st.set_page_config(
    page_title="Incairn · Daily Cairn",
    page_icon="🗿",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── API base URL ──────────────────────────────────────────────
# Change to your deployed API URL when hosting on Streamlit Cloud.
# e.g. "https://your-api.railway.app"
API_URL = "http://127.0.0.1:8000"

# ── Cosmetic helpers (frontend-only — no game logic here) ─────
def today_label():
    return date.today().strftime("%A, %d %B %Y").upper()

today_js = today_label()

# Strip ALL Streamlit chrome — the HTML component IS the entire UI
st.markdown("""
<style>
  #MainMenu,footer,header{visibility:hidden}
  .block-container{padding:0!important;max-width:100%!important;margin:0!important;}
  section[data-testid="stSidebar"]{display:none}
  iframe{border:none!important;display:block!important}
  div[data-testid="stVerticalBlock"]{gap:0!important}
</style>
""", unsafe_allow_html=True)

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

# ══════════════════════════════════════════════════════════════
# THE ENTIRE GAME — one HTML component, JS-driven screens
# ══════════════════════════════════════════════════════════════
GAME_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/><style>
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
      <div class="stat-lbl">Best</div>
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
.cell.locked{
  border-color:var(--goldD)!important;border-style:solid!important;
  background:radial-gradient(ellipse at 30% 30%,#2c2410,#1e1808)!important;
  color:var(--gold)!important;cursor:default!important;
  box-shadow:0 0 10px rgba(160,120,48,.3)!important
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
.btn-giveup{
  width:100%;max-width:520px;
  background:transparent;color:var(--muted);
  border:1px solid var(--border);border-radius:24px;
  padding:10px;font-size:.68rem;cursor:pointer;
  font-family:'Georgia',serif;letter-spacing:.1em;
  text-transform:uppercase;transition:color .15s,border-color .15s
}
.btn-giveup:hover{color:#c07050;border-color:var(--wrongB)}

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
  <div class="g-stat"><div class="g-sv" id="g-att">0</div><div class="g-sl">attempts</div></div>
  <div class="g-title" id="g-mode-label">Incairn</div>
  <div class="g-stat"><div class="g-sv" id="g-rev">0</div><div class="g-sl">reveals</div></div>
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
  <button class="btn-hint" id="revbtn" onclick="doReveal()">� Reveal (5)</button>
  <button class="btn-check" onclick="doCheck()">Check the Cairn</button>
  <button class="btn-reset" onclick="doReset()">↺</button>
</div>
<div class="act-row" style="margin-top:0">
  <button class="btn-giveup" id="giveupbtn" onclick="doGiveUp()" style="display:none">Give Up</button>
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
  <div class="wsc"><div class="wsv" id="w-att">—</div><div class="wsl">Attempts</div></div>
  <div class="wsc">
    <div class="wsv" id="w-bid" style="font-size:.85rem;letter-spacing:.08em">—</div>
    <div class="wsl">Board</div>
  </div>
  <div class="wsc"><div class="wsv" id="w-rev">—</div><div class="wsl">Reveals</div></div>
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
// CONFIG  — injected by Python
// ═══════════════════════════════════════════════════════
const API_BASE  = "{API_URL}";
const TODAY_STR = new Date().toISOString().split('T')[0];
const TR=[[0,1,2],[1,3,4],[2,4,5],[3,6,7],[4,7,8],[5,8,9]];
const ROWS=[[0],[1,2],[3,4,5],[6,7,8,9]];

// ═══════════════════════════════════════════════════════
// API HELPERS
// ═══════════════════════════════════════════════════════
async function apiPost(path, body) {{
  const res = await fetch(API_BASE + path, {{
    method:'POST', headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify(body)
  }});
  if(!res.ok) {{ const e=await res.json().catch(()=>({{}})); throw new Error(e.detail||'API error '+res.status); }}
  return res.json();
}}
async function apiGet(path, params={{}}) {{
  const qs=new URLSearchParams(params).toString();
  const res=await fetch(API_BASE+path+(qs?'?'+qs:''));
  if(!res.ok) {{ const e=await res.json().catch(()=>({{}})); throw new Error(e.detail||'API error '+res.status); }}
  return res.json();
}}

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
    const s   = JSON.parse(localStorage.getItem('incairn_stats')||'{{}}');
    const slv = JSON.parse(localStorage.getItem('incairn_solves')||'[]');
    document.getElementById('st-played').textContent = s.played||'—';
    document.getElementById('st-streak').textContent = s.streak||'—';
    document.getElementById('h-streak').textContent =
      (s.streak||0)>0?'🔥 '+s.streak+' day streak':'🔥 Start your streak';
    // Best = fewest attempts across all solves
    const best = slv.length
      ? Math.min(...slv.map(sv=>sv.attempts||Infinity).filter(v=>isFinite(v)))
      : 0;
    document.getElementById('st-best').textContent =
      best>0?best+' attempt'+(best!==1?'s':''):'—';
    document.getElementById('h-pnum').textContent = 'Daily Cairn';
  }} catch(e) {{}}
}}

// ═══════════════════════════════════════════════════════
// GAME STATE
// ═══════════════════════════════════════════════════════
// REVEAL_SEQ: fixed order of cell indices to reveal
const REVEAL_SEQ = [4, [0,6,9], 1, 7, 8];

let G = {{
  board:null, mode:'daily', sessionToken:null,
  C:Array(10).fill(null), CID:{{}}, CS:{{}},
  drag:null, attempts:0, solved:false,
  revealsUsed:0,          // how many Reveal steps used (0-5)
  lockedCells:new Set(),  // cell indices locked by reveals
  cachedSolution:null     // fetched once, reused for all reveals
}};

// ── Load board from API then launch ──────────────────
async function startDailyGame() {{
  showScreen('game');
  showToast("Loading today's cairn…",'info');
  try {{
    const tzOffset = new Date().getTimezoneOffset();
    const data = await apiPost('/incairn/load', {{mode:'daily', tz_offset:tzOffset}});
    _launchGame(data, 'daily');
  }} catch(e) {{ showToast('Could not load board: '+e.message,'err'); }}
}}
async function startPractice(diff) {{
  showScreen('game');
  showToast('Loading '+diff+' board…','info');
  try {{
    const data = await apiPost('/incairn/load', {{mode:'practice', difficulty:diff}});
    _launchGame(data, 'practice');
  }} catch(e) {{ showToast('Could not load board: '+e.message,'err'); }}
}}
async function startPastGame(dateStr) {{
  showScreen('game');
  showToast('Loading cairn for '+dateStr+'…','info');
  try {{
    const data = await apiPost('/incairn/load', {{mode:'past', date:dateStr}});
    _launchGame(data, 'past');
  }} catch(e) {{ showToast('Could not load board: '+e.message,'err'); }}
}}

function _launchGame(data, mode) {{
  const board = {{
    board_id: data.board_id,
    bid:      data.bid,
    diff:     data.difficulty,
    gen:      data.generation,
    rel:      data.relationship,
    puz:      data.numbers,
  }};
  G.board=board; G.mode=mode; G.sessionToken=data.session_token;
  G.C=Array(10).fill(null); G.CID={{}}; G.CS={{}};
  G.drag=null; G.attempts=0; G.solved=false;
  G.revealsUsed=0; G.lockedCells=new Set(); G.cachedSolution=null;

  document.getElementById('g-bid').textContent=board.bid.toUpperCase();
  const dc=board.diff.toLowerCase();
  const badge=document.getElementById('g-diff-badge');
  badge.textContent=board.diff; badge.className='badge '+dc;
  document.getElementById('g-mode-label').textContent =
    mode==='daily'?"Today's Cairn": mode==='past'?"Past Cairn":"Practice · "+board.diff;
  document.getElementById('g-att').textContent='0';
  document.getElementById('g-rev').textContent='0';
  document.getElementById('g-placed').textContent='0 / 10 placed';
  document.getElementById('g-prog').style.width='0%';
  document.getElementById('revbtn').textContent='� Reveal (5)';
  document.getElementById('revbtn').disabled=false;
  document.getElementById('giveupbtn').style.display='none';
  const diffColors={{easy:'#7ab06a',medium:'#d4a843',hard:'#c08860'}};
  const diffBg={{easy:'#1a2a14',medium:'#2a2210',hard:'#2a1e14'}};
  const diffBdr={{easy:'#3a6028',medium:'#6a5218',hard:'#6a3818'}};
  const pill=document.getElementById('daily-diff-pill');
  if(pill&&mode==='daily'){{
    pill.textContent=board.diff;
    pill.style.background=diffBg[dc];
    pill.style.color=diffColors[dc];
    pill.style.border='1px solid '+diffBdr[dc];
  }}
  initTray(); renderCells(); showScreen('game');
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
    if(G.drag&&G.drag.t==='cell'){{ret(G.drag.idx);G.drag=null;}}}};
}}

function onDrop(e){{
  e.preventDefault(); const el=e.currentTarget; el.classList.remove('over');
  const ti=parseInt(el.dataset.i); if(!G.drag)return;
  if(G.lockedCells.has(ti)){{G.drag=null;return;}} // can't drop onto a locked cell
  if(G.drag.t==='tray'){{
    if(G.C[ti]!==null)ret(ti); place(G.drag.id,G.CS[G.drag.id].v,ti,true);
  }} else if(G.drag.t==='cell'&&G.drag.idx!==ti){{
    if(G.lockedCells.has(G.drag.idx)){{G.drag=null;return;}} // can't drag a locked cell
    [G.C[ti],G.C[G.drag.idx]]=[G.C[G.drag.idx],G.C[ti]];
    [G.CID[ti],G.CID[G.drag.idx]]=[G.CID[G.drag.idx],G.CID[ti]];
    renderCells(); updateProg();
  }}
  G.drag=null;
}}

function place(id,v,i,anim){{
  G.C[i]=v; G.CS[id].placed=true; G.CID[i]=id;
  document.getElementById(id).classList.add('used');
  renderCells();
  if(anim){{const el=document.querySelector('.cell[data-i="'+i+'"]');
    if(el){{el.classList.add('snap');el.addEventListener('animationend',()=>el.classList.remove('snap'),{{once:true}});}};
  }}
  updateProg(); checkRowFlash(i);
}}
function ret(i){{
  if(G.lockedCells.has(i))return; // locked by reveal — cannot be moved
  const id=G.CID[i]; G.C[i]=null; delete G.CID[i];
  if(id){{G.CS[id].placed=false;const c=document.getElementById(id);if(c)c.classList.remove('used');}}
  renderCells(); updateProg();
}}
function rmCell(i){{ret(i);}}
function renderCells(){{
  document.querySelectorAll('.cell').forEach(el=>{{
    const i=parseInt(el.dataset.i),v=G.C[i];
    const locked=G.lockedCells.has(i);
    el.textContent=''; el.classList.remove('full','ok','bad','hint','locked');
    if(v!==null){{
      el.textContent=v; el.classList.add('full');
      if(locked){{
        el.classList.add('locked');
        el.draggable=false; el.ondragstart=null;
        el.ontouchstart=null; el.ontouchmove=null; el.ontouchend=null;
      }}else{{
        el.draggable=true;
        el.ondragstart=e=>{{G.drag={{t:'cell',idx:i}};e.dataTransfer.effectAllowed='move';}};
        const rm=document.createElement('button');rm.className='rm';rm.textContent='✕';
        rm.onclick=()=>rmCell(i); el.appendChild(rm);
        el.ontouchstart=tS; el.ontouchmove=tM; el.ontouchend=tE;
      }}
    }}else{{
      el.draggable=false; el.ondragstart=null;
      el.ontouchstart=null; el.ontouchmove=null; el.ontouchend=null;
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
  // Return only unlocked cells to the tray
  for(let i=0;i<10;i++){{
    if(!G.lockedCells.has(i)&&G.C[i]!==null){{
      const id=G.CID[i]; G.C[i]=null; delete G.CID[i];
      if(id){{G.CS[id].placed=false;const c=document.getElementById(id);if(c)c.classList.remove('used','dragging');}}
    }}
  }}
  renderCells(); updateProg();
}}

// ── Reveal  (fetches solution once, reveals stones in fixed order) ───
async function doReveal(){{
  if(G.solved||G.revealsUsed>=5)return;
  // Fetch solution once and cache it
  if(!G.cachedSolution){{
    try{{
      const ans=await apiGet('/incairn/answer',{{board_id:G.board.board_id}});
      G.cachedSolution=ans.solution;
    }}catch(e){{showToast('Reveal unavailable: '+e.message,'err');return;}}
  }}
  const sol=G.cachedSolution;
  // Reveal the next step in the sequence
  const step=REVEAL_SEQ[G.revealsUsed]; // number or array
  const indices=Array.isArray(step)?step:[step];
  indices.forEach(ci=>{{
    // If a non-locked stone is in this cell, return it to the tray first
    if(G.C[ci]!==null&&!G.lockedCells.has(ci))ret(ci);
    // Find a tray chip matching the solution value that isn't already placed/locked
    const need=sol[ci];
    const chip=Object.entries(G.CS).find(([id,cs])=>cs.v===need&&!cs.placed);
    if(chip){{
      G.CS[chip[0]].placed=true;
      G.C[ci]=need;
      G.CID[ci]=chip[0];
      const c=document.getElementById(chip[0]);if(c)c.classList.add('used');
    }}
    G.lockedCells.add(ci);
  }});
  G.revealsUsed++;
  document.getElementById('g-rev').textContent=G.revealsUsed;
  const remaining=5-G.revealsUsed;
  document.getElementById('revbtn').textContent=
    remaining>0?'👁 Reveal ('+remaining+')':'👁 Revealed';
  if(remaining===0)document.getElementById('revbtn').disabled=true;
  // Show Give Up after all 5 reveals
  if(G.revealsUsed===5)document.getElementById('giveupbtn').style.display='';
  renderCells(); updateProg();
  showToast('Stone'+(indices.length>1?'s':'')+' revealed','info');
}}

// ── Give Up — reveal full solution without winning ───────────
async function doGiveUp(){{
  if(G.solved)return;
  if(!G.cachedSolution){{
    try{{
      const ans=await apiGet('/incairn/answer',{{board_id:G.board.board_id}});
      G.cachedSolution=ans.solution;
    }}catch(e){{showToast('Could not retrieve solution: '+e.message,'err');return;}}
  }}
  const sol=G.cachedSolution;
  // Fill every cell from the solution, locking all
  for(let ci=0;ci<10;ci++){{
    if(G.C[ci]!==null&&!G.lockedCells.has(ci))ret(ci);
    const need=sol[ci];
    const chip=Object.entries(G.CS).find(([id,cs])=>cs.v===need&&!cs.placed);
    if(chip){{
      G.CS[chip[0]].placed=true;
      G.C[ci]=need;
      G.CID[ci]=chip[0];
      const c=document.getElementById(chip[0]);if(c)c.classList.add('used');
    }}
    G.lockedCells.add(ci);
  }}
  G.solved=true;
  document.getElementById('revbtn').disabled=true;
  document.getElementById('giveupbtn').style.display='none';
  renderCells(); updateProg();
  showToast('The cairn is revealed — better luck next time','info');
}}

// ── Check solution  (API) ────────────────────────────
async function doCheck(){{
  if(G.solved)return;
  const vals=Array.from({{length:10}},(_,i)=>G.C[i]);
  if(vals.some(v=>v===null)){{showToast('Place all ten stones first','info');return;}}
  G.attempts++;
  document.getElementById('g-att').textContent=G.attempts;
  try {{
    const data = await apiPost('/incairn/check', {{
      board_id:        G.board.board_id,
      player_solution: vals,
      session_token:   G.sessionToken
    }});
    if(data.correct){{
      G.solved=true;
      document.getElementById('revbtn').disabled=true;
      document.getElementById('giveupbtn').style.display='none';
      setTimeout(()=>{{
        showToast('The cairn is complete ◈','win');
        launchConfetti(); saveProgress(); showWin();
      }},120);
    }} else {{
      showToast('Not quite — rearrange the stones','err');
    }}
  }} catch(e) {{
    showToast('Check failed: '+e.message,'err');
  }}
}}
// ═══════════════════════════════════════════════════════
// WIN
// ═══════════════════════════════════════════════════════
function showWin(){{
  setTimeout(()=>{{
    const b=G.board;
    document.getElementById('w-att').textContent=
      G.attempts+' attempt'+(G.attempts!==1?'s':'');
    document.getElementById('w-rev').textContent=
      G.revealsUsed+' reveal'+(G.revealsUsed!==1?'s':'');
    document.getElementById('w-bid').textContent=b.bid.toUpperCase();
    document.getElementById('w-rule').textContent='Parent = '+b.rel;
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
// PROGRESS SAVE  (localStorage — client-side only)
// ═══════════════════════════════════════════════════════
function saveProgress(){{
  try{{
    const st=JSON.parse(localStorage.getItem('incairn_stats')||'{{}}');
    st.played=(st.played||0)+1;
    const yest=new Date(Date.now()-86400000).toISOString().split('T')[0];
    const last=st.lastSolve||'';
    if(last===yest)st.streak=(st.streak||0)+1;
    else if(last!==TODAY_STR)st.streak=1;
    st.lastSolve=TODAY_STR;
    localStorage.setItem('incairn_stats',JSON.stringify(st));
    const solves=JSON.parse(localStorage.getItem('incairn_solves')||'[]');
    solves.push({{
      date:     new Date().toISOString(),
      bid:      G.board.bid,
      difficulty: G.board.diff,
      attempts: G.attempts,
      reveals:  G.revealsUsed,
      gen:      G.board.gen
    }});
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
    const best=slv.length
      ?Math.min(...slv.map(sv=>sv.attempts||Infinity).filter(v=>isFinite(v)))
      :0;
    document.getElementById('hs-b').textContent=
      best>0?best+' attempt'+(best!==1?'s':''):'—';
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
        const dc=(sv.difficulty||'easy').toLowerCase();
        const att=sv.attempts!=null?sv.attempts:'—';
        const rev=sv.reveals!=null?sv.reveals:'—';
        row.innerHTML='<div><div class="hist-bid">'+(sv.bid||'—').toUpperCase()+
          '</div><div class="hist-date">'+new Date(sv.date).toLocaleDateString('en-GB',
          {{day:'numeric',month:'short',year:'numeric'}})+'</div></div>'+
          '<div class="hist-meta">'+
          '<span class="hist-time">'+att+' att · '+rev+' rev</span>'+
          '<span class="badge '+dc+'">'+(sv.difficulty||'—')+'</span></div>';
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
async function submitFeedback(){{
  const data={{
    board_id: G.board?G.board.board_id:'',
    rating:   fbRatings.diff||fbRatings.fun||null,
    comment:  document.getElementById('fb-comments').value
  }};
  try {{
    await apiPost('/incairn/feedback', data);
  }} catch(e) {{
    // best-effort — don't block the player
    console.warn('Feedback save failed:', e.message);
  }}
  // Also keep a local copy
  try{{
    const fb=JSON.parse(localStorage.getItem('incairn_feedback')||'[]');
    fb.push({{...data, timestamp:new Date().toISOString()}});
    localStorage.setItem('incairn_feedback',JSON.stringify(fb));
  }}catch(_){{}}
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
      if(G.lockedCells.has(ti)){{tCh=null;tSrc=null;return;}}
      if(G.C[ti]!==null)ret(ti);          // bump existing stone back to tray
      place(tSrc.id,G.CS[tSrc.id].v,ti,true);
    }}
    // Drop back on tray or elsewhere → no-op (stays in tray)
  }}else{{
    // ── Cell stone dragged somewhere ──
    const srcIdx=tSrc.idx;
    if(G.lockedCells.has(srcIdx)){{tCh=null;tSrc=null;return;}} // locked — can't move
    if(targetCell){{
      const ti=parseInt(targetCell.dataset.i);
      if(ti!==srcIdx&&!G.lockedCells.has(ti)){{
        // Swap the two cells
        const tmpV=G.C[ti],tmpId=G.CID[ti];
        G.C[ti]=G.C[srcIdx];   G.CID[ti]=G.CID[srcIdx];
        G.C[srcIdx]=tmpV;       G.CID[srcIdx]=tmpId;
        renderCells(); updateProg();
      }}
    }}else if(onTray){{
      // Dropped back on the tray → return stone
      ret(srcIdx);
    }}
    // Drop anywhere else → return stone to tray
    else{{ret(srcIdx);}}
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
