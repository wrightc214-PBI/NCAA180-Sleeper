import pandas as pd
from sleeper_wrapper import League, User
import datetime

user_id = 731808894699028480

today = datetime.date.today()
CURRENT_YEAR = today.year - 1 if today.month < 3 else today.year

LINKOFTIME_ID = "460518714907815936"
LINKOFTIME_REAL_LEAGUE = "NCAA BIG 10"

def resolve_owner_name(owner_id, roster_id, league_name, user_map):
    if owner_id is None:
        return "Unknown"
    if str(owner_id) == LINKOFTIME_ID and league_name != LINKOFTIME_REAL_LEAGUE:
        return f"{league_name} Orphan #{roster_id}"
    return user_map.get(owner_id, "Unknown")

# -------------------------
# REGULAR-SEASON RECORD (weeks 1-11 only) FROM MATCHUPS DATA
# -------------------------
matchups_df = pd.read_csv("data/Matchups_Season.csv", dtype=str)
matchups_df["PointsFor"] = matchups_df["PointsFor"].astype(float)
matchups_df["PointsAgainst"] = matchups_df["PointsAgainst"].astype(float)

regular_season = matchups_df[matchups_df["IsRegularSeason"].astype(str) == "True"]

standings_agg = regular_season.groupby(["LeagueID", "RosterID"]).agg(
    Wins=("Outcome", lambda x: (x == "Win").sum()),
    Losses=("Outcome", lambda x: (x == "Loss").sum()),
    PointsFor=("PointsFor", "sum"),
    PointsAgainst=("PointsAgainst", "sum")
).reset_index()

# -------------------------
# ROSTER/DIVISION METADATA (not available from Matchups data)
# -------------------------
all_rosters = []
leagues = User(user_id).get_all_leagues("nfl", CURRENT_YEAR)
for league in leagues:
    league_id = str(league["league_id"])
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

        owner_id = r.get("owner_id")
        all_rosters.append({
            "Year": CURRENT_YEAR,
            "LeagueID": league_id,
            "LeagueName": league_name,
            "RosterID": str(r["roster_id"]),
            "OwnerID": owner_id,
            "OwnerName": resolve_owner_name(owner_id, r["roster_id"], league_name, user_map),
            "Division": division_num,
            "DivisionName": division_name
        })

meta_df = pd.DataFrame(all_rosters)

# -------------------------
# MERGE METADATA WITH REGULAR-SEASON RECORD
# -------------------------
merged = meta_df.merge(standings_agg, on=["LeagueID", "RosterID"], how="left")
merged[["Wins", "Losses"]] = merged[["Wins", "Losses"]].fillna(0).astype(int)
merged[["PointsFor", "PointsAgainst"]] = merged[["PointsFor", "PointsAgainst"]].fillna(0).round(2)

out_file = "data/Standings_Season.csv"
merged.to_csv(out_file, index=False)
print(f"Saved {len(merged)} roster rows (regular season, weeks 1-11) to {out_file}")
