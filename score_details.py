import pandas as pd
import requests
import datetime
import os

# -------------------------
# CONFIG
# -------------------------
CURRENT_YEAR = datetime.datetime.now().year
CSV_PATH = "scores.csv"
LEAGUE_FILE = "data/LeagueIDs_AllYears.csv"
PLAYERS_FILE = "data/Players.csv"

# -------------------------
# LOAD PLAYERS DATA
# -------------------------
if not os.path.exists(PLAYERS_FILE):
    raise FileNotFoundError(f"Missing Players file: {PLAYERS_FILE}")

players_df = pd.read_csv(PLAYERS_FILE, dtype=str)

# Create 'label' column: first_name last_name, position (team)
players_df["label"] = (
    players_df["first_name"].fillna("") + " " +
    players_df["last_name"].fillna("") + ", " +
    players_df["position"].fillna("") + " (" +
    players_df["team"].fillna("") + ")"
)

# Build lookup dictionary for fast access
player_label_map = pd.Series(players_df.label.values, index=players_df.player_id).to_dict()

# -------------------------
# LOAD LEAGUE IDs
# -------------------------
if not os.path.exists(LEAGUE_FILE):
    raise FileNotFoundError(f"Missing LeagueID file: {LEAGUE_FILE}")

league_df = pd.read_csv(LEAGUE_FILE, dtype=str)
current_year_league_ids = league_df.loc[league_df["Year"].astype(int) == CURRENT_YEAR, "LeagueID"].tolist()

if not current_year_league_ids:
    raise ValueError(f"No LeagueIDs found for current year {CURRENT_YEAR}")

print(f"Found {len(current_year_league_ids)} leagues for {CURRENT_YEAR}")

# -------------------------
# LOAD EXISTING CSV
# -------------------------
if os.path.exists(CSV_PATH):
    existing_df = pd.read_csv(CSV_PATH, dtype=str)
else:
    existing_df = pd.DataFrame()

# -------------------------
# FUNCTION TO FETCH SCORES
# -------------------------
def get_weekly_scores(league_id):
    """Fetch matchup data from Sleeper API for all weeks in a league."""
    results = []
    for week in range(1, 19):  # typical fantasy season weeks 1–18
        url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"⚠️ Skipping week {week} for league {league_id} — {resp.status_code}")
            continue

        matchups = resp.json()
        if not matchups:
            continue

        for matchup in matchups:
            roster_id = matchup.get("roster_id", "")
            starters = matchup.get("starters", []) or []
            starters_points = matchup.get("starters_points", []) or []
            lookup_id = f"{league_id}{week}{roster_id}"

            # Determine max length to handle mismatched arrays safely
            length = max(len(starters), len(starters_points))
            for i in range(length):
                player_id = str(starters[i]) if i < len(starters) else ""
                points = starters_points[i] if i < len(starters_points) else ""

                results.append({
                    "LeagueYear": CURRENT_YEAR,
                    "league_id": league_id,
                    "weekNum": week,
                    "roster_id": roster_id,
                    "lookupID": lookup_id,
                    "starter": player_id,
                    "starter_points": points,
                    "array_index": i + 1,  # 1-based
                    "label": player_label_map.get(player_id, "")
                })
    return results

# -------------------------
# FETCH AND COMBINE DATA
# -------------------------
new_data = []
for league_id in current_year_league_ids:
    print(f"Fetching scores for {league_id} ({CURRENT_YEAR})")
    new_data.extend(get_weekly_scores(league_id))

new_df = pd.DataFrame(new_data)

# Keep past-year data and replace current-year data
if not existing_df.empty:
    old_df = existing_df[existing_df["LeagueYear"].astype(int) < CURRENT_YEAR]
else:
    old_df = pd.DataFrame()

combined_df = pd.concat([old_df, new_df], ignore_index=True)

# -------------------------
# SAVE CLEAN CSV
# -------------------------
combined_df.to_csv(CSV_PATH, index=False)
print(f"✅ Saved {CSV_PATH} — replaced {CURRENT_YEAR} data, kept prior years.")
print(f"Total rows now: {len(combined_df)}")
