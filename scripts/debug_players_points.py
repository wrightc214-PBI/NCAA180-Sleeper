import requests
import json
import pandas as pd

# One-time diagnostic: dump the raw shape of a single matchup's players_points
# / starters / starters_points fields so we can see what Sleeper is actually
# returning, since players_points is coming back ~all-zero in production.

league_df = pd.read_csv("data/LeagueIDs_AllYears.csv", dtype=str)
league_id = league_df.loc[league_df["Year"] == "2026", "LeagueID"].iloc[0]
week = 2

url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"
resp = requests.get(url, timeout=10)
resp.raise_for_status()
matchups = resp.json()

print(f"League: {league_id}, Week: {week}, matchup entries: {len(matchups)}")
print()

m = matchups[0]
print("Top-level keys:", list(m.keys()))
print()
print("roster_id:", m.get("roster_id"))
print("points:", m.get("points"))
print()
print("starters:", m.get("starters"))
print()
print("starters_points:", m.get("starters_points"))
print()
pp = m.get("players_points")
print("players_points type:", type(pp))
print("players_points:", json.dumps(pp, indent=2))
print()
print("players (full roster list, if present):", m.get("players"))
