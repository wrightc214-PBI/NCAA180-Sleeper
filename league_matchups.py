import pandas as pd
import datetime
import time
from collections import defaultdict
from sleeper_wrapper import League

# -------------------------
# CURRENT YEAR (season rollover: Jan/Feb still counts as prior season)
# -------------------------
today = datetime.date.today()
CURRENT_YEAR = today.year - 1 if today.month < 3 else today.year

# Load league IDs, restricted to current year only
league_df = pd.read_csv("data/LeagueIDs_AllYears.csv")
league_df = league_df[league_df["Year"] == CURRENT_YEAR]

season_matchups = []

OBSERVER_IDS = [731808894699028480]  # Optional: exclude observer accounts

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

    roster_map = {r['roster_id']: r.get('owner_id') for r in rosters}
    user_map = {u['user_id']: u['display_name'] for u in users if u['user_id'] in roster_map.values()}

    for week in range(1, 19):
        try:
            weekly_matchups = league_api.get_matchups(week)
        except Exception as e:
            print(f"  Warning: missing data for week {week} - {e}")
            continue

        if not weekly_matchups:
            continue

        matchups_by_id = defaultdict(list)
        for m in weekly_matchups:
            matchups_by_id[m['matchup_id']].append(m)

        for matchup_id, teams in matchups_by_id.items():
            if len(teams) != 2:
                teams.append({'roster_id': None, 'points': 0, 'starters': [], 'starters_points': [], 'players_points': {}})

            team1, team2 = teams

            for t, opp in [(team1, team2), (team2, team1)]:
                r_id = t['roster_id']
                owner_id = roster_map.get(r_id)
                if owner_id is None or owner_id in OBSERVER_IDS:
                    owner_id = 0
                    owner_name = "Vacant"
                else:
                    owner_name = user_map.get(owner_id, "Unknown")

                opp_rid = opp.get('roster_id')
                opp_owner_id = roster_map.get(opp_rid)
                if opp_owner_id is None or opp_owner_id in OBSERVER_IDS:
                    opp_name = "Vacant"
                else:
                    opp_name = user_map.get(opp_owner_id, "Unknown")

                points_for = t.get('points', 0)
                points_against = opp.get('points', 0)

                if points_for == 0 and points_against == 0:
                    outcome = ""
                else:
                    outcome = "Win" if points_for > points_against else ("Loss" if points_for < points_against else "Tie")

                season_matchups.append({
                    "Year": year,
                    "LeagueID": league_id,
                    "LeagueName": league_name,
                    "Week": week,
                    "RosterID": r_id,
                    "OwnerID": owner_id,
                    "OwnerName": owner_name,
                    "OpponentRosterID": opp_rid,
                    "OpponentName": opp_name,
                    "PointsFor": points_for,
                    "PointsAgainst": points_against,
                    "Outcome": outcome,
                    "IsRegularSeason": week <= 11,
                    "StarterPoints": sum(t.get('starters_points', [])) if t.get('starters_points') else None,
                    "BenchPoints": points_for - sum(t.get('starters_points', [])) if t.get('starters_points') else None
                })

        time.sleep(0.5)

# -------------------------
# SAVE SEASON FILE (current year, all weeks played so far)
# -------------------------
season_df = pd.DataFrame(season_matchups)
season_df.to_csv("data/Matchups_Season.csv", index=False)
print(f"Saved {len(season_df)} matchup rows to data/Matchups_Season.csv")

# -------------------------
# SAVE WEEK FILE (current week only)
# -------------------------
completed_weeks = [m["Week"] for m in season_matchups if m["Outcome"] != ""]
if completed_weeks:
    current_week = max(completed_weeks)
    week_df = season_df[season_df["Week"] == current_week]
    week_df.to_csv("data/Matchups_Week.csv", index=False)
    print(f"Saved {len(week_df)} rows for week {current_week} to data/Matchups_Week.csv")
else:
    print("No completed weeks yet — skipping Matchups_Week.csv")
