import pandas as pd
from sleeper_wrapper import User
import datetime
import os

# NCAA Ranks user ID (present in all conferences)
USER_ID = 731808894699028480

# Years: from 2020 to current
start_year = 2020
end_year = datetime.datetime.now().year
years = range(start_year, end_year + 1)

# Output folder (relative path so GitHub runners can use it too)
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

all_leagues = []

for year in years:
    user = User(USER_ID)

    # Pull all leagues for this user & year
    jsonDataLeagues = User.get_all_leagues(user, "nfl", year)

    # Extract league details
    for league in jsonDataLeagues:
        all_leagues.append({
            "Year": year,
            "LeagueID": league.get("league_id"),
            "LeagueName": league.get("name"),
            "Division1": league.get("metadata", {}).get("division_1"),
            "Division2": league.get("metadata", {}).get("division_2")
        })

# Convert to DataFrame
df = pd.DataFrame(all_leagues)

# Save single file (all years combined)
filename = os.path.join(OUTPUT_DIR, "LeagueIDs_AllYears.csv")
df.to_csv(filename, index=False)

print(f"✅ Saved {len(df)} league records to {filename}")
