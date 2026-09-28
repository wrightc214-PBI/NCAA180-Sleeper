import pandas as pd
import datetime
import argparse
import os
import sys

from _postseason_common import load_regular_season_standings

# -------------------------
# CONFIG
# -------------------------
POSTSEASON_FILE = "data/Postseason_Season.csv"
OUTPUT_PATH = "data/PlayoffField_Season.csv"

AUTO_BID_ROUND = "CCG"
NUM_AUTO_BIDS = 15       # one per league, the CCG winner
NUM_AT_LARGE = 17        # rest of the 32-team field
FIELD_SIZE = NUM_AUTO_BIDS + NUM_AT_LARGE

# -------------------------
# ARGUMENT PARSER
# -------------------------
parser = argparse.ArgumentParser(description="Determine the 32-team playoff field (15 CCG-winner auto bids + 17 at-large).")
parser.add_argument("--year", type=int, help="Season year (defaults to current NFL year)")
args = parser.parse_args()

today = datetime.date.today()
CURRENT_YEAR = args.year or (today.year - 1 if today.month < 3 else today.year)
print(f"Season: {CURRENT_YEAR}")

# -------------------------
# STEP 1: AUTO BIDS -- the 15 CCG winners.
# Requires conference_championships.py to have already been run to completion
# (all 15 CCGs Final, no unresolved ties) -- until every CCG has a real winner,
# we can't know which teams are even eligible for an at-large bid.
# -------------------------
if not os.path.exists(POSTSEASON_FILE):
    print(f"FATAL: {POSTSEASON_FILE} doesn't exist yet -- run conference_championships.py first.")
    sys.exit(1)

postseason_df = pd.read_csv(POSTSEASON_FILE, dtype=str)
ccg_rows = postseason_df[
    (postseason_df["Year"] == str(CURRENT_YEAR)) & (postseason_df["Round"] == AUTO_BID_ROUND)
].copy()

if ccg_rows.empty:
    print(f"FATAL: no {AUTO_BID_ROUND} rows found for {CURRENT_YEAR} in {POSTSEASON_FILE} -- "
          f"run conference_championships.py first.")
    sys.exit(1)

not_final = ccg_rows[ccg_rows["Status"] != "Final"]
if not not_final.empty:
    leagues_pending = sorted(not_final["LeagueName"].unique())
    print(f"FATAL: {len(leagues_pending)} league(s) don't have a Final CCG result yet -- "
          f"can't determine the playoff field until every CCG is decided: {leagues_pending}")
    sys.exit(1)

auto_bids = ccg_rows[ccg_rows["Outcome"] == "Win"][["LeagueID", "RosterID"]].copy()
if len(auto_bids) != NUM_AUTO_BIDS:
    print(f"FATAL: expected {NUM_AUTO_BIDS} CCG winners, found {len(auto_bids)}. "
          f"Check for an unresolved CCG tie (Outcome='Tie') in {POSTSEASON_FILE}.")
    sys.exit(1)

auto_bid_keys = set(zip(auto_bids["LeagueID"], auto_bids["RosterID"]))
print(f"Auto bids confirmed: {len(auto_bid_keys)} CCG winners")

# -------------------------
# STEP 2: AT-LARGE POOL
# Regular season only (weeks 1-11) -- week 12 (CCG) points do NOT count toward
# at-large ranking, per the commissioner. Same Sleeper tiebreaker as CCG: Wins,
# then PointsFor, no H2H, no known tiebreaker beyond that.
# -------------------------
standings, _season_matchups = load_regular_season_standings(CURRENT_YEAR)
standings = standings.dropna(subset=["DivisionKey"])

is_auto_bid = standings.apply(lambda r: (r["LeagueID"], r["RosterID"]) in auto_bid_keys, axis=1)
pool = standings[~is_auto_bid].copy()
print(f"At-large pool: {len(pool)} teams competing for {NUM_AT_LARGE} spots "
      f"({len(standings)} total teams - {len(auto_bid_keys)} auto bids)")

pool = pool.sort_values(["Wins", "PointsFor"], ascending=[False, False]).reset_index(drop=True)

if len(pool) < NUM_AT_LARGE:
    print(f"FATAL: only {len(pool)} teams in the at-large pool, need {NUM_AT_LARGE}. "
          f"Check standings/auto-bid data.")
    sys.exit(1)

