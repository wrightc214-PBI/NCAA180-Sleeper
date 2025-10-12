import pandas as pd

print("🔍 Cleaning data/Scores.csv...")

# Load data safely
df = pd.read_csv("data/Scores.csv", dtype=str)

# Standardize and clean key columns
for col in ["league_id", "roster_id", "weekNum", "array_index"]:
    df[col] = df[col].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)

# Convert numeric keys to consistent int-like strings
df["weekNum"] = df["weekNum"].astype(float).astype(int).astype(str)
df["array_index"] = df["array_index"].astype(float).astype(int).astype(str)

# Drop duplicates on normalized key set
before = len(df)
df.drop_duplicates(
    subset=["league_id", "roster_id", "weekNum", "array_index"],
    keep="last",
    inplace=True
)
after = len(df)

# Save cleaned version
df.to_csv("data/Scores.csv", index=False)
print(f"✅ Duplicates removed and file cleaned. V2")
print(f"🧾 Rows before: {before:,} → after: {after:,} ({before - after:,} duplicates removed)")
