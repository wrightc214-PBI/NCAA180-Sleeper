import pandas as pd
import datetime
import argparse
import os
import sys
import random

from _postseason_common import load_regular_season_standings, week_points_lookup

# -------------------------
# CONFIG
# -------------------------
POSTSEASON_FILE = "data/Postseason_Season.csv"
PLAYOFF_FIELD_FILE = "data/PlayoffField_Season.csv"
TEAM_REGIONS_FILE = "data/TeamRegions.csv"
LEAGUE_SHORTNAMES_FILE = "data/LeagueShortNames.csv"

ROUND_NAME = "Bowl"
MIN_BOWL_WINS = 6          # base bowl eligibility: 6+ regular-season wins, not in the playoff field
BUMP_UP_WINS = 5           # if short on 6-win teams, bump up 5-win teams by PointsFor
NUM_TEAMS_NEEDED = 64      # 32 bowls x 2 teams

# The full bowl table, commissioner-confirmed 2026-09-27/28, processed strictly top-down.
# "rank" bowls draw the next-best remaining team pair from the pool (the #1 overall team
# is held aside for the Holiday Bowl before any rank bowl runs -- see "reserved_plus_league").
# "conf_pair" bowls take the best remaining team from each of two named leagues (short names,
# resolved against data/LeagueShortNames.csv).
# "favored_conf_pair" tries a conf_pair first, falls back to a plain random pair if either
# league has no remaining eligible team.
# "favored_teams" tries to include specific named teams (if still available and not already
# used elsewhere), falls back to a plain random partner/pair otherwise.
# "random" bowls pick uniformly at random from the remaining pool, subject to the global
# no-same-league constraint and any region/state exclusion given.
BOWL_SLOTS = [
    {"name": "Tangerine Bowl",     "week": 16, "type": "rank"},
    {"name": "Liberty Bowl",       "week": 16, "type": "rank"},
    {"name": "Independence Bowl",  "week": 16, "type": "rank"},
    {"name": "New Orleans Bowl",   "week": 16, "type": "rank"},
    {"name": "Gator Bowl",         "week": 16, "type": "rank"},
    {"name": "Holiday Bowl",       "week": 16, "type": "reserved_plus_league", "league": "Wild"},
    {"name": "Music City Bowl",    "week": 16, "type": "conf_pair",         "leagues": ("HBCU", "Ivy")},
    {"name": "Alamo Bowl",         "week": 16, "type": "conf_pair",         "leagues": ("CUSA", "Pioneer")},
    {"name": "Aloha Bowl",         "week": 15, "type": "conf_pair",         "leagues": ("PAC 12", "Big 12")},
    {"name": "Citrus Bowl",        "week": 15, "type": "conf_pair",         "leagues": ("Mountain West", "Sun Belt")},
    {"name": "Sun Bowl",           "week": 15, "type": "conf_pair",         "leagues": ("ACC", "Big East")},
    {"name": "Gasparilla Bowl",    "week": 15, "type": "conf_pair",         "leagues": ("SEC", "Big 10")},
    {"name": "Bahamas Bowl",       "week": 15, "type": "conf_pair",         "leagues": ("Big Sky", "Ohio Valley")},
    {"name": "Las Vegas Bowl",     "week": 15, "type": "favored_conf_pair", "leagues": ("Mountain West", "PAC 12")},
    {"name": "Military Bowl",      "week": 15, "type": "favored_teams",     "teams": ("Texas A&M", "Vanderbilt")},
    {"name": "Armed Forces Bowl",  "week": 15, "type": "favored_teams",     "teams": ("Army", "Air Force")},
    {"name": "Poinsettia Bowl",    "week": 14, "type": "favored_teams",     "teams": ("Navy",)},
    {"name": "Texas Bowl",         "week": 14, "type": "random",            "max_one_state": "TX"},
    {"name": "Idaho Potato Bowl",  "week": 14, "type": "random",            "exclude_state": "ID"},
    {"name": "New Mexico Bowl",    "week": 14, "type": "random",            "exclude_state": "NM"},
    {"name": "Arizona Bowl",       "week": 14, "type": "random",            "exclude_state": "AZ"},
    {"name": "Brooklyn Bowl",      "week": 14, "type": "random",            "exclude_region": "Northeast"},
    {"name": "Miami Beach Bowl",   "week": 14, "type": "random",            "exclude_state": "FL"},
    {"name": "Fenway Bowl",        "week": 13, "type": "random",            "exclude_region": "Northeast"},
    {"name": "International Bowl", "week": 13, "type": "random"},
    {"name": "Birmingham Bowl",    "week": 13, "type": "random",            "exclude_state": "AL"},
    {"name": "Pinstripe Bowl",     "week": 13, "type": "random",            "exclude_region": "Northeast"},
    {"name": "Boca Raton Bowl",    "week": 13, "type": "random",            "exclude_state": "FL"},
    {"name": "Cure Bowl",          "week": 13, "type": "random",            "exclude_state": "FL"},
    {"name": "LA Bowl",            "week": 13, "type": "random",            "exclude_region": "SoCal"},
    {"name": "Camellia Bowl",      "week": None, "type": "random",         "exclude_state": "AL"},
    {"name": "TBA Bowl",           "week": None, "type": "random"},
]
assert len(BOWL_SLOTS) == 32, f"Expected 32 bowls, got {len(BOWL_SLOTS)}"

