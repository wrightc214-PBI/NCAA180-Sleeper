import pandas as pd
from sleeper_wrapper import League, Drafts
import time

# Load league IDs
league_df = pd.read_csv("data/LeagueIDs_AllYears.csv")

all_drafts = []

# Define observer/unassigned user IDs
OBSERVER_IDS = [731808894699028480]

# Loop through leagues
for idx, row in league_df.iterrows():
    league_id = row['LeagueID']
    year = row['Year']
    league_name = row['LeagueName']

    print(f"Processing drafts for {league_name} ({year})")

    league_api = League(league_id)

    try:
        drafts_list = league_api.get_drafts()  # fetch all draft metadata for the league
    except Exception as e:
        print(f"  ERROR fetching drafts for {league_name} ({year}): {e}")
        continue

    if not drafts_list:
        print(f"  No drafts found for {league_name} ({year})")
        continue

    for draft_meta in drafts_list:
        draft_id = draft_meta['draft_id']

        try:
            draft_api = Drafts(draft_id)
            picks = draft_api.get_picks()
        except Exception as e:
            print(f"  ERROR fetching picks for draft {draft_id}: {e}")
            continue

        for pick in picks:
            owner_id = pick.get('player_id', 0)
            if owner_id in OBSERVER_IDS or owner_id is None:
                owner_id = 0
                owner_name = "Vacant"
            else:
                owner_name = pick.get('player_name', 'Unknown')

            all_drafts.append({
                "Year": year,
                "LeagueID": league_id,
                "LeagueName": league_name,
                "DraftID": draft_id,
                "PickNumber": pick.get('pick_number', None),
                "Round": pick.get('round', None),
                "RosterID": pick.get('roster_id', None),
                "OwnerID": owner_id,
                "OwnerName": owner_name,
                "PlayerID": pick.get('player_id', None),
                "PlayerName": pick.get('player_name', None),
                "Position": pick.get('position', None)
            })

        # Polite pause to avoid rate limits
        time.sleep(0.5)

# Save CSV
out_file = "data/Drafts_AllYears.csv"
pd.DataFrame(all_drafts).to_csv(out_file, index=False)
print(f"Saved {len(all_drafts)} draft rows to {out_file}")
