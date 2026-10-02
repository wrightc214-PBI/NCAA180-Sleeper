"""
roster_map.py -- dynasty value vs. contender status for all 180 teams.

Writes:
  data/RosterValues_Season.csv  one row per team per run-week (replaced for the current week)
  reports/roster-map.html        interactive page: All 180 (dots, league colors) + one view
                                 per conference (logos). Hover or tap a team for its card.

Axes
  Dynasty value  = sum of FantasyCalc dynasty value for every player on the roster.
  Contender      = blend of market and results, results gaining weight each week:
                     market  = FantasyCalc redraft value of the best legal starting lineup
                     results = points per game, completed regular-season weeks
                     w = min(games, FADE_GAMES) / FADE_GAMES
                     Contender = (1 - w) * z(market) + w * z(results)     (z across all 180)
                   With FADE_GAMES = 6 the market is fully phased out by week 6, matching the
                   commissioner's old preseason-KTC fade.
Draft picks are not valued yet (FantasyCalc values picks, but our pick-ownership file
would need mapping) -- noted as a known gap.

Needs data/PlayerValues_Current.csv (player_values.py); exits cleanly without it.
CWD must be repo root.
"""
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_common import nav_html, page_head  # noqa: E402

ROSTERS = "data/Rosters_Current.csv"
VALUES = "data/PlayerValues_Current.csv"
MATCHUPS = "data/Matchups_Season.csv"
TEAMS = "data/Teams.csv"
LEAGUE_COLORS = "data/Colors - Leagues.csv"
LEAGUES = "data/LeagueIDs_AllYears.csv"
OUT_CSV = "data/RosterValues_Season.csv"
OUT_HTML = "reports/roster-map.html"
LOGO_DIR = "assets/logos/teams"
FADE_GAMES = 6
LAST_REGULAR_WEEK = 11
DEFAULT_SLOTS = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "FLEX"]
ELIGIBLE = {"QB": {"QB"}, "RB": {"RB"}, "WR": {"WR"}, "TE": {"TE"},
            "FLEX": {"RB", "WR", "TE"}, "WRRB_FLEX": {"RB", "WR"},
            "REC_FLEX": {"WR", "TE"}, "SUPER_FLEX": {"QB", "RB", "WR", "TE"}}
LEAGUE_DISPLAY = {
    "NCAA BIG EAST & CO.": "Big East", "NCAA SEC": "SEC", "NCAA PAC 12": "Pac 12",
    "NCAA ACC": "ACC", "NCAA BIG 12": "Big 12", "NCAA SUN BELT": "Sun Belt",
    "NCAA PIONEER": "Pioneer", "NCAA IVY": "Ivy", "NCAA USA": "CUSA",
    "NCAA HISTORICALLY BLACK": "HBCU", "NCAA MOUNTAIN WEST": "Mountain West",
    "NCAA OHIO VALLEY": "Ohio Valley", "NCAA WILD": "Wild", "NCAA BIG 10": "Big 10",
    "NCAA BIG SKY": "Big Sky",
}


def best_lineup(players, slots):
    pool = sorted(players, key=lambda x: -x[0])
    used = [False] * len(pool)
    total = 0.0
    for slot in sorted(slots, key=lambda s: len(ELIGIBLE.get(s, ()))):
        ok = ELIGIBLE.get(slot)
        if not ok:
            continue  # K / DEF / unknown: FantasyCalc doesn't value them
        for i, (v, pos) in enumerate(pool):
            if not used[i] and pos in ok:
                used[i] = True
                total += v
                break
    return total


def zscore(s):
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd else s * 0


