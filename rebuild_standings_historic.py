import pandas as pd
import datetime

today = datetime.date.today()
CURRENT_YEAR = today.year - 1 if today.month < 3 else today.year

# -------------------------
# REGULAR-SEASON RECORD (weeks 1-11 only) FROM HISTORIC MATCHUPS
# -------------------------
matchups_df = pd.read_csv("data/Matchups_Historic.csv", dtype=str)
matchups_df["Year"] = matchups_df["Year"].astype(int)
matchups_df["PointsFor"] = matchups_df["PointsFor"].astype(float)
matchups_df["PointsAgainst"] = matchups_df["PointsAgainst"].astype(float)

regular_season = matchups_df[matchups_df["IsRegularSeason"].astype(str) == "True"]

standings_agg = regular_season.groupby(["Year", "LeagueID", "RosterID"]).agg(
    Wins=("Outcome", lambda x: (x == "Win").sum()),
    Losses=("Outcome", lambda x: (x == "Loss").sum()),
    PointsFor=("PointsFor", "sum"),
    PointsAgainst=("PointsAgainst", "sum")
).reset_index()

# -------------------------
# METADATA (LeagueName, OwnerID, OwnerName, Division, DivisionName) FROM THE OLD ALLYEARS FILE
# -------------------------
meta_df = pd.read_csv("data/Users_AllYears.csv", dtype=str)
meta_df["Year"] = meta_df["Year"].astype(int)
meta_df = meta_df[meta_df["Year"] < CURRENT_YEAR]
meta_df = meta_df[["Year", "LeagueID", "LeagueName", "RosterID", "OwnerID", "OwnerName", "Division", "DivisionName"]]

# -------------------------
# MERGE
# -------------------------
merged = meta_df.merge(standings_agg, on=["Year", "LeagueID", "RosterID"], how="left")
merged[["Wins", "Losses"]] = merged[["Wins", "Losses"]].fillna(0).astype(int)
merged[["PointsFor", "PointsAgainst"]] = merged[["PointsFor", "PointsAgainst"]].fillna(0).round(2)

out_file = "data/Standings_Historic.csv"
merged.to_csv(out_file, index=False)
print(f"Saved {len(merged)} roster rows (regular season, weeks 1-11) to {out_file}")
