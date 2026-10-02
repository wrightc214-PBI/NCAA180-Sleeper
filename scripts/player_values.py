"""
player_values.py -- dynasty + redraft player values from FantasyCalc (free public API).

One request returns every valued player with both numbers, keyed to Sleeper player IDs.
Settings match NCAA 180: 1 QB, 12 teams, full PPR. Kickers/DEF are not valued.

Writes:
  data/PlayerValues_Current.csv  overwritten each run
  data/PlayerValues_Season.csv   one snapshot per NFL week (first run of that week wins,
                                 so the snapshot is the start-of-week market). This is the
                                 only history: past values cannot be fetched later.
Columns: Date, Week, SleeperID, Name, Position, NFLTeam, DynastyValue, RedraftValue

On a failed request, existing files are left untouched (exit 1 so the run flags it).
CWD must be repo root.
"""
import datetime
import os
import sys

import pandas as pd
import requests

URL = "https://api.fantasycalc.com/values/current"
PARAMS = {"isDynasty": "true", "numQbs": 1, "numTeams": 12, "ppr": 1}
CURRENT = "data/PlayerValues_Current.csv"
SEASON = "data/PlayerValues_Season.csv"
MATCHUPS = "data/Matchups_Season.csv"


def current_week():
    """First week without final results = the week in progress / about to start."""
    m = pd.read_csv(MATCHUPS, dtype=str)
    done = m.groupby(m["Week"].astype(int))["Outcome"].apply(lambda s: s.notna().all())
    pending = [w for w, ok in done.items() if not ok]
    return min(pending) if pending else max(done.index)


def main():
    try:
        r = requests.get(URL, params=PARAMS, timeout=30,
                         headers={"User-Agent": "NCAA180-Sleeper/1.0"})
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"ERROR fetching FantasyCalc values: {e}")
        sys.exit(1)

    today = datetime.date.today().isoformat()
    week = current_week()
    rows = []
    for d in data:
        p = d.get("player") or {}
        sid = p.get("sleeperId")
        if not sid:
            continue
        rows.append({"Date": today, "Week": week, "SleeperID": str(sid),
                     "Name": p.get("name", ""), "Position": p.get("position", ""),
                     "NFLTeam": p.get("maybeTeam") or "",
                     "DynastyValue": d.get("value", 0) or 0,
                     "RedraftValue": d.get("redraftValue", 0) or 0})
    if len(rows) < 100:
        print(f"ERROR: only {len(rows)} valued players returned; not overwriting files")
        sys.exit(1)
    cur = pd.DataFrame(rows)
    cur.to_csv(CURRENT, index=False)
    print(f"Wrote {CURRENT}: {len(cur)} players (week {week})")

    if os.path.exists(SEASON):
        hist = pd.read_csv(SEASON, dtype={"SleeperID": str})
        if (hist["Week"].astype(int) == week).any():
            print(f"Week {week} snapshot already saved; {SEASON} unchanged")
            return
        hist = pd.concat([hist, cur], ignore_index=True)
    else:
        hist = cur
    hist.to_csv(SEASON, index=False)
    print(f"Saved week {week} snapshot to {SEASON}")


if __name__ == "__main__":
    main()
