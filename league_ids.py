#!/usr/bin/env python3
import requests
import pandas as pd
import datetime
import os
import time

USER_ID = "731808894699028480"
BASE = "https://api.sleeper.app/v1"
START_YEAR = 2020
END_YEAR = datetime.datetime.now().year

OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "NCAA180-Sleeper/1.0"})

all_leagues = []

for year in range(START_YEAR, END_YEAR + 1):
    url = f"{BASE}/user/{USER_ID}/leagues/nfl/{year}"
    print(f"Fetching leagues for {year} -> {url}")
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        leagues = resp.json()
    except Exception as e:
        print(f"  ERROR fetching year {year}: {e}")
        leagues = []

    for league in leagues:
        all_leagues.append({
            "Year": year,
            "LeagueID": league.get("league_id"),
            "LeagueName": league.get("name"),
            "Division1": league.get("metadata", {}).get("division_1"),
            "Division2": league.get("metadata", {}).get("division_2")
        })

    # polite pause to avoid hitting rate limits
    time.sleep(1)

df = pd.DataFrame(all_leagues)
out_file = os.path.join(OUTPUT_DIR, "LeagueIDs_AllYears.csv")
df.to_csv(out_file, index=False)
print(f"✅ Saved {len(df)} league records to {out_file}")
