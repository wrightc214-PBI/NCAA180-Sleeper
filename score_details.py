import pandas as pd
import datetime
import os

CURRENT_YEAR = datetime.datetime.now().year
CSV_PATH = "scores.csv"
LEAGUE_PATH = "data/LeagueIDs_AllYears.csv"

# --- Load league IDs ---
league_df = pd.read_csv(LEAGUE_PATH, dtype=str)
league_df["Year"] = league_df["Year"].astype(int)

# Check if CURRENT_YEAR exists in data; if not, use most recent available year
if CURRENT_YEAR in league_df["Year"].values:
    target_year = CURRENT_YEAR
else:
    target_year = league_df["Year"].max()
    print(f"⚠️ No leagues found for {CURRENT_YEAR}, using most recent year: {target_year}")

current_year_league_ids = league_df.loc[league_df["Year"] == target_year, "LeagueID"].tolist()

# --- Load existing scores data if file exists ---
if os.path.exists(CSV_PATH):
    existing_df = pd.read_csv(CSV_PATH, dtype=str)
else:
    existing_df = pd.DataFrame()

# --- Fetch new data for target year ---
new_data = []  # list of dicts from API

for league_id in current_year_league_ids:
    print(f"Fetching scores for {league_id} ({target_year})")

    # Replace this with your actual API function
    weekly_scores = get_weekly_scores(league_id)

    # Ensure each entry has a LeagueYear
    for score in weekly_scores:
        score["LeagueYear"] = target_year

    new_data.extend(weekly_scores)

new_df = pd.DataFrame(new_data)

# --- Combine with existing data ---
if not existing_df.empty:
    # Keep all past-year data
    old_df = existing_df[existing_df["LeagueYear"].astype(int) < target_year]
else:
    old_df = pd.DataFrame()

combined_df = pd.concat([old_df, new_df], ignore_index=True)

# --- Save updated file ---
combined_df.to_csv(CSV_PATH, index=False)
print(f"✅ Updated {CSV_PATH} (kept old years, replaced {target_year} data)")
