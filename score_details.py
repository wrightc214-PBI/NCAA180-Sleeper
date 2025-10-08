import pandas as pd
import datetime
import os

CURRENT_YEAR = datetime.datetime.now().year
CSV_PATH = "scores.csv"

# Load existing data if file exists
if os.path.exists(CSV_PATH):
    existing_df = pd.read_csv(CSV_PATH, dtype=str)
else:
    existing_df = pd.DataFrame()

# Function to determine year from LeagueID
def get_league_year(league_id):
    # Assuming your league_id encodes the year somewhere — adjust if needed
    # Or if you track league-year in your metadata, read it directly.
    return league_id_year_map.get(league_id, CURRENT_YEAR)

# --- Fetch new data for leagues this year ---
new_data = []  # list of dicts from API

for league_id in current_year_league_ids:
    league_year = CURRENT_YEAR
    print(f"Fetching scores for {league_id} ({league_year})")
    # Your existing code that builds weekly game / team score data
    weekly_scores = get_weekly_scores(league_id)
    new_data.extend(weekly_scores)

new_df = pd.DataFrame(new_data)

# --- Combine logic ---
if not existing_df.empty:
    # Keep all past-year data
    old_df = existing_df[existing_df["LeagueYear"].astype(int) < CURRENT_YEAR]
    # Drop current-year data (will be replaced)
    existing_df = existing_df[existing_df["LeagueYear"].astype(int) < CURRENT_YEAR]
else:
    old_df = pd.DataFrame()

# Append new data to old data
combined_df = pd.concat([old_df, new_df], ignore_index=True)

# Save
combined_df.to_csv(CSV_PATH, index=False)
print(f"✅ Updated {CSV_PATH} (kept old years, replaced current year data)")
