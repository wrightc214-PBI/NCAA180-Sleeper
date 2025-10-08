from datetime import datetime, timezone
import csv
import os

# Path to the folder containing your CSVs
data_folder = "data"

# Output CSV that tracks timestamps
out_file = os.path.join(data_folder, "LastUpdate.csv")

# Get current UTC time
utc_now = datetime.now(timezone.utc)
timestamp_str = utc_now.strftime("%Y-%m-%d %H:%M:%S %Z")

# Collect all CSV files in the folder
csv_files = [f for f in os.listdir(data_folder) if f.lower().endswith(".csv")]

# Write the tracker CSV
with open(out_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Filename", "TimestampUTC"])
    for csv_file in csv_files:
        writer.writerow([csv_file, timestamp_str])

print(f"Recorded timestamps for {len(csv_files)} files to {out_file}")
