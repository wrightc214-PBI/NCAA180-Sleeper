import pandas as pd
from sleeper_wrapper import League, Drafts
import os

# Load league IDs file
league_ids_df = pd.read_csv("data/LeagueIDs_AllYears.csv")

all_draft_picks = []

for _, row in league_ids_df.iterrows():
    league_id = row['LeagueID']
    league_name = row['LeagueName']

    print(f"Processing drafts for {league_name} (LeagueID: {league_id})")

    try:
        league = League(league_id)
        league_drafts = league.get_all_drafts()

        if league_drafts:
            for d in league_drafts:
                draft_id = d["draft_id"]

                try:
                    draft = Drafts(draft_id)
                    picks = draft.get_all_picks()  # ✅ picks for this draft

                    if picks:
                        for p in picks:
                            p["LeagueID"] = league_id
                            p["LeagueName"] = league_name
                            p["DraftID"] = draft_id
                        all_draft_picks.extend(picks)

                except Exception as e:
                    print(f"  ERROR fetching picks for draft {draft_id}: {e}")

        else:
            print(f"  No drafts found for {league_name}")

    except Exception as e:
        print(f"  ERROR fetching drafts for {league_name}: {e}")

# Save results
if all_draft_picks:
    picks_df = pd.DataFrame(all_draft_picks)
    os.makedirs("data", exist_ok=True)
    picks_df.to_csv("data/DraftPicks_AllYears.csv", index=False)
    print(f"Saved {len(picks_df)} draft pick rows to data/DraftPicks_AllYears.csv")
else:
    print("No draft picks collected.")
