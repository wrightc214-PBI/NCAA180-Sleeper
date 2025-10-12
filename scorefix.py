import pandas as pd

df = pd.read_csv("data/Scores.csv", dtype=str)

df["league_id"] = df["league_id"].astype(str).str.strip()
df["roster_id"] = df["roster_id"].astype(str).str.strip()
df["weekNum"] = df["weekNum"].astype(str).str.strip().astype(int)
df["array_index"] = df["array_index"].astype(str).str.strip().astype(int)

df.drop_duplicates(
    subset=["league_id", "roster_id", "weekNum", "array_index"],
    keep="last",
    inplace=True
)

df.to_csv("data/Scores.csv", index=False)
print("✅ Duplicates removed and file cleaned.")
