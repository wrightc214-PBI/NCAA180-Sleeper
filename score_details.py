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
    except pd.errors.EmptyDataError:
        print(f"⚠️ {CSV_PATH} exists but is empty. Starting with empty DataFrame.")
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
        print(f"Week {week}, league {league_id}, matchups returned: {len(matchups)}")

        if not matchups:
            continue

        for matchup in matchups:
            roster_id = matchup.get("roster_id", "")
            starters = matchup.get("starters", []) or []
            starters_points = matchup.get("starters_points", []) or []
            lookup_id = f"{league_id}{roster_id}"

            # Ensure all starters are captured safely
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
                    "array_index": i + 1,  # 1-based
                    "label": player_label_map.get(player_id, "")
                })
    return results

# -------------------------
# FETCH AND COMBINE DATA FOR ALL YEARS
# -------------------------
all_years = sorted(league_df["Year"].astype(int).unique())
all_data = []

for year in all_years:
    league_ids = league_df.loc[league_df["Year"].astype(int) == year, "LeagueID"].tolist()
    print(f"Found {len(league_ids)} leagues for {year}")

    for league_id in league_ids:
        print(f"Fetching scores for {league_id} ({year})")
        league_scores = get_weekly_scores(league_id, league_year=year)
        print(f"  -> {len(league_scores)} rows fetched for this league")
        all_data.extend(league_scores)

print(f"Total rows collected for all leagues/years: {len(all_data)}")

if all_data:
    new_df = pd.DataFrame(all_data)

    # Keep previous CSV data if exists
    if not existing_df.empty:
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    # Convert types for Power BI
    combined_df['starter'] = combined_df['starter'].astype(str)
    combined_df['starter_points'] = combined_df['starter_points'].astype(str)
    combined_df['array_index'] = combined_df['array_index'].astype(int)
    combined_df['label'] = combined_df['label'].astype(str)

    # Optional sort
    combined_df = combined_df.sort_values(
        by=["LeagueYear", "league_id", "roster_id", "weekNum", "array_index"]
    )

    combined_df.to_csv(CSV_PATH, index=False)
    print(f"✅ Saved {CSV_PATH} — historical + current year data included.")
    print(f"Total rows now: {len(combined_df)}")
else:
    print("⚠️ No data fetched — scores.csv not updated.")
