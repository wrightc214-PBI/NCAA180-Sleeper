import pandas as pd
from sleeper_wrapper import League

# Load league IDs
league_ids_df = pd.read_csv("data/League_IDs.csv")

all_drafts = []

for _, row in league_ids_df.iterrows():
    league_id = row["LeagueID"]
    league_name = row["LeagueName"]
    year = row["Year"]

    print(f"Processing drafts for {league_name} ({year})")

    try:
        league = League(str(league_id))

        # Fetch draft(s) for this league
        drafts = league.get_all_drafts()
        if not drafts:
            print(f"  No drafts found for {league_name} ({year})")
            continue

        for draft in drafts:
            draft_id = draft.get("draft_id")
            draft_year = draft.get("season")
            draft_type = draft.get("type")
            status = draft.get("status")

            # Fetch draft picks
            picks = league.get_draft(draft_id)
            if not picks:
                print(f"  No picks found for draft {draft_id}")
                continue

            for pick in picks:
                all_drafts.append({
                    "LeagueID": league_id,
                    "LeagueName": league_name,
                    "Year": year,
                    "DraftID": draft_id,
                    "DraftYear": draft_year,
                    "DraftType": draft_type,
                    "DraftStatus": status,
                    "PickNo": pick.get("pick_no"),
                    "Round": pick.get("round"),
                    "RosterID": pick.get("roster_id"),
                    "PlayerID": pick.get("player_id"),
                    "PickedBy": pick.get("picked_by"),
                    "IsKeeper": pick.get("is_keeper")
                })

    except Exception as e:
        print(f"  ERROR fetching draft data for {league_name} ({year}): {e}")
        continue

# Convert to DataFrame
all_drafts_df = pd.DataFrame(all_drafts)

# Save to CSV
output_file = "data/League_Drafts.csv"
if not all_drafts_df.empty:
    all_drafts_df.to_csv(output_file, index=False)
    print(f"✅ Saved {len(all_drafts_df)} draft picks to {output_file}")
else:
    print("⚠️ No draft data found across all leagues.")