# -------------------------
# ARGUMENT PARSER
# -------------------------
parser = argparse.ArgumentParser(description="Determine the 32-bowl field and pairings for non-playoff teams.")
parser.add_argument("--year", type=int, help="Season year (defaults to current NFL year)")
args = parser.parse_args()

today = datetime.date.today()
CURRENT_YEAR = args.year or (today.year - 1 if today.month < 3 else today.year)
print(f"Season: {CURRENT_YEAR}")


def rank_sort(df):
    return df.sort_values(["Wins", "PointsFor"], ascending=[False, False]).reset_index(drop=True)


def load_league_shortnames():
    df = pd.read_csv(LEAGUE_SHORTNAMES_FILE, dtype=str)
    return dict(zip(df["Short Name"], df["Full Name"]))


def load_team_regions():
    df = pd.read_csv(TEAM_REGIONS_FILE, dtype=str)
    df["Region"] = df["Region"].fillna("")
    return df


SHORTNAME_TO_LEAGUE = load_league_shortnames()


def league_full(short_name):
    full = SHORTNAME_TO_LEAGUE.get(short_name)
    if full is None:
        raise ValueError(f"Unknown league short name '{short_name}' -- check {LEAGUE_SHORTNAMES_FILE}")
    return full


def best_in_league(pool, league_full_name, exclude_league_id=None):
    candidates = [t for t in pool if t["LeagueName"] == league_full_name
                  and t["LeagueID"] != exclude_league_id]
    if not candidates:
        return None
    return sorted(candidates, key=lambda t: (-t["Wins"], -t["PointsFor"]))[0]


def find_team(pool, team_name):
    for t in pool:
        if t["Team"] == team_name:
            return t
    return None


def pick_rank_pair(pool):
    """Top team in `pool` is side A; side B is the next-best remaining team whose
    league differs from A's. A same-league conflict is resolved by skipping down
    the ranked list for B -- the skipped team(s) stay in the pool untouched for a
    later slot, they are not discarded."""
    ranked = sorted(pool, key=lambda t: (-t["Wins"], -t["PointsFor"]))
    if len(ranked) < 2:
        return None
    a = ranked[0]
    for candidate in ranked[1:]:
        if candidate["LeagueID"] != a["LeagueID"]:
            return (a, candidate)
    return None  # everyone left is in A's own league -- can't pair, leave unfilled


def pick_conf_pair(pool, league_a_short, league_b_short):
    league_a = league_full(league_a_short)
    league_b = league_full(league_b_short)
    a = best_in_league(pool, league_a)
    b = best_in_league(pool, league_b)
    if a is None or b is None:
        return None
    return (a, b)


def pick_random_pair(pool, exclude_state=None, exclude_region=None, max_one_state=None):
    candidates = pool
    if exclude_state:
        candidates = [t for t in candidates if t["State"] != exclude_state]
    if exclude_region:
        candidates = [t for t in candidates if t["Region"] != exclude_region]
    if len(candidates) < 2:
        return None
    shuffled = candidates[:]
    random.shuffle(shuffled)
    for i, a in enumerate(shuffled):
        for b in shuffled[i + 1:]:
            if a["LeagueID"] == b["LeagueID"]:
                continue
            if max_one_state and a["State"] == max_one_state and b["State"] == max_one_state:
                continue
            return (a, b)
    return None


