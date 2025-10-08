from datetime import datetime, timezone
import csv

utc_now = datetime.now(timezone.utc)
timestamp_str = utc_now.strftime("%Y-%m-%d %H:%M:%S %Z")

with open("data/update_tracker.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Filename", "TimestampUTC"])
    writer.writerow(["Results_RegularSeason.csv", timestamp_str])

print("UTC timestamp recorded:", timestamp_str)
