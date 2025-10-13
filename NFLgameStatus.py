import requests
import sys
import json
from datetime import datetime
import pytz

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

# Use Eastern Time (handles EST/EDT automatically)
eastern = pytz.timezone("America/New_York")
now_et = datetime.now(eastern)
weekday = now_et.strftime("%a")  # e.g., 'Sun', 'Mon', etc.
hour_et = now_et.hour

# ------------------------------------------------------------
# FETCH ESPN API DATA
# ------------------------------------------------------------
try:
    resp = requests.get(URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
except Exception as e:
    print(f"⚠️ Error fetching game status: {e}")
    sys.exit(2)  # exit code 2 = API error

# ------------------------------------------------------------
# EXTRACT WEEK NUMBER
# ------------------------------------------------------------
week_number = None
try:
    week_number = data.get("week", {}).get("number", None)
except Exception:
    pass

if week_number is None:
    print("⚠️ Could not determine current NFL week.")
    sys.exit(2)

# ------------------------------------------------------------
# DETECT ACTIVE GAMES
# ------------------------------------------------------------
games_active = False
for event in data.get("events", []):
    state = event.get("status", {}).get("type", {}).get("state", "")
    if state.lower() == "in":  # 'in' means game is live
        games_active = True
        break

# ------------------------------------------------------------
# DETERMINE REFRESH INTERVAL
# ------------------------------------------------------------
# Default 15-minute refresh for all non-Monday games
refresh_interval = 15

# Monday Night Football: faster 5-minute refresh
if weekday == "Mon" and 20 <= hour_et or (weekday == "Tue" and hour_et < 1):
    refresh_interval = 5

# Just to be extra safe, if there are no games, interval stays at 15
if not games_active:
    refresh_interval = 15

# ------------------------------------------------------------
# LOG SUMMARY
# ------------------------------------------------------------
print(f"📅 Current NFL Week: {week_number}")
print(f"🕒 Local ET time: {now_et.strftime('%Y-%m-%d %I:%M %p')}")
print(f"🏈 Games active: {'YES' if games_active else 'NO'}")
print(f"🔁 Suggested refresh interval: {refresh_interval} min")

# ------------------------------------------------------------
# SAVE STATUS JSON
# ------------------------------------------------------------
with open("nfl_status.json", "w") as f:
    json.dump(
        {
            "week_number": week_number,
            "games_active": games_active,
            "refresh_interval": refresh_interval,
            "timestamp_et": now_et.strftime("%Y-%m-%d %H:%M:%S %Z"),
        },
        f,
        indent=2,
    )

# ------------------------------------------------------------
# EXIT CODES
# ------------------------------------------------------------
if games_active:
    sys.exit(0)  # success → active games
else:
    sys.exit(1)  # no live games → skip workflow
