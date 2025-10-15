import os
import pandas as pd
from datetime import datetime, timezone, timedelta

# -------------------------
# CONFIG
# -------------------------
DATA_DIR = "data"
OUT_FILE = os.path.join(DATA_DIR, "LastUpdate.csv")

# -------------------------
# HELPER: Get Eastern Time (handles DST automatically)
# -------------------------
def get_eastern_time(ts):
    # UTC offset: -5 in standard time, -4 in DST
    # Using built-in tz handling from datetime + isdst heuristic
    utc_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    # Approx conversion to US Eastern manually
    offset = -4 if datetime.now().astimezone().dst() else -5
    return (utc_dt + timedelta(hours=offset)).strftime("%Y-%m-%d %H:%M:%S %Z")

# -------------------------
# MAIN: Collect all file info
# -------------------------
rows = []
for root, _, files in os.walk(DATA_DIR):
    for fname in files:
        fpath = os.path.join(root, fname)
        try:
            ts = os.path.getmtime(fpath)
            mtime = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
            size_kb = round(os.path.getsize(fpath) / 1024, 1)
            rows.append({
                "FileName": fname,
                "LastModified": mtime,
                "Size_KB": size_kb
            })
        except Exception as e:
            print(f"⚠️ Could not read {fpath}: {e}")

# -------------------------
# SAVE TO CSV
# -------------------------
df = pd.DataFrame(rows).sort_values(by="FileName")
df.to_csv(OUT_FILE, index=False)

print(f"✅ Saved {len(df)} file entries to {OUT_FILE}")
