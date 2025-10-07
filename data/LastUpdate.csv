import os
import pandas as pd
from datetime import datetime

# Folder that holds all your CSVs
DATA_DIR = "data"

# Build a list of CSV files and timestamps
rows = []
for fname in os.listdir(DATA_DIR):
    if fname.endswith(".csv"):
        path = os.path.join(DATA_DIR, fname)
        mod_time = datetime.fromtimestamp(os.path.getmtime(path))
        rows.append({"FileName": fname, "LastUpdatedUTC": mod_time.strftime("%Y-%m-%d %H:%M:%S")})

# Create DataFrame
df = pd.DataFrame(rows).sort_values("FileName")

# Write to a new CSV
out_path = os.path.join(DATA_DIR, "LastUpdate.csv")
df.to_csv(out_path, index=False)

print(f"✅ Created {out_path} with {len(df)} file entries.")
