import pandas as pd
import requests
import datetime
import os

# -------------------------
# CONFIG
# -------------------------
CSV_PATH = "data/Scores.csv"
LEAGUE_FILE = "data/LeagueIDs_AllYears.csv"
PLAYERS_FILE = "data/Players.csv"

# -------------------------
# DETERMINE CURRENT NFL YEAR (adjust for Jan/Feb rollover)
# -------------------------
today = datetime.date.today()
CURRENT_YEAR = today.year - 1 if today.month < 3 else today.year
print(f"🏈 Current NFL Year: {CURRENT_YEAR}")

# -------------------------
# LOAD PLAYERS DATA
# -------------------------
if not os.path.exists(PLAYERS_FILE):
    raise FileNotFoundError(f"Missing Players file: {PLAYERS_FILE}")

players_df = pd.read_csv(PLAYERS_FILE, dtype=str)

# Create readable player labels
players_df["label"] = (
    players_df["first_name"].fillna("") + " " +
    players_df["last_name"].fillna("") + ", " +
    players_df["position"].fillna("") + " (" +
    players_df["team"].fillna("") + ")"
)

# Build player ID → label lookup
player_label_map = pd.Series(players_df.label.values, index=players_df.player_id).to_dict()

# -------------------------
# LOAD LEAGUE IDs
# -------------------------
if not os.path.exists(LEAGUE_FILE):
    raise FileNotFoundError(f"Missing LeagueID file: {LEAGUE_FILE}")

league_df = pd.read_csv(LEAGUE_FILE, dtype=str)

# -------------------------
# LOAD EXISTING SCORES
# -------------------------
if os.path.exists(CSV_PATH):
    try:
        existing_df = pd.read_csv(CSV_PATH, dtype=str)
        print(f"📂 Loaded existing data: {len(existing_df)} rows")
    except pd.errors.EmptyDataError:
        print(f"⚠️ {CSV_PATH} exists but is empty. Starting fresh.")
        existing_df = pd.DataFrame()
else:
    existing_df = pd.DataFrame()

# -------------------------
# FUNCTION TO FETCH WEEKLY SCORES
# -------------------------
def get_weekly_scores(league_id, league_year):
    results = []
    for week in range(1, 19):  # NFL weeks 1–18
        url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"⚠️ Error fetching league {league_id}, week {week}: {e}")
            continue

        matchups = resp.json() or []
        print(f"  Week {week}: {len(matchups)} matchups")

        for matchup in matchups:
            roster_id = matchup.get("roster_id", "")
            starters = matchup.get("starters", []) or []
            starters_points = matchup.get("starters_points", []) or []
            lookup_id = f"{league_id}{roster_id}"

            for i, player_id in enumerate(starters):
                points = starters_points[i] if i < len(starters_points) else ""
                results.append({
                    "LeagueYear": league_year,
                    "league_id": league_id,
                    "weekNum": week,
                    "roster_id": roster_id,
                    "lookupID": lookup_id,
                    "starter": str(player_id),
                    "starter_points": points,
                    "array_index": i + 1,
                    "label": player_label_map.get(str(player_id), "")
                })

    return results

# -------------------------
# FETCH DATA FOR CURRENT YEAR ONLY
# -------------------------
current_leagues = league_df.loc[league_df["Year"].astype(int) == CURRENT_YEAR, "LeagueID"].tolist()
if not current_leagues:
    raise ValueError(f"No leagues found for {CURRENT_YEAR} in {LEAGUE_FILE}")

all_data = []
for league_id in current_leagues:
    print(f"➡️ Fetching scores for league {league_id}")
    league_scores = get_weekly_scores(league_id, league_year=CURRENT_YEAR)
    print(f"   -> {len(league_scores)} rows fetched")
    all_data.extend(league_scores)

if not all_data:
    print("⚠️ No new data fetched. Exiting without changes.")
    exit()

new_df = pd.DataFrame(all_data)

# -------------------------
# DEDUPLICATE NEW DATA
# -----
