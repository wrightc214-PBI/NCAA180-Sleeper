import pandas as pd
import datetime

today = datetime.date.today()
CURRENT_YEAR = today.year - 1 if today.month < 3 else today.year

# Matchups
matchups = pd.read_csv("data/Matchups_AllYears.csv", dtype=str)
matchups["Year"] = matchups["Year"].astype(int)
matchups["StarterPoints"] = pd.to_numeric(matchups["StarterPoints"], errors="coerce").round(2)
matchups["BenchPoints"] = pd.to_numeric(matchups["BenchPoints"], errors="coerce").round(2)
matchups[matchups["Year"] < CURRENT_YEAR].to_csv("data/Matchups_Historic.csv", index=False)
print(f"Wrote Matchups_Historic.csv (years < {CURRENT_YEAR})")

# Standings
standings = pd.read_csv("data/Users_AllYears.csv", dtype=str)
standings["Year"] = standings["Year"].astype(int)
standings[standings["Year"] < CURRENT_YEAR].to_csv("data/Standings_Historic.csv", index=False)
print(f"Wrote Standings_Historic.csv (years < {CURRENT_YEAR})")
