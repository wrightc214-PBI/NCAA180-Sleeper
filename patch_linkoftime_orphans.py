import pandas as pd

LINKOFTIME_ID = "460518714907815936"
LINKOFTIME_REAL_LEAGUE = "NCAA BIG 10"

def orphan_label(league_name, roster_id):
    return f"{league_name} Orphan #{roster_id}"

# --- Standings_Historic.csv ---
standings = pd.read_csv("data/Standings_Historic.csv", dtype=str)
mask = (standings["OwnerID"] == LINKOFTIME_ID) & (standings["LeagueName"] != LINKOFTIME_REAL_LEAGUE)
standings.loc[mask, "OwnerName"] = standings.loc[mask].apply(
    lambda r: orphan_label(r["LeagueName"], r["RosterID"]), axis=1
)
standings.to_csv("data/Standings_Historic.csv", index=False)
print(f"Patched {mask.sum()} orphan rows in Standings_Historic.csv")

# --- Matchups_Historic.csv ---
matchups = pd.read_csv("data/Matchups_Historic.csv", dtype=str)
owner_lookup = matchups.set_index(["Year", "LeagueID", "RosterID"])["OwnerID"].to_dict()

mask_owner = (matchups["OwnerID"] == LINKOFTIME_ID) & (matchups["LeagueName"] != LINKOFTIME_REAL_LEAGUE)
matchups.loc[mask_owner, "OwnerName"] = matchups.loc[mask_owner].apply(
    lambda r: orphan_label(r["LeagueName"], r["RosterID"]), axis=1
)

def patch_opponent(row):
    key = (row["Year"], row["LeagueID"], row["OpponentRosterID"])
    opp_owner_id = owner_lookup.get(key)
    if opp_owner_id == LINKOFTIME_ID and row["LeagueName"] != LINKOFTIME_REAL_LEAGUE:
        return orphan_label(row["LeagueName"], row["OpponentRosterID"])
    return row["OpponentName"]

matchups["OpponentName"] = matchups.apply(patch_opponent, axis=1)
matchups.to_csv("data/Matchups_Historic.csv", index=False)
print(f"Patched {mask_owner.sum()} owner rows in Matchups_Historic.csv (opponent side included)")
