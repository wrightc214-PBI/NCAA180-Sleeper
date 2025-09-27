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

    # Only include users that have a roster
    roster_map = {r['roster_id']: r.get('owner_id') for r in rosters}
    user_map = {u['user_id']: u['display_name'] for u in users if u['user_id'] in roster_map.values()}

    # Pull all weeks (1–18)
    for week in range(1, 19):
        try:
            weekly_matchups = league_api.get_matchups(week)
        except Exception as e:
            print(f"  Warning: missing data for week {week} - {e}")
            weekly_matchups = []

        for matchup in weekly_matchups:
            rosters_in_matchup = matchup.get('rosters', [])
            if len(rosters_in_matchup) < 2:
                continue  # Skip incomplete or invalid matchups

            for r_id in rosters_in_matchup:
                # Skip if roster id is not recognized
                if r_id not in roster_map:
                    continue

                opponent_r_id = [x for x in rosters_in_matchup if x != r_id][0]

                points_for = matchup.get('points', {}).get(str(r_id), 0)
                points_against = matchup.get('points', {}).get(str(opponent_r_id), 0)

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

        # Polite pause to avoid API rate limits
        time.sleep(0.5)

# Save CSV
out_file = "data/Matchups_AllYears.csv"
pd.DataFrame(all_matchups).to_csv(out_file, index=False)
print(f"Saved {len(all_matchups)} matchup rows to {out_file}")
