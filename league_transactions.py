import pandas as pd
from sleeper_wrapper import League
import time

YEAR = 2025

league_df = pd.read_csv("data/LeagueIDs_AllYears.csv")
league_df = league_df[league_df['Year'] == YEAR]

all_transactions = []

OBSERVER_IDS = [731808894699028480]

for idx, row in league_df.iterrows():
    league_id = row['LeagueID']
    league_name = row['LeagueName']

    print(f"Processing transactions for {league_name} ({YEAR})")

    league_api = League(league_id)

    # Loop through each week (1-18)
    for week in range(1, 19):
        try:
            weekly_tx = league_api.get_transactions(week)
        except Exception as e:
            print(f"  ERROR fetching transactions for {league_id} week {week}: {e}")
            continue

        if not weekly_tx:
            continue

        for tx in weekly_tx:
            roster_ids = tx.get('roster_ids', [])
            owner_ids = []
            for r_id in roster_ids:
                # Map to owner
                owner_id = None
                try:
                    owner_id = next((r['owner_id'] for r in league_api.get_rosters() if r['roster_id'] == r_id), None)
                except:
                    pass
                if owner_id is None or owner_id in OBSERVER_IDS:
                    owner_id = 0
                owner_ids.append(owner_id)

            all_transactions.append({
                "Year": YEAR,
                "LeagueID": league_id,
                "LeagueName": league_name,
                "Week": week,
                "TransactionID": tx.get('transaction_id'),
                "Type": tx.get('type'),
                "RosterIDs": roster_ids,
                "OwnerIDs": owner_ids,
                "Picks": tx.get('draft_picks', []),
                "Adds": tx.get('adds', {}),
                "Drops": tx.get('drops', {}),
                "Status": tx.get('status'),
                "Created": tx.get('created')
            })

        # Polite pause
        time.sleep(0.5)

# Save CSV
out_file = "data/Transactions_AllYears.csv"
pd.DataFrame(all_transactions).to_csv(out_file, index=False)
print(f"Saved {len(all_transactions)} transactions to {out_file}")
