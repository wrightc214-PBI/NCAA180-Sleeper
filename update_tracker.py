from datetime import datetime
from zoneinfo import ZoneInfo
import csv
import os

# Folder containing CSVs
data_folder = "data"

# Output CSV that lists filenames and last modified time
out_file = os.path.join(data_folder, "LastUpdate.csv")

# Collect all CSV files
csv_files = [f for f in os.listdir(data_folder) if f.lower().endswith(".csv")]

# Prepare rows for output
rows = []
for csv_file in csv_files:
    full_path = os.path.join(data_folder, csv_file)
    last_mod_time = datetime.fromtimestamp(os.path.getmtime(full_path), ZoneInfo("America/New_York"))
    last_mod_str = last_mod_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    rows.append([csv_file, last_mod_str])

# Write CSV
with open(out_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Filename", "LastModifiedET"])
    writer.writerows(rows)

print(f"Recorded last modified times for {len(csv_files)} files to {out_file}")