def pick_favored_teams(pool, favored_names, max_one_state=None, exclude_state=None, exclude_region=None):
    present = [find_team(pool, name) for name in favored_names]
    present = [t for t in present if t is not None]
    if len(favored_names) == 2 and len(present) == 2 and present[0]["LeagueID"] != present[1]["LeagueID"]:
        return (present[0], present[1])
    if len(present) == 1:
        a = present[0]
        candidates = [t for t in pool if t["Team"] != a["Team"] and t["LeagueID"] != a["LeagueID"]]
        if exclude_state:
            candidates = [t for t in candidates if t["State"] != exclude_state]
        if exclude_region:
            candidates = [t for t in candidates if t["Region"] != exclude_region]
        if not candidates:
            return None
        b = random.choice(candidates)
        return (a, b)
    # neither present, or both present but same league -- fall back to plain random
    return pick_random_pair(pool, exclude_state=exclude_state, exclude_region=exclude_region,
                             max_one_state=max_one_state)


def compute_assignments(pool_records):
    pool = [dict(r) for r in pool_records]  # working copy
    if not pool:
        return [], [b["name"] for b in BOWL_SLOTS]

    reserved = sorted(pool, key=lambda t: (-t["Wins"], -t["PointsFor"]))[0]
    pool = [t for t in pool if t["Team"] != reserved["Team"]]

    assignments = []   # list of (bowl, teamA, teamB)
    unfilled = []

    for bowl in BOWL_SLOTS:
        btype = bowl["type"]
        pair = None

        if btype == "reserved_plus_league":
            b = best_in_league(pool, league_full(bowl["league"]), exclude_league_id=reserved["LeagueID"])
            pair = (reserved, b) if b is not None else None
        elif btype == "rank":
            pair = pick_rank_pair(pool)
        elif btype == "conf_pair":
            pair = pick_conf_pair(pool, *bowl["leagues"])
        elif btype == "favored_conf_pair":
            pair = pick_conf_pair(pool, *bowl["leagues"])
            if pair is None:
                pair = pick_random_pair(pool)
        elif btype == "favored_teams":
            pair = pick_favored_teams(pool, bowl["teams"])
        elif btype == "random":
            pair = pick_random_pair(pool, exclude_state=bowl.get("exclude_state"),
                                     exclude_region=bowl.get("exclude_region"),
                                     max_one_state=bowl.get("max_one_state"))
        else:
            raise ValueError(f"Unknown bowl type '{btype}' for {bowl['name']}")

        if pair is None:
            unfilled.append(bowl["name"])
            continue

        a, b = pair
        assignments.append((bowl, a, b))
        pool = [t for t in pool if t["Team"] not in (a["Team"], b["Team"])]

    if pool:
        print(f"WARNING: {len(pool)} eligible team(s) could not be placed in any bowl "
              f"(likely same-league lockups): {', '.join(t['Team'] for t in pool)}")

    return assignments, unfilled


# -------------------------
# STEP 1: DEPENDENCIES -- playoff field must be complete for this year.
# -------------------------
if not os.path.exists(PLAYOFF_FIELD_FILE):
    print(f"FATAL: {PLAYOFF_FIELD_FILE} doesn't exist yet -- run playoff_field.py first.")
    sys.exit(1)

playoff_df = pd.read_csv(PLAYOFF_FIELD_FILE, dtype=str)
playoff_year = playoff_df[playoff_df["Year"] == str(CURRENT_YEAR)]
if playoff_year.empty:
    print(f"FATAL: no playoff field found for {CURRENT_YEAR} in {PLAYOFF_FIELD_FILE} -- run playoff_field.py first.")
    sys.exit(1)
if (playoff_year["BidType"] == "Tied - Unresolved").any():
    print(f"FATAL: playoff field for {CURRENT_YEAR} has unresolved bubble ties -- resolve before running bowls.py.")
    sys.exit(1)

playoff_keys = set(zip(playoff_year["LeagueID"], playoff_year["RosterID"]))

# -------------------------
# STEP 1b: LOCK CHECK -- bowl pairings are randomly generated, so once written they
# must NEVER be recomputed on a rerun (that would reshuffle a done deal every time the
# workflow fires). If this year's Bowl rows already exist, skip straight past all the
# pool-building/assignment logic below and only refresh scores.
# -------------------------
if os.path.exists(POSTSEASON_FILE):
    existing_df = pd.read_csv(POSTSEASON_FILE, dtype=str)
else:
    existing_df = pd.DataFrame()

existing_bowl_rows = pd.DataFrame()
if not existing_df.empty:
    existing_bowl_rows = existing_df[
        (existing_df["Year"] == str(CURRENT_YEAR)) & (existing_df["Round"] == ROUND_NAME)
    ].copy()

