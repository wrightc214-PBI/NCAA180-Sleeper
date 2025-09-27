import pandas as pd
from sleeper_wrapper import League
import time

# Load league IDs
league_df = pd.read_csv("data/LeagueIDs_AllYears.csv")

all_matchups = []

# Define observer or unassigned user IDs
OBSERVER_IDS = [731808894699028480]

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

    # Map roster_id -> owner_id
    roster_map = {r['roster_id']: r.get('owner_id') for r in rosters}

    # Map user_id -> display name (only users assigned to a roster)
    user_map = {u['user_id']: u['display_name'] for u in users if u['user_id'] in roster_map.values()}

    # Fetch all weeks 1-18
    for week in range(1, 19):
        try:
            weekly_matchups = league_api.get_matchups(week)
        except Exception as e:
            print(f"  Warning: missing data for week {week} - {e}")
            weekly_matchups = []

        if not weekly_matchups:
            continue

        for matchup in weekly_matchups:
            rosters_in_matchup = matchup.get('rosters', [])
            if not rosters_in_matchup:
                print(f"  Skipping empty matchup: {matchup}")
                continue

            for r_id in rosters_in_matchup:
                owner_id = roster_map.get(r_id)
                # Replace observer or unassigned users with Vacant
                if owner_id is None or owner_id in OBSERVER_IDS:
                    owner_id = 0
                    owner_name = "Vacant"
                else:
                    owner_name = user_map.get(owner_id, "Unknown")

                # Get opponent roster
                opponents = [x for x in rosters_in_matchup if x != r_id]
                if not opponents:
                    opponent_r_id = None
                    opponent_name = "Vacant"
                    points_against = 0
                else:
                    opponent_r_id = opponents[0]
                    opp_owner_id = roster_map.get(opponent_r_id)
                    if opp_owner_id is None or opp_owner_id in OBSERVER_IDS:
                        opponent_name = "Vacant"
                    else:
                        opponent_name = user_map.get(opp_owner_id, "Unknown")
                    points_against = matchup.get('points', {}).get(str(opponent_r_id), 0)

                points_for = matchup.get('points', {}).get(str(r_id), 0)

                all_matchups.append({
                    "Year": year,
                    "LeagueID": league_id,
                    "LeagueName": league_name,
                    "Week": week,
                    "RosterID": r_id,
                    "OwnerID": owner_id,
                    "OwnerName": owner_name,
                    "OpponentRosterID": opponent_r_id,
                    "OpponentName": opponent_name,
                    "PointsFor": points_for,
                    "PointsAgainst": points_against,
                    "Outcome": "Win" if points_for > points_against else ("Loss" if points_for < points_against else "Tie"),
                    "IsRegularSeason": week <= 11,
                    "StarterPoints": matchup.get("starters_points", {}).get(str(r_id), None),
                    "BenchPoints": matchup.get("bench_points", {}).get(str(r_id), None)
                })

        # Polite pause to avoid API rate limits
        time.sleep(0.5)

# Save CSV
out_file = "data/Matchups_AllYears.csv"
pd.DataFrame(all_matchups).to_csv(out_file, index=False)
print(f"Saved {len(all_matchups)} matchup rows to {out_file}")
