"""
ONE-TIME: relabel orphan rosters in data/Matchups_Historic.csv to match the new
league_matchups.py rule. Run once via workflow_dispatch, verify, then DELETE this file.

Orphan = any of:
  - OwnerName like "<League> Orphan #N"   (old linkoftime1 caretaker label)
  - OwnerName starting with "DELETED"      (deleted Sleeper account)
  - OwnerName == "Vacant" / OwnerID == 0   (no owner / observer)
OwnerID and OwnerName both become "Orphan". OpponentName gets the same rule.
"""
import pandas as pd

FILE = "data/Matchups_Historic.csv"

def is_orphan(name):
    n = str(name)
    return (" Orphan #" in n) or n.upper().startswith("DELETED") or n == "Vacant" or n == "Orphan"

df = pd.read_csv(FILE, dtype=str)
before = df["OwnerName"].apply(is_orphan).sum()
own = df["OwnerName"].apply(is_orphan) | (df["OwnerID"] == "0")
df.loc[own, ["OwnerID", "OwnerName"]] = "Orphan"
opp = df["OpponentName"].apply(is_orphan)
df.loc[opp, "OpponentName"] = "Orphan"
df.to_csv(FILE, index=False)
print(f"Owner rows relabeled: {own.sum()} (name matches {before}); opponent rows: {opp.sum()}")
print(df[own].groupby("Year").size().to_string())