ALREADY_LOCKED = not existing_bowl_rows.empty

if ALREADY_LOCKED:
    print(f"Bowl pairings for {CURRENT_YEAR} are already locked in ({len(existing_bowl_rows)} rows) -- "
          f"refreshing scores/status only, not reassigning teams.")
    _, season_matchups = load_regular_season_standings(CURRENT_YEAR)
else:
    # -------------------------
    # STEP 2: BUILD THE BOWL-ELIGIBLE POOL
    # -------------------------
    standings, season_matchups = load_regular_season_standings(CURRENT_YEAR)
    standings = standings.dropna(subset=["DivisionKey"])
    regions_df = load_team_regions()
    standings = standings.merge(regions_df, on="Team", how="left")

    no_region = standings[standings["State"].isna()]
    if not no_region.empty:
        print(f"WARNING: {len(no_region)} team(s) have no entry in {TEAM_REGIONS_FILE} -- "
              f"geographic exclusions won't apply to them: {', '.join(no_region['Team'])}")
    standings["State"] = standings["State"].fillna("")
    standings["Region"] = standings["Region"].fillna("")

    is_playoff = standings.apply(lambda r: (r["LeagueID"], r["RosterID"]) in playoff_keys, axis=1)
    non_playoff = standings[~is_playoff].copy()

    six_win_pool = rank_sort(non_playoff[non_playoff["Wins"] >= MIN_BOWL_WINS].copy())
    pool_records = six_win_pool.to_dict("records")

    if len(pool_records) < NUM_TEAMS_NEEDED:
        shortfall = NUM_TEAMS_NEEDED - len(pool_records)
        five_win_pool = rank_sort(non_playoff[non_playoff["Wins"] == BUMP_UP_WINS].copy()).to_dict("records")
        bumped = five_win_pool[:shortfall]
        if bumped:
            print(f"Bowl pool short by {shortfall} -- bumping up {len(bumped)} highest-scoring "
                  f"5-win team(s) instead of sending them to the NIT: "
                  + ", ".join(f"{b['Team']} ({b['PointsFor']} pts)" for b in bumped))
        pool_records = pool_records + bumped
        pool_records = sorted(pool_records, key=lambda r: (-r["Wins"], -r["PointsFor"]))

    if len(pool_records) > NUM_TEAMS_NEEDED:
        overflow = pool_records[NUM_TEAMS_NEEDED:]
        pool_records = pool_records[:NUM_TEAMS_NEEDED]
        print(f"WARNING: {len(overflow)} more 6+-win team(s) than bowl slots exist -- the lowest-ranked "
              f"of them fall through to the NIT instead (assumption -- flag if this should work differently): "
              + ", ".join(f"{o['Team']} ({o['Wins']}-{o['PointsFor']})" for o in overflow))

    if len(pool_records) < NUM_TEAMS_NEEDED:
        print(f"WARNING: only {len(pool_records)} eligible teams for {NUM_TEAMS_NEEDED} bowl slots even after "
              f"the 5-win bump-up -- the lowest-priority bowls (bottom of the table) will be left unfilled.")

    print(f"Bowl-eligible pool: {len(pool_records)} teams for {NUM_TEAMS_NEEDED} slots")

    # -------------------------
    # STEP 3: PROCESS THE TABLE TOP-DOWN
    # -------------------------
    assignments, unfilled_bowls = compute_assignments(pool_records)

