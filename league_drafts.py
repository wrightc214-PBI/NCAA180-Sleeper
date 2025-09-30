import pandas as pd
from sleeper_wrapper import League, Drafts
import time

league_ids_file = "data/LeagueIDs_AllYears.csv"
output_file = "data/Drafts_AllYears.csv"

league_ids_df = pd.read_csv(league_ids_file)

all_drafts = []
drafts_api = Drafts()

for _, row in league_ids_df.iterrows():
    league_id = str(row["LeagueID"])
    league_name = row["LeagueName"]
    year = row["Year"]

    print(f"Processing drafts for {league_name} ({year})")

    try:
        # Get all drafts for this league (usually 1 per season)
        drafts = drafts_api.get_league_drafts(league_id)
        if not drafts:
            print(f"  No draft found for {league_name} ({year})")
            continue

        for draft in drafts:
            draft_id = draft["draft_id"]

            # Get picks for this draft
            picks = drafts_api.get_draft_picks(draft_id)

            if not picks:
                print(f"  No picks found for draft {draft_id}")
                continue

            for pick in picks:
                all_drafts.append({
                    "LeagueID": league_id,
                    "LeagueName": league_name,
                    "Year": year,
                    "DraftID": draft_id,
                    "Round": pick.get("round"),
                    "Pick": pick.get("pick_no"),
                    "Overall": pick.get("overall"),
                    "RosterID": pick.get("roster_id"),
                    "PlayerID": pick.get("player_id"),
                    "PickedBy": pick.get("picked_by"),
                    "Metadata": pick.get("metadata", {})
                })

            # be polite to the API
            time.sleep(0.2)

    except Exception as e:
        print(f"  ERROR fetching draft data for {league_name} ({year}): {e}")
        continue

# Save results
if all_drafts:
    df = pd.DataFrame(all_drafts)
    df.to_csv(output_file, index=False)
    print(f"✅ Saved {len(df)} draft picks to {output_file}")
else:
    print("⚠️ No draft data found across all leagues.")
