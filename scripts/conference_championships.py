import pandas as pd
import datetime
import argparse
import os
import sys

from _postseason_common import load_regular_season_standings, week_points_lookup

# -------------------------
# CONFIG
# -------------------------
OUTPUT_PATH = "data/Postseason_Season.csv"

CCG_WEEK = 12  # first postseason week; division winners from weeks 1-11 meet here.
ROUND_NAME = "CCG"

# -------------------------
# ARGUMENT PARSER
# -------------------------
parser = argparse.ArgumentParser(description="Determine conference championship game (CCG) matchups and results.")
parser.add_argument("--year", type=int, help="Season year (defaults to current NFL year)")
args = parser.parse_args()

today = datetime.date.today()
CURRENT_YEAR = args.year or (today.year - 1 if today.month < 3 else today.year)
print(f"Season: {CURRENT_YEAR}")

# -------------------------
# STEP 1: REGULAR SEASON STANDINGS (weeks 1-11), PER LEAGUE
# -------------------------
standings, season_matchups = load_regular_season_standings(CURRENT_YEAR)
standings = standings.dropna(subset=["DivisionKey"])

# -------------------------
# STEP 2: PICK DIVISION WINNERS
# Sleeper's default tiebreaker per the commissioner: Wins, then PointsFor.
# No known tiebreaker beyond that (H2H is explicitly NOT used) -- a genuine tie on
# both is flagged rather than guessed at.
# -------------------------
division_winners = []
unresolved_ties = []

for (league_id, league_name, division), group in standings.groupby(["LeagueID", "LeagueName", "DivisionKey"]):
    ranked = group.sort_values(["Wins", "PointsFor"], ascending=[False, False])
    top_wins, top_points = ranked.iloc[0][["Wins", "PointsFor"]]
    tied = ranked[(ranked["Wins"] == top_wins) & (ranked["PointsFor"] == top_points)]
    if len(tied) > 1:
        unresolved_ties.append((league_name, division, tied))
        print(f"WARNING: unresolved division-winner tie in {league_name} / {division}: "
              f"{', '.join(tied['OwnerName'])} all at {top_wins} wins / {top_points} points. "
              f"No known tiebreaker beyond Wins+PointsFor -- resolve manually.")
        continue
    winner = ranked.iloc[0]
    division_winners.append({
        "LeagueID": league_id,
        "LeagueName": league_name,
        "Division": division,
        "RosterID": winner["RosterID"],
        "OwnerName": winner["OwnerName"],
        "Wins": winner["Wins"],
        "PointsFor": winner["PointsFor"],
    })

division_winners_df = pd.DataFrame(
    division_winners,
    columns=["LeagueID", "LeagueName", "Division", "RosterID", "OwnerName", "Wins", "PointsFor"],
)
print(f"\nDivision winners determined: {len(division_winners_df)} "
      f"(expected up to {2 * standings['LeagueID'].nunique()} -- 2 per league, minus any ties above)")

if division_winners_df.empty:
    print("No division winners were determined at all -- nothing to pair for CCGs. "
          "Check the warnings above (missing Teams.csv divisions or unresolved ties).")
    sys.exit(1 if unresolved_ties else 0)

# -------------------------
# STEP 3: PAIR THE TWO DIVISION WINNERS PER LEAGUE, PULL WEEK-12 POINTS
# Sleeper's own Outcome/OpponentRosterID for week 12 is fictional -- it's just the
# next round-robin slot, not the real CCG opponent. We only trust each division
# winner's own PointsFor for week 12, then compare the two winners directly.
# -------------------------
week12 = week_points_lookup(season_matchups, CCG_WEEK)

