import pandas as pd
from sleeper_wrapper import League

# Load league IDs
league_df = pd.read_csv("data/LeagueIDs_AllYears.csv")

all_players = []

for idx, row in league_df.iterrows():
    league_id = row['LeagueID']
    year = row['Year']
    league_name = row['LeagueName']

    print(f"Processing {league_name} ({year})")

    league_api = League(league_id)

    try:
        rosters = league_api.get_rosters()
        users = league_api.get_users()
    except Exception as e:
        print(f"  ERROR fetching rosters/users for {league_id}: {e}")
        continue

    # Map user_id -> display_name
    user_map = {u["user_id"]: u["display_name"] for u in users}

    for r in rosters:
        roster_id = r["roster_id"]
        owner_id = r.get("owner_id")
        owner_name = user_map.get(owner_id, "Unknown")

        # loop through all players on this roster
        for player_id in r.get("players", []):
            all_players.append({
                "Year": year,
                "LeagueID": league_id,
                "LeagueName": league_name,
                "RosterID": roster_id,
                "OwnerID": owner_id,
                "OwnerName": owner_name,
                "PlayerID": player_id
            })

# Convert to DataFrame
df = pd.DataFrame(all_players)

# Save CSV
out_file = "data/Rosters_Players_AllYears.csv"
df.to_csv(out_file, index=False)
print(f"Saved {len(df)} player rows to {out_file}")
