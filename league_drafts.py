import pandas as pd
from sleeper_wrapper import Leagues, Drafts

# Load league IDs
league_ids_df = pd.read_csv("data/LeagueIDs_AllYears.csv")

all_drafts = []
all_picks = []

# Loop through each league and pull draft info
for _, row in league_ids_df.iterrows():
    league_id = row["LeagueID"]
    league_name = row["LeagueName"]

    print(f"Fetching draft info for league {league_name} ({league_id})...")

    # Get drafts for this league
    drafts = Leagues(league_id).get_all_drafts()

    if drafts:
        for draft in drafts:
            draft_id = draft.get("draft_id")
            rounds = draft.get("settings", {}).get("rounds", 0)
            slots = draft.get("settings", {}).get("slots", 0)
            num_teams = draft.get("settings", {}).get("teams", 0)

            # Store draft metadata
            all_drafts.append({
                "LeagueID": league_id,
                "LeagueName": league_name,
                "DraftID": draft_id,
                "Status": draft.get("status"),
                "Type": draft.get("type"),
                "Season": draft.get("season"),
                "Rounds": rounds,
                "Teams": num_teams
            })

            # Get picks for this draft
            picks = Drafts().get_draft_picks(draft_id)

            for p in picks:
                meta = p.get("metadata", {})

                round_no = p.get("round")
                pick_no = p.get("pick_no")

                # Overall pick = ((round - 1) * num_teams) + pick_no
                overall_pick = None
                if round_no and pick_no and num_teams:
                    overall_pick = ((round_no - 1) * num_teams) + pick_no

                all_picks.append({
                    "LeagueID": league_id,
                    "LeagueName": league_name,
                    "DraftID": draft_id,
                    "Round": round_no,
                    "Pick_No": pick_no,
                    "OverallPick": overall_pick,
                    "Picked_By": p.get("picked_by"),
                    "RosterID": p.get("roster_id"),
                    "PlayerID": meta.get("player_id"),
                    "FirstName": meta.get("first_name"),
                    "LastName": meta.get("last_name"),
                    "Team": meta.get("team"),
                    "Position": meta.get("position"),
                    "Status": meta.get("status"),
                    "YearsExp": meta.get("years_exp")
                })

# Save drafts and picks to CSV
drafts_df = pd.DataFrame(all_drafts)
picks_df = pd.DataFrame(all_picks)

drafts_df.to_csv("data/Drafts_AllYears.csv", index=False)
picks_df.to_csv("data/DraftPicks_AllYears.csv", index=False)

print("Drafts and picks exported successfully!")
