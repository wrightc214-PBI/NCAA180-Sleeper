import os
import pandas as pd
from datetime import datetime, timezone, timedelta

# -------------------------
# CONFIG
# -------------------------
DATA_DIR = "data"
OUT_FILE = os.path.join(DATA_DIR, "LastUpdate.csv")

# -------------------------
# HELPER: Get Eastern Time (handles DST)
# -------------------------
def to_eastern(ts):
    """Return timestamp in US Eastern Time (handles DST)."""
    # Get UTC datetime first
    utc_time = datetime.fromtimestamp(ts, tz=timezone.utc)
    # Determine correct offset (-5 in standard time, -4 in DST)
    offset_hours = -4 if datetime.now().astimezone().dst() else -5
    eastern_time = utc_time + timedelta(hours=offset_hours)
    return eastern_time.strftime("%Y-%m-%d %H:%M:%S")

# -------------------------
# MAIN: Collect file info
# -------------------------
rows = []
for root, _, files in os.walk(DATA_DIR):
    for fname in files:
        fpath = os.path.join(root, fname)
        try:
            ts = os.path.getmtime(fpath)
            rows.append({
                "FileName": fname,
                "LastModified": to_eastern(ts)
            })
        except Exception as e:
            print(f"⚠️ Could not read {fpath}: {e}")

# -------------------------
# SAVE TO CSV
# -------------------------
df = pd.DataFrame(rows).sort_values(by="FileName")
df.to_csv(OUT_FILE, index=False)

print(f"✅ Saved {len(df)} file entries to {OUT_FILE}")
