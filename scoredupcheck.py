import pandas as pd

df = pd.read_csv("data/Scores.csv", dtype=str)
df = df[df["league_id"] == "1192383038721757184"]

# Sort logically
df = df.sort_values(["league_id", "roster_id", "weekNum", "array_index"])

# Show potentially suspicious differences
print("Unique roster_id count:", df["roster_id"].nunique())
print("Unique weekNum values:", sorted(df["weekNum"].unique().tolist())[:20])
print("Unique array_index values:", sorted(df["array_index"].unique().tolist())[:20])

print("\nSample rows for visual inspection:")
print(df.head(20))
