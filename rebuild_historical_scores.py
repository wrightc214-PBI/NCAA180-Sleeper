import pandas as pd
import requests
import datetime
import os
import subprocess

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

print(f"🏈 Running full rebuild — includes all years up to {CURRENT_YEAR}")

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
# LOAD LEAGUE IDs (all years)
# -------------------------
if not os.path.exists(LEAGUE_FILE):
    raise FileNotFoundError(f"Missing LeagueID file: {LEAGUE_FILE}")

league_df = pd.read_csv(LEAGUE_FILE, dtype=str)
league_df["Year"] = league_df["Year"].astype(int)

# -------------------------
# LOAD EXISTING CSV (optional, for incremental rebuilds)
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
            lookup_id = f"{league_id}{roster_id}"

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
# FETCH AND COMBINE DATA (ALL YEARS)
# -------------------------
all_data = []

for year in sorted(league_df["Year"].unique()):
    leagues = league_df.loc[league_df["Year"] == year, "LeagueID"].tolist()
    if not leagues:
        print(f"⚠️ No leagues found for {year}")
        continue

    print(f"🏆 Fetching data for season {year} ({len(leagues)} leagues)")
    for league_id in leagues:
        print(f"➡️ League {league_id}")
        league_scores = get_weekly_scores(league_id, league_year=year)
        print(f"   -> {len(league_scores)} rows fetched")
        all_data.extend(league_scores)

if not all_data:
    print("⚠️ No new data fetched. Exiting without changes.")
    exit()

new_df = pd.DataFrame(all_data)

# -------------------------
# DEDUPLICATE — overwrite duplicates based on key combo
# -------------------------
new_df = new_df.drop_duplicates(
    subset=["league_id", "weekNum", "roster_id", "array_index"],
    keep="last"
)

# -------------------------
# COMBINE WITH EXISTING DATA (replace duplicates, append new)
# -------------------------
if not existing_df.empty:
    existing_df = existing_df.drop_duplicates(
        subset=["league_id", "weekNum", "roster_id", "array_index"],
        keep="last"
    )

    # Drop old duplicates and replace with latest
    merged_df = pd.concat([existing_df, new_df], ignore_index=True)
    merged_df = merged_df.drop_duplicates(
        subset=["league_id", "weekNum", "roster_id", "array_index"],
        keep="last"
    )
else:
    merged_df = new_df

# -------------------------
# SORT & SAVE
# -------------------------
merged_df["array_index"] = merged_df["array_index"].astype(int)
merged_df = merged_df.sort_values(
    by=["LeagueYear", "league_id", "roster_id", "weekNum", "array_index"]
)

merged_df.to_csv(CSV_PATH, index=False)

print(f"\n✅ Rebuild complete — Scores.csv updated through {CURRENT_YEAR}")
print(f"📊 Total rows after rebuild: {len(merged_df)}")

# -------------------------
# AUTO GIT COMMIT + PUSH
# -------------------------
try:
    subprocess.run(["git", "add", CSV_PATH], check=True)
    subprocess.run(["git", "commit", "-m", f"Auto rebuild: Scores.csv updated through {CURRENT_YEAR}"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("🚀 Auto-commit and push completed successfully.")
except subprocess.CalledProcessError as e:
    print(f"⚠️ Git auto-commit failed: {e}")
