import pandas as pd
import requests
import datetime
import os
import argparse

# -------------------------
# CONFIG
# -------------------------
CSV_PATH = "data/Scores.csv"
LEAGUE_FILE = "data/LeagueIDs_AllYears.csv"
PLAYERS_FILE = "data/Players.csv"

# -------------------------
# ARGUMENT PARSER
# -------------------------
parser = argparse.ArgumentParser(description="Fetch Sleeper league scores.")
parser.add_argument("--week", type=int, help="Specify NFL week number to fetch (1–18)")
args = parser.parse_args()

# -------------------------
# DETERMINE CURRENT NFL YEAR (adjust for Jan/Feb rollover)
# -------------------------
today = datetime.date.today()
CURRENT_YEAR = today.year - 1 if today.month < 3 else today.year
print(f"🏈 Current NFL Year: {CURRENT_YEAR}")
if args.week:
    print(f"📅 Limiting update to Week {args.week}")

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
def get_weekly_scores(league_id, league_year, week=None):
    results = []
    weeks_to_pull = [week] if week else range(1, 19)
    for week_num in weeks_to_pull:
        url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week_num}"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"⚠️ Error fetching league {league_id}, week {week_num}: {e}")
            continue

        matchups = resp.json() or []
        print(f"  Week {week_num}: {len(matchups)} matchups")

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
                    "weekNum": week_num,
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
    league_scores = get_weekly_scores(league_id, league_year=CURRENT_YEAR, week=args.week)
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
combined_df = pd.concat([existing_df, new_df], ignore_index=True)
combined_df.drop_duplicates(
    subset=["league_id", "roster_id", "weekNum", "array_index"],
    keep="last",
    inplace=True
)

# -------------------------
# FINAL CLEANUP — remove exact full-row duplicates
# -------------------------
before = len(combined_df)
combined_df = combined_df.drop_duplicates(keep="last").reset_index(drop=True)
after = len(combined_df)
print(f"🧹 Final cleanup removed {before - after:,} exact duplicates")

# -------------------------
# SORT & SAVE
# -------------------------
combined_df["array_index"] = combined_df["array_index"].astype(int)
combined_df.sort_values(
    by=["LeagueYear", "league_id", "roster_id", "weekNum", "array_index"],
    inplace=True
)

combined_df.to_csv(CSV_PATH, index=False)
print(f"\n✅ Scores.csv updated for {CURRENT_YEAR}")
print(f"📊 Total rows after update: {len(combined_df)}")
