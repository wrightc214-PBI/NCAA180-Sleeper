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
if today.month < 3:  # Jan or Feb -> still previous NFL season
    CURRENT_YEAR = today.year - 1
else:
    CURRENT_YEAR = today.year

print(f"🏈 Current NFL Year: {CURRENT_YEAR}")

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

# -------------------------
# LOAD EXISTING CSV (handle empty)
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
# FUNCTION TO FETCH SCORES
# -------------------------
def get_weekly_scores(league_id, league_year):
    results = []
    for week in range(1, 19):  # weeks 1–18
        url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"
        try:
            resp = requests.get(url, timeout=10)
        except Exception as e:
            print(f"⚠️ Error fetching league {league_id}, week {week}: {e}")
            continue

        if resp.status_code != 200:
            print(f"⚠️ Skipping week {week} for league {league_id} — HTTP {resp.status_code}")
            continue

        matchups = resp.json()
        print(f"  Week {week}: {len(matchups)} matchups")

        for matchup in matchups or []:
            roster_id = matchup.get("roster_id", "")
            starters = matchup.get("starters", []) or []
            starters_points = matchup.get("starters_points", []) or []
            lookup_id = f"{league_id}&{roster_id}"

            length = max(len(starters), len(starters_points))
            for i in range(length):
                player_id = str(starters[i]) if i < len(starters) else ""
                points = starters_points[i] if i < len(starters_points) else ""

                results.append({
                    "LeagueYear": league_year,
                    "league_id": league_id,
                    "weekNum": week,
                    "roster_id": roster_id,
                    "lookupID": lookup_id,
                    "starter": player_id,
                    "starter_points": points,
                    "array_index": i + 1,
                    "label": player_label_map.get(player_id, "")
                })
    return results

# -------------------------
# FETCH AND COMBINE DATA (CURRENT YEAR ONLY)
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
# -------------------------
new_df = new_df.drop_duplicates(
    subset=["LeagueYear", "league_id", "weekNum", "roster_id", "starter"],
    keep="last"
)

# -------------------------
# COMBINE WITH EXISTING DATA (replace current year)
# -------------------------
if not existing_df.empty:
    existing_df["LeagueYear"] = existing_df["LeagueYear"].astype(int)
    existing_df = existing_df[existing_df["LeagueYear"] != CURRENT_YEAR]  # remove old current year

    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    combined_df = combined_df.drop_duplicates(
        subset=["LeagueYear", "league_id", "weekNum", "roster_id", "starter"],
        keep="last"
    )
else:
    combined_df = new_df

# -------------------------
# SORT & SAVE
# -------------------------
combined_df["array_index"] = combined_df["array_index"].astype(int)
combined_df = combined_df.sort_values(
    by=["LeagueYear", "league_id", "roster_id", "weekNum", "array_index"]
)

combined_df.to_csv(CSV_PATH, index=False)

print(f"\n✅ Scores.csv updated for {CURRENT_YEAR}")
print(f"📊 Total rows after update: {len(combined_df)}")
