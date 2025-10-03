import pandas as pd
from sleeper_wrapper import League, User
import datetime

# NCAA Ranks user ID
user_id = 731808894699028480

# Automatically include all years from 2020 through the current year
start_year = 2020
current_year = datetime.datetime.now().year
years = list(range(start_year, current_year + 1))


all_rosters = []

for year in years:
    # Get all leagues for this user/year
    leagues = User(user_id).get_all_leagues("nfl", year)
    for league in leagues:
        league_id = league["league_id"]
        league_name = league.get("name")
        division1 = league.get("metadata", {}).get("division_1")
        division2 = league.get("metadata", {}).get("division_2")

        league_api = League(league_id)

        # Pull rosters and users
        rosters = league_api.get_rosters()
        users = league_api.get_users()

        # Map user_id -> display_name
        user_map = {u["user_id"]: u["display_name"] for u in users}

        for r in rosters:
            # Division number comes from settings
            division_num = r.get("settings", {}).get("division")

            # Map to actual division name
            if division_num == 1:
                division_name = division1
            elif division_num == 2:
                division_name = division2
            else:
                division_name = None

            all_rosters.append({
                "Year": year,
                "LeagueID": league_id,
                "LeagueName": league_name,
                "RosterID": r["roster_id"],
                "OwnerID": r.get("owner_id"),
                "OwnerName": user_map.get(r.get("owner_id"), "Unknown"),
                "Division": division_num,          # 1 or 2 (int)
                "DivisionName": division_name,     # actual name
                "Wins": r.get("settings", {}).get("wins", 0),
                "Losses": r.get("settings", {}).get("losses", 0),
                "PointsFor": r.get("settings", {}).get("fpts", 0),
                "PointsAgainst": r.get("settings", {}).get("fpts_against", 0)
            })

# Convert to DataFrame
df = pd.DataFrame(all_rosters)

# Save CSV
out_file = "data/Users_AllYears.csv"
df.to_csv(out_file, index=False)
print(f"Saved {len(df)} roster rows to {out_file}")