# -------------------------
# STEP 4a: RERUN PATH -- refresh scores/status for already-locked pairings only.
# -------------------------
if ALREADY_LOCKED:
    results = []
    for _, row in existing_bowl_rows.iterrows():
        week = row["Week"]
        if pd.isna(week) or str(week).strip().lower() in ("", "none", "nan"):
            results.append(row.to_dict())
            continue
        week_int = int(float(week))
        wk = week_points_lookup(season_matchups, week_int)
        my_pts = wk[(wk["LeagueID"] == row["LeagueID"]) & (wk["RosterID"] == row["RosterID"])]
        row_out = row.to_dict()
        if not my_pts.empty:
            row_out["Points"] = my_pts[f"Week{week_int}Points"].iloc[0]
        results.append(row_out)

    results_df = pd.DataFrame(results)
    for bowl_name, game in results_df.groupby("BowlName"):
        if len(game) != 2:
            continue
        i0, i1 = game.index[0], game.index[1]
        p0, p1 = results_df.loc[i0, "Points"], results_df.loc[i1, "Points"]
        if pd.isna(p0) or pd.isna(p1) or p0 in ("", None) or p1 in ("", None):
            continue
        p0f, p1f = float(p0), float(p1)
        results_df.loc[i0, "OpponentPoints"] = p1f
        results_df.loc[i1, "OpponentPoints"] = p0f
        if p0f == p1f:
            results_df.loc[[i0, i1], "Status"] = "Final"
            results_df.loc[[i0, i1], "Outcome"] = "Tie"
            results_df.loc[[i0, i1], "Margin"] = 0.0
        else:
            results_df.loc[i0, "Status"] = "Final"
            results_df.loc[i1, "Status"] = "Final"
            results_df.loc[i0, "Outcome"] = "Win" if p0f > p1f else "Loss"
            results_df.loc[i1, "Outcome"] = "Win" if p1f > p0f else "Loss"
            results_df.loc[i0, "Margin"] = round(abs(p0f - p1f), 2)
            results_df.loc[i1, "Margin"] = round(abs(p0f - p1f), 2)

    other_rounds = existing_df[~((existing_df["Year"] == str(CURRENT_YEAR)) & (existing_df["Round"] == ROUND_NAME))]
    combined_df = pd.concat([other_rounds, results_df], ignore_index=True)
    combined_df.to_csv(POSTSEASON_FILE, index=False)
    print(f"Refreshed {len(results_df)} Bowl rows for {CURRENT_YEAR}.")
    sys.exit(0)

# -------------------------
# STEP 4b: FIRST RUN -- write the newly-generated pairings.
# -------------------------
rows = []
for bowl, a, b in assignments:
    week = bowl["week"]
    if week is not None:
        wk = week_points_lookup(season_matchups, week)
        a_pts_row = wk[(wk["LeagueID"] == a["LeagueID"]) & (wk["RosterID"] == a["RosterID"])]
        b_pts_row = wk[(wk["LeagueID"] == b["LeagueID"]) & (wk["RosterID"] == b["RosterID"])]
        a_points = a_pts_row[f"Week{week}Points"].iloc[0] if not a_pts_row.empty else None
        b_points = b_pts_row[f"Week{week}Points"].iloc[0] if not b_pts_row.empty else None
    else:
        a_points = None
        b_points = None

    if a_points is None or b_points is None:
        status, outcome_a, outcome_b, margin = "Pending", "Pending", "Pending", None
    elif a_points == b_points:
        status, outcome_a, outcome_b, margin = "Final", "Tie", "Tie", 0.0
    else:
        status = "Final"
        margin = round(abs(a_points - b_points), 2)
        outcome_a = "Win" if a_points > b_points else "Loss"
        outcome_b = "Win" if b_points > a_points else "Loss"

    for team, opponent, points, opp_points, outcome in [
        (a, b, a_points, b_points, outcome_a),
        (b, a, b_points, a_points, outcome_b),
    ]:
        rows.append({
            "Year": CURRENT_YEAR,
            "Round": ROUND_NAME,
            "BowlName": bowl["name"],
            "Week": week,
            "LeagueID": team["LeagueID"],
            "LeagueName": team["LeagueName"],
            "RosterID": team["RosterID"],
            "OwnerName": team["OwnerName"],
            "Team": team["Team"],
            "RegularSeasonWins": team["Wins"],
            "RegularSeasonPoints": team["PointsFor"],
            "OpponentRosterID": opponent["RosterID"],
            "OpponentName": opponent["OwnerName"],
            "OpponentTeam": opponent["Team"],
            "OpponentLeague": opponent["LeagueName"],
            "Points": points,
            "OpponentPoints": opp_points,
            "Outcome": outcome,
            "Margin": margin,
            "Status": status,
        })

results_df = pd.DataFrame(rows)
other_rounds = existing_df[~((existing_df["Year"] == str(CURRENT_YEAR)) & (existing_df["Round"] == ROUND_NAME))] \
    if not existing_df.empty else pd.DataFrame()
combined_df = pd.concat([other_rounds, results_df], ignore_index=True)
combined_df.to_csv(POSTSEASON_FILE, index=False)

print(f"\nWrote {len(results_df)} Bowl rows ({len(assignments)} games) for {CURRENT_YEAR} to {POSTSEASON_FILE}")
if unfilled_bowls:
    print(f"\n{len(unfilled_bowls)} bowl(s) could NOT be filled (ran out of eligible teams): {unfilled_bowls}")
    sys.exit(1)
