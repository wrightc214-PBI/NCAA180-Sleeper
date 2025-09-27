import pandas as pd
from sleeper_wrapper import League

# Load league IDs
league_df = pd.read_csv("data/LeagueIDs_AllYears.csv")

all_matchups = []

for idx, row in league_df.iterrows():
    league_id = row['LeagueID']
    year = row['Year']
    league_name = row['LeagueName']

    league_api = League(league_id)

    # Get rosters and users for mapping
    rosters = league_api.get_rosters()
    users = league_api.get_users()
    user_map = {u['user_id']: u['display_name'] for u in users}
    roster_map = {r['roster_id']: r.get('owner_id') for r in rosters}

    # Determine all weeks (1–18)
    for week in range(1, 19):
        try:
            weekly_matchups = league_api.get_matchups(week)
        except Exception:
            weekly_matchups = []
        for matchup in weekly_matchups:
            for r_id in matchup['rosters']:
                opponent_r_id = [x for x in matchup['rosters'] if x != r_id][0]  # 1v1 league
                all_matchups.append({
                    "Year": year,
                    "LeagueID": league_id,
                    "LeagueName": league_name,
                    "Week": week,
                    "RosterID": r_id,
                    "OwnerName": user_map.get(roster_map.get(r_id), "Unknown"),
                    "OpponentRosterID": opponent_r_id,
                    "OpponentName": user_map.get(roster_map.get(opponent_r_id), "Unknown"),
                    "PointsFor": matchup['points'].get(str(r_id), 0),
                    "PointsAgainst": matchup['points'].get(str(opponent_r_id), 0),
                    "Outcome": "Win" if matchup['points'].get(str(r_id),0) > matchup['points'].get(str(opponent_r_id),0) else ("Loss" if matchup['points'].get(str(r_id),0) < matchup['points'].get(str(opponent_r_id),0) else "Tie"),
                    "IsRegularSeason": week <= 11
                })

# Save CSV
out_file = "data/Matchups_AllYears.csv"
pd.DataFrame(all_matchups).to_csv(out_file, index=False)
print(f"Saved {len(all_matchups)} matchup rows to {out_file}")
