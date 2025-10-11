import pandas as pd
import requests
import datetime
import os
import shutil

# -------------------------
# CONFIG
# -------------------------
CSV_PATH = "data/Scores.csv"
LEAGUE_FILE = "data/LeagueIDs_AllYears.csv"
PLAYERS_FILE = "data/Players.csv"

# -------------------------
# BACKUP EXISTING FILE
# -------------------------
if os.path.exists(CSV_PATH):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = f"{CSV_PATH.replace('.csv', f'_backup_{timestamp}.csv')}"
    shutil.copy(CSV_PATH, backup_path)
    print(f"💾 Backup created: {backup_path}")
else:
    print("⚠️ No existing Scores.csv found — building fresh.")

# -------------------------
# LOAD PLAYERS DATA
# -------------------------
if not os.path.exists(PLAYERS_FILE):
    raise FileNotFoundError(f"Missing Players file: {PLAYERS_FILE}")

players_df = pd.read_csv(PLAYERS_FILE, dtype=str)

# Create label: "first last, position (team)"
players_df["label"] = (
    players_df["first_name"].fillna("") + " " +
    players_df["last_name"].fillna("") + ", " +
    players_df["position"].fillna("") + " (" +
    players_df["team"].fillna("") + ")"
)
player_label_map = pd.Series(players_df.label.values, index=players_df.player_id).to_dict()

# -------------------------
# LOAD LEAGUE IDs
# -------------------------
if not os.path.exists(LEAGUE_FILE):
    raise FileNotFoundError(f"Missing LeagueID file: {LEAGUE_FILE}")

league_df = pd.read_csv(LEAGUE_FILE, dtype=str)
all_years = sorted(league_df["Year"].astype(int).unique())

print(f"📘 Found {len(all_years)} years in LeagueID file: {all_years}")

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
        print(f"   Week {week}: {len(matchups)} matchups")

        if not matchups:
            continue

        for matchup in matchups:
            roster_id = matchup.get("roster_id", "")
            starters = matchup.get("starters", []) or []
            starters_points = matchup.get("starters_points", []) or []
            lookup_id = f"{league_id}.{roster_id}"

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
# FETCH ALL HISTORICAL DATA
# -------------------------
all_data = []
for year in all_years:
    league_ids = league_df.loc[league_df["Year"].astype(int) == year, "LeagueID"].tolist()
    print(f"\n📅 Fetching data for {year} ({len(league_ids)} leagues)")
    for league_id in league_ids:
        print(f"➡️ League {league_id}")
        league_scores = get_weekly_scores(league_id, league_year=year)
        print(f"   -> {len(league_scores)} rows fetched")
        all_data.extend(league_scores)

if not all_data:
    raise RuntimeError("No data fetched. Check your LeagueIDs or network connection.")

# -------------------------
# BUILD AND SAVE FINAL CSV
# -------------------------
df = pd.DataFrame(all_data)

# Deduplicate in case of any overlaps
df = df.drop_duplicates(
    subset=["LeagueYear", "league_id", "weekNum", "roster_id", "array_index"],
    keep="last"
)

# Sort cleanly for readability
df["array_index"] = df["array_index"].astype(int)
df = df.sort_values(
    by=["LeagueYear", "league_id", "roster_id", "weekNum", "array_index"]
)

os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
df.to_csv(CSV_PATH, index=False)

print(f"\n✅ Historical rebuild complete!")
print(f"📊 Total rows written: {len(df)}")
print(f"💾 Saved to: {CSV_PATH}")
