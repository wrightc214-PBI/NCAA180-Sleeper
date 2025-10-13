import requests
import sys

url = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard'
resp = requests.get(url, timeout=10)
resp.raise_for_status()
data = resp.json()

games_active = False
for event in data.get('events', []):
    status = event.get('status', {}).get('type', {}).get('state', '')
    if status.lower() == "in":
        games_active = True
        break

if games_active:
    print("🏈 Games are active")
    sys.exit(0)  # 0 = success, trigger refresh
else:
    print("✅ No live games")
    sys.exit(1)  # 1 = no refresh needed
