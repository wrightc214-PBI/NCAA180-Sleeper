import pandas as pd
from sleeper_wrapper import League
import time

# Load league IDs
league_df = pd.read_csv("data/LeagueIDs_AllYears.csv")

all_matchups = []

for idx, row in league_df.iterrows():
    league_id = row['LeagueID']
    year = row['Year']
    league_name = row['LeagueName']

    print(f"Processing {league_name} ({year})")

    league_api = League(league_id)

    # Pull rosters and users for mapping
    try:
        rosters = league_api.get_rosters()
        users = league_api.get_users()
    except Exception as e:
        print(f"  ERROR fetching rosters/users for {league_id}: {e}")
        continue

    user_map = {u['user_id']: u['display_name'] for u in users}
    roster_map = {r['roster_id']: r.get('owner_id') for r in rosters}

    # Pull all weeks
    for week in range(1, 19):
        try:
            weekly_matchups = league_api.get_matchups(week)
        except Exception:
            print(f"  Warning: missing data for week {week}")
            weekly_matchups = []

        # Collect points to calculate max points for later
        weekly_points = []

        for matchup in weekly_matchups:
            for r_id in matchup['rosters']:
                opponent_r_id = [x for x in matchup['rosters'] if x != r_id][0]

                points_for = matchup['points'].get(str(r_id), 0)
                points_against = matchup['points'].get(str(opponent_r_id), 0)

                # Add to weekly points for max calculation
                weekly_points.append(points_for)

                all_matchups.append({
                    "Year": year,
                    "LeagueID": league_id,
                    "LeagueName": league_name,
                    "Week": week,
                    "RosterID": r_id,
                    "OwnerName": user_map.get(roster_map.get(r_id), "Unknown"),
                    "OpponentRosterID": opponent_r_id,
                    "OpponentName": user_map.get(roster_map.get(opponent_r_id), "Unknown"),
                    "PointsFor": points_for,
                    "PointsAgainst": points_against,
                    "Outcome": "Win" if points_for > points_against else ("Loss" if points_for < points_against else "Tie"),
                    "IsRegularSeason": week <= 11,
                    "StarterPoints": matchup.get("starters_points", {}).get(str(r_id), None),
                    "BenchPoints": matchup.get("bench_points", {}).get(str(r_id), None),
                })

        # After all matchups for this week, set max points
        max_points = max(weekly_points) if weekly_points else None
        for m in all_matchups[-len(weekly_points):]:
            m['MaxPointsForWeek'] = max_points

        # Polite pause to avoid API rate limits
        time.sleep(0.5)

# Save CSV
out_file = "data/Matchups_AllYears.csv"
pd.DataFrame(all_matchups).to_csv(out_file, index=False)
print(f"Saved {len(all_matchups)} matchup rows to {out_file}")
