import requests
import sys
import json

url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

try:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
except Exception as e:
    print(f"⚠️ Error fetching game status: {e}")
    sys.exit(2)  # exit code 2 = API error

# Extract week number
week_number = None
try:
    week_number = data.get("week", {}).get("number", None)
except Exception:
    pass

if week_number is None:
    print("⚠️ Could not determine current NFL week.")
    sys.exit(2)

# Detect if any games are active
games_active = False
for event in data.get("events", []):
    state = event.get("status", {}).get("type", {}).get("state", "")
    if state.lower() == "in":  # 'in' means game is live
        games_active = True
        break

# Output summary (for GitHub logs)
print(f"📅 Current NFL Week: {week_number}")
print(f"🏈 Games active: {'YES' if games_active else 'NO'}")

# Save week number to JSON for later steps
with open("nfl_status.json", "w") as f:
    json.dump({"week_number": week_number, "games_active": games_active}, f)

# Exit codes for workflow logic
if games_active:
    sys.exit(0)  # success → run refresh
else:
    sys.exit(1)  # no live games → skip refresh
