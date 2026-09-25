import pandas as pd
import requests
import time
import datetime

# -------------------------
# CONFIG
# -------------------------
LEAGUE_FILE = "data/LeagueIDs_AllYears.csv"
PLAYERS_FILE = "data/Players.csv"
OUT_FILE = "data/Scores_Historic.csv"

today = datetime.date.today()
CURRENT_YEAR = today.year - 1 if today.month < 3 else today.year

# -------------------------
# LOAD PLAYERS DATA (for labels)
# -------------------------
players_df = pd.read_csv(PLAYERS_FILE, dtype=str)
players_df["label"] = (
    players_df["first_name"].fillna("") + " " +
    players_df["last_name"].fillna("") + ", " +
    players_df["position"].fillna("") + " (" +
    players_df["team"].fillna("") + ")"
)
player_label_map = pd.Series(players_df.label.values, index=players_df.player_id).to_dict()

# -------------------------
# LOAD LEAGUE IDs (historic years only — kept as text throughout, never touches a numeric dtype)
# -------------------------
league_df = pd.read_csv(LEAGUE_FILE, dtype=str)
league_df["Year"] = league_df["Year"].astype(int)
historic_df = league_df[league_df["Year"] < CURRENT_YEAR]

# -------------------------
# FETCH SCORES FOR ONE LEAGUE/YEAR
# -------------------------
def get_weekly_scores(league_id, league_year):
    results = []
    for week_num in range(1, 19):
        url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week_num}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"  Warning: {league_id} week {week_num} - {e}")
            continue

        matchups = resp.json() or []
        if not matchups:
            continue

        for matchup in matchups:
            roster_id = matchup.get("roster_id", "")
            starters = matchup.get("starters", []) or []
            starters_points = matchup.get("starters_points", []) or []
            player_points = matchup.get("players_points", {}) or {}
            lookup_id = f"{league_id}{roster_id}"

            for i, player_id in enumerate(starters):
                points = player_points.get(str(player_id))
                if points is None and i < len(starters_points):
                    points = starters_points[i]
                points = float(points) if points not in (None, "", "null") else 0.0

                results.append({
                    "LeagueYear": league_year,
                    "league_id": league_id,
                    "weekNum": week_num,
                    "roster_id": roster_id,
                    "lookupID": lookup_id,
                    "starter": str(player_id),
                    "starter_points": points,
                    "array_index": i + 1,
                    "label": player_label_map.get(str(player_id), "")
                })
        time.sleep(0.3)
    return results

# -------------------------
# LOOP OVER ALL HISTORIC LEAGUE/YEARS
# -------------------------
all_data = []
for idx, row in historic_df.iterrows():
    league_id = row["LeagueID"]
    year = int(row["Year"])
    league_name = row["LeagueName"]
    print(f"Fetching {league_name} ({year})")
    scores = get_weekly_scores(league_id, year)
    print(f"  -> {len(scores)} rows")
    all_data.extend(scores)

df = pd.DataFrame(all_data)
df.to_csv(OUT_FILE, index=False)
print(f"Saved {len(df)} rows to {OUT_FILE}")
