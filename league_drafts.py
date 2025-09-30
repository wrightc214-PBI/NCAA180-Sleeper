import pandas as pd
from sleeper_wrapper import League, Drafts

# Load your leagues data
league_ids_df = pd.read_csv("data/LeagueIDs_AllYears.csv")

all_draft_rows = []

# Loop through each league and year
for _, row in league_ids_df.iterrows():
    league_name = row['League']
    league_id = row['League_ID']
    year = row['Year']

    print(f"Processing drafts for {league_name} ({year})")

    try:
        league = League(league_id)             # Initialize League
        draft_ids = league.draft_ids           # Get all draft IDs in that league

        if not draft_ids:
            print(f"  ⚠️ No draft IDs found for {league_name} ({year})")
            continue

        for draft_id in draft_ids:
            draft = Drafts(draft_id)          # Initialize Drafts with a draft ID
            picks = draft.picks                # Get the picks list

            for pick in picks:
                pick_row = {
                    "League": league_name,
                    "Year": year,
                    "Draft_ID": draft_id,
                    "Pick": pick.get("pick_no"),
                    "Roster_ID": pick.get("roster_id"),
                    "Player_ID": pick.get("player_id"),
                    "Position": pick.get("metadata", {}).get("position"),
                    "Team": pick.get("metadata", {}).get("team")
                }
                all_draft_rows.append(pick_row)

    except Exception as e:
        print(f"  ERROR fetching drafts for {league_name} ({year}): {e}")

# Save all draft picks to CSV
drafts_df = pd.DataFrame(all_draft_rows)
drafts_df.to_csv("data/Drafts_AllYears.csv", index=False)
print(f"Saved {len(all_draft_rows)} draft rows to data/Drafts_AllYears.csv")
