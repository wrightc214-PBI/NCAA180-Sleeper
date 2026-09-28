"""
Shared helpers for postseason scripts (conference_championships.py, playoff_field.py,
bowls.py, and future NIT script).

Not a standalone script -- imported only. Follows the same CWD-is-repo-root
convention as every other script in this folder.
"""
import pandas as pd

MATCHUPS_FILE = "data/Matchups_Season.csv"
TEAMS_FILE = "data/Teams.csv"


def load_regular_season_standings(year):
    """
    Returns one row per team with its regular-season (weeks 1-11) Wins and
    PointsFor, joined to its League and Division from Teams.csv.

    Columns: LeagueID, LeagueName, RosterID, OwnerName, DivisionKey, Wins, PointsFor, Team

    Sleeper's default tiebreaker (confirmed by the commissioner): Wins, then
    PointsFor. H2H is explicitly NOT used. There's no known tiebreaker if both
    are exactly equal -- callers are responsible for detecting and flagging
    that themselves (see conference_championships.py's tie-handling), this
    function does not resolve or hide ties.
    """
    matchups_df = pd.read_csv(MATCHUPS_FILE, dtype=str)
    matchups_df["Year"] = matchups_df["Year"].astype(str)
    matchups_df["Week"] = matchups_df["Week"].astype(int)
    matchups_df["PointsFor"] = matchups_df["PointsFor"].astype(float)
    matchups_df["IsRegularSeason"] = matchups_df["IsRegularSeason"].astype(str).str.lower() == "true"

    teams_df = pd.read_csv(TEAMS_FILE, dtype=str)
    teams_df["DivisionKey"] = teams_df["Division Name"].str.strip().str.upper()

    season_matchups = matchups_df[matchups_df["Year"] == str(year)].copy()
    if season_matchups.empty:
        raise ValueError(f"No matchup data found for {year} in {MATCHUPS_FILE}")

    regular = season_matchups[season_matchups["IsRegularSeason"]].copy()
    if regular.empty:
        raise ValueError("No regular-season rows found -- has season data been collected yet?")

    regular["Win"] = (regular["Outcome"] == "Win").astype(int)

    standings = (
        regular.groupby(["LeagueID", "LeagueName", "RosterID", "OwnerName"], as_index=False)
        .agg(Wins=("Win", "sum"), PointsFor=("PointsFor", "sum"))
    )

    teams_lookup = teams_df.rename(columns={"League": "LeagueName", "Roster ID": "RosterID"})[
        ["LeagueName", "RosterID", "DivisionKey", "Team"]
    ]
    standings = standings.merge(teams_lookup, on=["LeagueName", "RosterID"], how="left")

    missing_division = standings[standings["DivisionKey"].isna()]
    if not missing_division.empty:
        print("WARNING: could not find a Teams.csv division for these League/RosterID rows:")
        print(missing_division[["LeagueName", "RosterID", "OwnerName"]].to_string(index=False))

    return standings, season_matchups


def week_points_lookup(season_matchups, week):
    """Each team's own PointsFor for a given week, keyed by (LeagueID, RosterID).
    Deliberately ignores Sleeper's Outcome/OpponentRosterID for postseason weeks --
    those are fictional round-robin artifacts, not the real bracket."""
    wk = season_matchups[season_matchups["Week"] == week][["LeagueID", "RosterID", "PointsFor"]]
    return wk.rename(columns={"PointsFor": f"Week{week}Points"})