# Determine the cutoff score (Wins, PointsFor) at the last at-large spot, and check
# whether it's a clean cutoff or a tie spanning the boundary -- same "flag, don't
# guess" policy as conference_championships.py's tiebreaker handling.
cutoff_wins, cutoff_points = pool.iloc[NUM_AT_LARGE - 1][["Wins", "PointsFor"]]
at_cutoff_score = pool[(pool["Wins"] == cutoff_wins) & (pool["PointsFor"] == cutoff_points)]

if len(at_cutoff_score) > 1:
    # More than one team shares the exact score at the last spot -- can't cut cleanly.
    above_cutoff = pool[
        (pool["Wins"] > cutoff_wins) |
        ((pool["Wins"] == cutoff_wins) & (pool["PointsFor"] > cutoff_points))
    ]
    spots_remaining = NUM_AT_LARGE - len(above_cutoff)
    print(f"WARNING: {len(at_cutoff_score)} teams are tied at {cutoff_wins} wins / {cutoff_points} "
          f"points for the last {spots_remaining} at-large spot(s): "
          f"{', '.join(at_cutoff_score['OwnerName'])}. No known tiebreaker beyond Wins+PointsFor "
          f"-- resolve manually before finalizing the field.")
    at_large = above_cutoff.copy()
    bubble_tied = at_cutoff_score.copy()
    field_complete = False
else:
    at_large = pool.iloc[:NUM_AT_LARGE].copy()
    bubble_tied = pd.DataFrame()
    field_complete = True

# -------------------------
# STEP 3: ASSEMBLE FIELD
# -------------------------
auto_bid_teams = standings.merge(
    pd.DataFrame(list(auto_bid_keys), columns=["LeagueID", "RosterID"]),
    on=["LeagueID", "RosterID"], how="inner",
)

rows = []
for _, row in auto_bid_teams.iterrows():
    rows.append({
        "Year": CURRENT_YEAR, "LeagueID": row["LeagueID"], "LeagueName": row["LeagueName"],
        "RosterID": row["RosterID"], "OwnerName": row["OwnerName"], "Division": row["DivisionKey"],
        "BidType": "Auto (CCG winner)", "RegularSeasonWins": row["Wins"],
        "RegularSeasonPoints": row["PointsFor"],
    })
for _, row in at_large.iterrows():
    rows.append({
        "Year": CURRENT_YEAR, "LeagueID": row["LeagueID"], "LeagueName": row["LeagueName"],
        "RosterID": row["RosterID"], "OwnerName": row["OwnerName"], "Division": row["DivisionKey"],
        "BidType": "At-Large", "RegularSeasonWins": row["Wins"], "RegularSeasonPoints": row["PointsFor"],
    })
for _, row in bubble_tied.iterrows():
    rows.append({
        "Year": CURRENT_YEAR, "LeagueID": row["LeagueID"], "LeagueName": row["LeagueName"],
        "RosterID": row["RosterID"], "OwnerName": row["OwnerName"], "Division": row["DivisionKey"],
        "BidType": "Tied - Unresolved", "RegularSeasonWins": row["Wins"], "RegularSeasonPoints": row["PointsFor"],
    })

field_df = pd.DataFrame(rows)

# -------------------------
# STEP 4: WRITE (replace this year's field entirely -- it's a full recompute, not
# an accumulation like Postseason_Season.csv's game-by-game results).
# -------------------------
if os.path.exists(OUTPUT_PATH):
    existing_df = pd.read_csv(OUTPUT_PATH, dtype=str)
    existing_df = existing_df[existing_df["Year"] != str(CURRENT_YEAR)]
else:
    existing_df = pd.DataFrame()

combined_df = pd.concat([existing_df, field_df], ignore_index=True)
combined_df.to_csv(OUTPUT_PATH, index=False)

print(f"\nWrote {len(field_df)} rows for {CURRENT_YEAR} to {OUTPUT_PATH} "
      f"({len(auto_bid_teams)} auto, {len(at_large)} at-large"
      + (f", {len(bubble_tied)} unresolved-tied" if len(bubble_tied) else "") + ")")

if not field_complete:
    print(f"\nField is INCOMPLETE -- {len(bubble_tied)} team(s) tied for the last at-large spot(s) "
          f"need manual resolution. Rerun after deciding.")
    sys.exit(1)
