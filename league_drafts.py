import pandas as pd
from sleeper_wrapper import League
import os

# Load league IDs file
league_ids_df = pd.read_csv("data/LeagueIDs_AllYears.csv")

all_drafts = []

for _, row in league_ids_df.iterrows():
    league_id = row['LeagueID']
    league_name = row['LeagueName']

    print(f"Processing drafts for {league_name} (LeagueID: {league_id})")

    try:
        league = League(league_id)
        league_drafts = league.get_all_drafts()  # ✅ correct method

        if league_drafts:
            for d in league_drafts:
                d["LeagueID"] = league_id
                d["LeagueName"] = league_name
            all_drafts.extend(league_drafts)
        else:
            print(f"  No drafts found for {league_name}")

    except Exception as e:
        print(f"  ERROR fetching drafts for {league_name}: {e}")

# Save results
if all_drafts:
    drafts_df = pd.DataFrame(all_drafts)
    os.makedirs("data", exist_ok=True)
    drafts_df.to_csv("data/Drafts_AllYears.csv", index=False)
    print(f"Saved {len(drafts_df)} draft rows to data/Drafts_AllYears.csv")
else:
    print("No draft data collected.")
