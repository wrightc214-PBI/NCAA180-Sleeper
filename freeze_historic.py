import pandas as pd
import datetime

today = datetime.date.today()
CURRENT_YEAR = today.year - 1 if today.month < 3 else today.year

# Matchups
matchups = pd.read_csv("data/Matchups_AllYears.csv")
matchups[matchups["Year"] < CURRENT_YEAR].to_csv("data/Matchups_Historic.csv", index=False)
print(f"Wrote Matchups_Historic.csv (years < {CURRENT_YEAR})")

# Standings
standings = pd.read_csv("data/Users_AllYears.csv")
standings[standings["Year"] < CURRENT_YEAR].to_csv("data/Standings_Historic.csv", index=False)
print(f"Wrote Standings_Historic.csv (years < {CURRENT_YEAR})")

# Scores
scores = pd.read_csv("data/Scores.csv")
scores["LeagueYear"] = scores["LeagueYear"].astype(int)
scores[scores["LeagueYear"] < CURRENT_YEAR].to_csv("data/Scores_Historic.csv", index=False)
print(f"Wrote Scores_Historic.csv (years < {CURRENT_YEAR})")