def main():
    if not os.path.exists(VALUES):
        print(f"{VALUES} missing (run player_values first); skipping roster map.")
        return
    ro = pd.read_csv(ROSTERS, dtype=str)
    year = ro["Year"].iloc[0]
    ro = ro[ro["Year"] == year]
    pv = pd.read_csv(VALUES, dtype={"SleeperID": str})
    ro = ro.merge(pv[["SleeperID", "DynastyValue", "RedraftValue", "Position"]].rename(
        columns={"SleeperID": "PlayerID", "Position": "VPos"}), on="PlayerID", how="left")
    ro["Pos"] = ro["VPos"].fillna(ro["Position"]).replace({"FB": "RB"})
    ro[["DynastyValue", "RedraftValue"]] = ro[["DynastyValue", "RedraftValue"]].fillna(0)

    slots = {}
    if os.path.exists(LEAGUES):
        lg = pd.read_csv(LEAGUES, dtype=str)
        if "RosterPositions" in lg.columns:
            for r in lg[lg["Year"] == year].itertuples():
                if isinstance(r.RosterPositions, str):
                    slots[r.LeagueID] = [x for x in r.RosterPositions.split(",")
                                         if x not in ("BN", "IR", "TAXI", "K", "DEF")]

    rows = []
    for (lid, lname, rid), g in ro.groupby(["LeagueID", "LeagueName", "RosterID"]):
        rows.append({"LeagueID": lid, "LeagueName": lname, "RosterID": rid,
                     "DynastyTotal": round(g["DynastyValue"].sum()),
                     "LineupRedraft": round(best_lineup(list(zip(g["RedraftValue"], g["Pos"])),
                                                        slots.get(lid, DEFAULT_SLOTS)))})
    t = pd.DataFrame(rows)

    m = pd.read_csv(MATCHUPS, dtype=str)
    m["Week"] = m["Week"].astype(int)
    m["P"] = m["PointsFor"].astype(float)
    reg = m[(m["Week"] <= LAST_REGULAR_WEEK) & m["Outcome"].notna()]
    rec = reg.groupby(["LeagueID", "RosterID"]).agg(
        Owner=("OwnerName", "last"), G=("P", "size"), PPG=("P", "mean"),
        W=("Outcome", lambda x: int((x == "Win").sum())),
        L=("Outcome", lambda x: int((x == "Loss").sum())),
        T=("Outcome", lambda x: int((x == "Tie").sum()))).reset_index()
    t = t.merge(rec, on=["LeagueID", "RosterID"], how="left")
    owners = m.drop_duplicates(["LeagueID", "RosterID"]).set_index(["LeagueID", "RosterID"])["OwnerName"]
    t["Owner"] = t["Owner"].fillna(pd.Series([owners.get(k, "") for k in zip(t.LeagueID, t.RosterID)], index=t.index))
    t[["G", "W", "L", "T"]] = t[["G", "W", "L", "T"]].fillna(0).astype(int)
    games = int(t["G"].max()) if len(t) else 0
    w = min(games, FADE_GAMES) / FADE_GAMES
    t["PPG"] = t["PPG"].fillna(t["PPG"].mean() if games else 0)
    t["Contender"] = (1 - w) * zscore(t["LineupRedraft"]) + (w * zscore(t["PPG"]) if games else 0)
    for c in ("DynastyTotal", "LineupRedraft", "Contender", "PPG"):
        t[c + "Rank"] = t[c].rank(ascending=False, method="min").astype(int)

    tm = pd.read_csv(TEAMS, dtype=str, encoding="utf-8-sig").rename(
        columns={"League": "LeagueName", "Roster ID": "RosterID"})
    t = t.merge(tm[["LeagueName", "RosterID", "Team"]], on=["LeagueName", "RosterID"], how="left")
    t["Team"] = t["Team"].fillna(t["Owner"])
    t["Lg"] = t["LeagueName"].map(LEAGUE_DISPLAY).fillna(t["LeagueName"])

    week = games
    t["Year"], t["Week"], t["ResultsWeight"] = year, week, round(w, 3)
    keep = ["Year", "Week", "LeagueID", "LeagueName", "RosterID", "Team", "Owner", "W", "L", "T",
            "PPG", "DynastyTotal", "LineupRedraft", "Contender", "ResultsWeight"]
    out = t[keep].copy()
    out["PPG"] = out["PPG"].round(2)
    out["Contender"] = out["Contender"].round(3)
    if os.path.exists(OUT_CSV):
        old = pd.read_csv(OUT_CSV, dtype=str)
        old = old[~((old["Year"] == str(year)) & (old["Week"] == str(week)))]
        out = pd.concat([old, out.astype(str)], ignore_index=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"Wrote {OUT_CSV}: week {week}, results weight {w:.2f}")

    lc = pd.read_csv(LEAGUE_COLORS, dtype=str, encoding="utf-8-sig")
    up = {k.upper(): v for k, v in LEAGUE_DISPLAY.items()}
    colors = {}
    for r in lc.itertuples():
        s = up.get(str(r.League).upper())
        if s and isinstance(r.Background, str):
            colors[s] = r.Background if r.Background.startswith("#") else "#" + r.Background

    teams = []
    for r in t.itertuples():
        logo = os.path.exists(os.path.join(LOGO_DIR, f"{r.Team}.png"))
        teams.append({"team": r.Team, "owner": r.Owner, "lg": r.Lg,
                      "rec": f"{r.W}-{r.L}" + (f"-{r.T}" if r.T else ""),
                      "ppg": round(float(r.PPG), 1), "dyn": int(r.DynastyTotal),
                      "red": int(r.LineupRedraft), "con": round(float(r.Contender), 3),
                      "dynR": int(r.DynastyTotalRank), "redR": int(r.LineupRedraftRank),
                      "conR": int(r.ContenderRank), "ppgR": int(r.PPGRank),
                      "logo": f"../{LOGO_DIR}/{r.Team}.png" if logo else None})
    payload = {"teams": teams, "colors": colors, "week": week, "w": round(w, 2),
               "leagues": sorted(set(t["Lg"]))}
    page = page_head("NCAA 180 Roster Map", MAP_CSS) + MAP_BODY.replace(
        "{{NAV}}", nav_html("map")).replace("{{WEEK}}", str(week)).replace(
        "{{WPCT}}", f"{round(w * 100)}").replace(
        "{{DATA}}", json.dumps(payload).replace("</", "<\\/"))
    os.makedirs("reports", exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Wrote {OUT_HTML}")


MAP_CSS = """
.picker{display:flex;flex-wrap:wrap;gap:6px}
.picker button{font:600 13px var(--num);letter-spacing:.04em;padding:5px 10px;border:1px solid var(--line);
 border-radius:3px;background:var(--panel);color:var(--ink);cursor:pointer}
.picker button[aria-pressed=true]{background:var(--ink);color:var(--panel);border-color:var(--ink)}
.picker button:focus-visible,.dot:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.chartwrap{position:relative;width:100%}
svg.map{width:100%;height:auto;display:block;overflow:visible}
.ax{stroke:var(--ink);stroke-width:1.5}.mid{stroke:var(--line);stroke-dasharray:4 4}
.qlab{fill:var(--mute);font:600 11px var(--num);letter-spacing:.12em;text-transform:uppercase}
.axlab{fill:var(--mute);font:600 12px var(--num);letter-spacing:.12em;text-transform:uppercase}
.dot{cursor:pointer}.dot circle{stroke:var(--panel);stroke-width:1.5}
.dot.sel circle,.dot.sel .ring{stroke:var(--accent);stroke-width:3}
.ring{fill:var(--panel);stroke:var(--line);stroke-width:1}
.lsel{display:none;font:600 14px var(--num)}.lsel select{font:600 15px var(--num);padding:6px 8px;margin-left:6px;border:1px solid var(--line);border-radius:3px;background:var(--panel);color:var(--ink)}
@media (max-width:640px){.picker{display:none}.lsel{display:block}}
.tlab{fill:var(--ink);font-weight:600;font-family:var(--body);text-anchor:middle;paint-order:stroke;stroke:var(--panel);stroke-width:3px}
.card{display:grid;grid-template-columns:auto 1fr;gap:4px 16px;align-items:start;min-height:120px}
.card img{width:72px;height:72px;object-fit:contain}
.card h3{margin:0;font:700 22px var(--disp);text-transform:uppercase;letter-spacing:.03em}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px 16px;margin-top:8px}
.stats div b{display:block;font:600 22px var(--num);font-variant-numeric:tabular-nums}
.stats div span{font:600 11px var(--num);letter-spacing:.1em;text-transform:uppercase;color:var(--mute)}
.hint{color:var(--mute);font-size:13px}
"""

MAP_BODY = """
<div class="wrap">
<nav class="weeks" aria-label="Pages">{{NAV}}</nav>
<header>
  <div><div class="eyebrow">15 conferences · 180 teams · after week {{WEEK}}</div><h1>Roster <em>Map</em></h1></div>
</header>
<section>
  <h2>Dynasty value vs. contender <small>Tap a team</small></h2>
  <div class="picker" id="picker" role="group" aria-label="Conference"></div>
  <label class="lsel">Conference <select id="lsel"></select></label>
  <div class="chartwrap"><svg class="map" id="map" viewBox="0 0 800 560" role="img" aria-label="Scatter of dynasty value against contender score"></svg></div>
  <p class="note">Right = more total dynasty value (FantasyCalc, whole roster). Up = stronger contender:
  a blend of the best lineup's redraft value and actual points per game. Results count {{WPCT}}% this week
  and take over fully by week 6. Dashed lines are the NCAA 180 medians. Draft picks aren't counted yet.</p>
</section>
<section id="card" aria-live="polite"><p class="hint">Hover or tap a team to see its numbers.</p></section>
<footer>Values: FantasyCalc (1 QB, 12 teams, PPR). Results: Sleeper, via the NCAA180-Sleeper pipeline.</footer>
</div>
<script>
const D = {{DATA}};
let W = 800, H = 560; const M = {l: 46, r: 24, t: 20, b: 46};
const svg = document.getElementById('map'), NS = 'http://www.w3.org/2000/svg';
const med = a => { const s = [...a].sort((x, y) => x - y), n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };
const mx = med(D.teams.map(t => t.dyn)), my = med(D.teams.map(t => t.con));
let view = 'All 180', sel = null;
try { const v = localStorage.getItem('rm-view'); if (v && (v === 'All 180' || D.leagues.includes(v))) view = v; } catch (e) {}

const picker = document.getElementById('picker'), lsel = document.getElementById('lsel');
['All 180', ...D.leagues].forEach(n => { const o = document.createElement('option'); o.textContent = n; lsel.appendChild(o); });
lsel.onchange = () => { view = lsel.value; sel = null; try { localStorage.setItem('rm-view', view); } catch (e) {} draw(); };
let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(draw, 150); });
['All 180', ...D.leagues].forEach(name => {
  const b = document.createElement('button'); b.type = 'button'; b.textContent = name;
  b.onclick = () => { view = name; sel = null; try { localStorage.setItem('rm-view', name); } catch (e) {} draw(); };
  picker.appendChild(b);
});
function el(tag, attrs, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); (parent || svg).appendChild(e); return e; }
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c])); }
function fmt(n) { return n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n); }

function draw() {
  [...picker.children].forEach(b => b.setAttribute('aria-pressed', b.textContent === view));
  const narrow = svg.parentNode.clientWidth < 600;
  W = narrow ? 400 : 800; H = narrow ? 520 : 560; svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  if (lsel) lsel.value = view;
  svg.textContent = '';
  const all = view === 'All 180', ts = all ? D.teams : D.teams.filter(t => t.lg === view);
  const xs = ts.map(t => t.dyn).concat([mx]), ys = ts.map(t => t.con).concat([my]);
  let x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const px = (x1 - x0) * 0.1 || 1, py = (y1 - y0) * 0.16 || 0.1; x0 -= px; x1 += px; y0 -= py; y1 += py;
  const X = v => M.l + (v - x0) / (x1 - x0) * (W - M.l - M.r), Y = v => H - M.b - (v - y0) / (y1 - y0) * (H - M.t - M.b);
  el('line', {x1: X(mx), x2: X(mx), y1: M.t, y2: H - M.b, class: 'mid'});
  el('line', {x1: M.l, x2: W - M.r, y1: Y(my), y2: Y(my), class: 'mid'});
  el('line', {x1: M.l, x2: M.l, y1: M.t, y2: H - M.b, class: 'ax'});
  el('line', {x1: M.l, x2: W - M.r, y1: H - M.b, y2: H - M.b, class: 'ax'});
  const q = (x, y, t, a) => { const e = el('text', {x, y, class: 'qlab', 'text-anchor': a}); e.textContent = t; };
  q(W - M.r - 4, M.t + 14, 'Loaded', 'end'); q(M.l + 8, M.t + 14, 'Win now', 'start');
  q(W - M.r - 4, H - M.b - 8, 'Building', 'end'); q(M.l + 8, H - M.b - 8, 'Rebuild', 'start');
  const xl = el('text', {x: (M.l + W - M.r) / 2, y: H - 12, class: 'axlab', 'text-anchor': 'middle'}); xl.textContent = 'Dynasty value →';
  const yl = el('text', {x: 14, y: (M.t + H - M.b) / 2, class: 'axlab', 'text-anchor': 'middle', transform: `rotate(-90 14 ${(M.t + H - M.b) / 2})`}); yl.textContent = 'Contender →';
  const r = all ? (narrow ? 4.5 : 6) : (narrow ? 15 : 22);
  ts.slice().sort((a, b) => (a === sel) - (b === sel)).forEach(t => {
    const g = el('g', {class: 'dot' + (t === sel ? ' sel' : ''), tabindex: 0, role: 'button', 'aria-label': `${t.team}, ${t.owner}`});
    const cx = X(t.dyn), cy = Y(t.con);
    if (!all && t.logo) {
      el('circle', {cx, cy, r: r + 3, class: 'ring'}, g);
      el('image', {href: encodeURI(t.logo), x: cx - r, y: cy - r, width: r * 2, height: r * 2, preserveAspectRatio: 'xMidYMid meet'}, g);
    } else {
      el('circle', {cx, cy, r: all ? r : 10, fill: D.colors[t.lg] || '#888'}, g);
    }
    if (!all) { const lb = el('text', {x: cx, y: cy + r + (narrow ? 12 : 15), class: 'tlab', 'font-size': narrow ? 9 : 11}, g); lb.textContent = t.team; }
    const pick = () => { sel = t; show(t); draw(); };
    g.addEventListener('mouseenter', () => show(t));
    g.addEventListener('click', pick);
    g.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); } });
  });
  if (sel && ts.includes(sel)) show(sel);
}
function show(t) {
  const c = document.getElementById('card');
  c.innerHTML = `<div class="card">${t.logo ? `<img src="${encodeURI(t.logo)}" alt="">` : '<span></span>'}
  <div><h3>${esc(t.team)}</h3><div class="hint">${esc(t.owner)} · ${esc(t.lg)} · ${esc(t.rec)}</div>
  <div class="stats">
   <div><b>${fmt(t.dyn)}</b><span>Dynasty value · #${t.dynR}</span></div>
   <div><b>${fmt(t.red)}</b><span>Best lineup (redraft) · #${t.redR}</span></div>
   <div><b>${t.ppg}</b><span>Points per game · #${t.ppgR}</span></div>
   <div><b>#${t.conR}</b><span>Contender rank of 180</span></div>
  </div></div></div>`;
}
draw();
</script>
</body></html>
"""

if __name__ == "__main__":
    main()