results = []
for league_id, group in division_winners_df.groupby("LeagueID"):
    if len(group) != 2:
        print(f"WARNING: league {group['LeagueName'].iloc[0]} ({league_id}) has "
              f"{len(group)} division winner(s), not 2 -- skipping CCG for this league "
              f"(likely an unresolved tie above, or a missing division).")
        continue

    a, b = group.iloc[0], group.iloc[1]
    a_pts_row = week12[(week12["LeagueID"] == league_id) & (week12["RosterID"] == a["RosterID"])]
    b_pts_row = week12[(week12["LeagueID"] == league_id) & (week12["RosterID"] == b["RosterID"])]

    a_points = a_pts_row["Week12Points"].iloc[0] if not a_pts_row.empty else None
    b_points = b_pts_row["Week12Points"].iloc[0] if not b_pts_row.empty else None

    if a_points is None or b_points is None:
        status = "Pending"
        winner_owner = None
        margin = None
    else:
        status = "Final"
        if a_points > b_points:
            winner_owner, margin = a["OwnerName"], round(a_points - b_points, 2)
        elif b_points > a_points:
            winner_owner, margin = b["OwnerName"], round(b_points - a_points, 2)
        else:
            winner_owner, margin = None, 0.0
            print(f"WARNING: CCG tie in {a['LeagueName']} at week {CCG_WEEK} "
                  f"({a['OwnerName']} vs {b['OwnerName']}, both {a_points} points) -- "
                  f"no known tiebreaker for this case either, resolve manually.")

    for team, opponent, points, opp_points in [
        (a, b, a_points, b_points),
        (b, a, b_points, a_points),
    ]:
        results.append({
            "Year": CURRENT_YEAR,
            "Round": ROUND_NAME,
            "Week": CCG_WEEK,
            "LeagueID": league_id,
            "LeagueName": team["LeagueName"],
            "RosterID": team["RosterID"],
            "OwnerName": team["OwnerName"],
            "Division": team["Division"],
            "RegularSeasonWins": team["Wins"],
            "RegularSeasonPoints": team["PointsFor"],
            "OpponentRosterID": opponent["RosterID"],
            "OpponentName": opponent["OwnerName"],
            "OpponentDivision": opponent["Division"],
            "Points": points,
            "OpponentPoints": opp_points,
            "Outcome": ("Win" if winner_owner == team["OwnerName"]
                        else "Loss" if status == "Final" and winner_owner is not None
                        else "Tie" if status == "Final"
                        else "Pending"),
            "Margin": margin if status == "Final" else None,
            "Status": status,
        })

results_df = pd.DataFrame(results)

# -------------------------
# STEP 4: MERGE INTO data/Postseason_Season.csv
# Same accumulate-and-dedupe pattern as WeeklyAwards_Season.csv: rerunning this
# (e.g. once week 12 finishes) updates Pending rows to Final in place rather than
# duplicating them. Keyed on (Year, Round, LeagueID, RosterID).
# -------------------------
if os.path.exists(OUTPUT_PATH):
    existing_df = pd.read_csv(OUTPUT_PATH, dtype=str)
else:
    existing_df = pd.DataFrame()

if not existing_df.empty:
    # Only replace rows for this Round -- other rounds (Bowls, Playoff, NIT, once
    # built) live in the same file and must be left alone.
    existing_df = existing_df[
        ~((existing_df["Year"] == str(CURRENT_YEAR)) & (existing_df["Round"] == ROUND_NAME))
    ]

combined_df = pd.concat([existing_df, results_df], ignore_index=True)
combined_df.to_csv(OUTPUT_PATH, index=False)

print(f"\nWrote {len(results_df)} CCG rows for {CURRENT_YEAR} to {OUTPUT_PATH}")
finals = results_df[results_df["Status"] == "Final"]
pendings = results_df[results_df["Status"] == "Pending"]
print(f"  {len(finals)} rows Final, {len(pendings)} rows Pending (week {CCG_WEEK} not yet played)")
if unresolved_ties:
    print(f"\n{len(unresolved_ties)} division-winner tie(s) need manual resolution -- see warnings above.")
    sys.exit(1)
