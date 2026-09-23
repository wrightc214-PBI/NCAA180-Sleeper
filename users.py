import pandas as pd
from sleeper_wrapper import League, User
import datetime

# NCAA Ranks user ID
user_id = 731808894699028480

# Current NFL season year (Jan/Feb still counts as prior season)
today = datetime.date.today()
CURRENT_YEAR = today.year - 1 if today.month < 3 else today.year

all_rosters = []

leagues = User(user_id).get_all_leagues("nfl", CURRENT_YEAR)
for league in leagues:
    league_id = league["league_id"]
    league_name = league.get("name")
    division1 = league.get("metadata", {}).get("division_1")
    division2 = league.get("metadata", {}).get("division_2")

    league_api = League(league_id)
    rosters = league_api.get_rosters()
    users = league_api.get_users()

    user_map = {u["user_id"]: u["display_name"] for u in users}

    for r in rosters:
        division_num = r.get("settings", {}).get("division")

        if division_num == 1:
            division_name = division1
        elif division_num == 2:
            division_name = division2
        else:
            division_name = None

        all_rosters.append({
            "Year": CURRENT_YEAR,
            "LeagueID": league_id,
            "LeagueName": league_name,
            "RosterID": r["roster_id"],
            "OwnerID": r.get("owner_id"),
            "OwnerName": user_map.get(r.get("owner_id"), "Unknown"),
            "Division": division_num,
            "DivisionName": division_name,
            "Wins": r.get("settings", {}).get("wins", 0),
            "Losses": r.get("settings", {}).get("losses", 0),
            "PointsFor": r.get("settings", {}).get("fpts", 0),
            "PointsAgainst": r.get("settings", {}).get("fpts_against", 0)
        })

df = pd.DataFrame(all_rosters)

out_file = "data/Standings_Season.csv"
df.to_csv(out_file, index=False)
print(f"Saved {len(df)} roster rows to {out_file}")
