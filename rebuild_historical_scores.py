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
CURRENT_YEAR = today.year - 1 if today.month < 3 else today.year
print(f"🏈 Running full rebuild — includes all years up to {CURRENT_YEAR}")

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
# HELPER: Normalize Key Columns
# -------------------------
def normalize_keys(df):
    if df.empty:
        return df
    for col in ["LeagueYear", "league_id", "roster_id", "weekNum", "array_index"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    return df

# -------------------------
# FUNCTION TO FETCH SCORES
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
# NORMALIZE BEFORE MERGE
# -------------------------
new_df = normalize_keys(new_df)
if not existing_df.empty:
    existing_df = normalize_keys(existing_df)

# -------------------------
# MERGE & DEDUPLICATE BY KEY
# -------------------------
merged_df = pd.concat([existing_df, new_df], ignore_index=True)
merged_df.drop_duplicates(
    subset=["league_id", "roster_id", "weekNum", "array_index"],
    keep="last",
    inplace=True
)

# -------------------------
# FINAL CLEANUP — remove exact full-row duplicates
# -------------------------
before = len(merged_df)
merged_df = merged_df.drop_duplicates(keep="last").reset_index(drop=True)
after = len(merged_df)
print(f"🧹 Final cleanup removed {before - after:,} exact duplicates")

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
