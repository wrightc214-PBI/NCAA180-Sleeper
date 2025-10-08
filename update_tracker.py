from datetime import datetime
from zoneinfo import ZoneInfo
import csv
import os

# Folder containing CSVs
data_folder = "data"

# Tracker CSV
out_file = os.path.join(data_folder, "LastUpdate.csv")

# Load previous timestamps if exists
prev_timestamps = {}
if os.path.exists(out_file):
    with open(out_file, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prev_timestamps[row["Filename"]] = row["TimestampET"]

# Collect all CSVs
csv_files = [f for f in os.listdir(data_folder) if f.lower().endswith(".csv")]

# Get current ET time
et_now = datetime.now(ZoneInfo("America/New_York"))
timestamp_str = et_now.strftime("%Y-%m-%d %H:%M:%S %Z")

# Prepare updated timestamp list
updated_rows = []

for csv_file in csv_files:
    full_path = os.path.join(data_folder, csv_file)
    last_mod_time = datetime.fromtimestamp(os.path.getmtime(full_path), ZoneInfo("America/New_York"))
    last_mod_str = last_mod_time.strftime("%Y-%m-%d %H:%M:%S %Z")

    # Update timestamp only if modified after last recorded timestamp
    prev_timestamp = prev_timestamps.get(csv_file)
    if not prev_timestamp or last_mod_time.strftime("%Y-%m-%d %H:%M:%S") > prev_timestamp[:19]:
        row_timestamp = last_mod_str
    else:
        row_timestamp = prev_timestamp

    updated_rows.append([csv_file, row_timestamp])

# Write tracker CSV
with open(out_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Filename", "TimestampET"])
    writer.writerows(updated_rows)

print(f"Processed {len(csv_files)} files. Timestamps updated for changed files only.")
