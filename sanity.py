#!/usr/bin/env python3
"""
count_fbs_regular_games.py

Counts D1 FBS regular-season games (excludes bowls/playoffs) by querying ESPN's
scoreboard API with groups=80 & seasontype=2 (regular season). Includes Army-Navy.

Run:
    python count_fbs_regular_games.py

Notes:
- Uses ESPN public JSON: https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard
- Iterates reasonable week range (0..20) for each season; ESPN returns empty for non-existent weeks.
- Respects a small sleep between requests to avoid rate-limiting.
- If you want to include more years, change START_YEAR / END_YEAR variables.
"""

import requests
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

BASE = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; count-fbs-script/1.0)",
    "Accept": "application/json"
}

START_YEAR = 2017
END_YEAR = 2025
EXCLUDE_YEARS = {2020}  # explicitly exclude 2020
SEASONTYPE = 2  # 2 = regular season
GROUPS = 80      # group 80 returns all FBS games

# conservative week range (Week 0..20 covers all possible regular-season weeks)
WEEK_RANGE = range(0, 18)

def fetch_scoreboard(year, week):
    params = {
        "year": year,
        "week": week,
        "seasontype": SEASONTYPE,
        "groups": GROUPS
    }
    r = requests.get(BASE, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def count_regular_games_for_season(year):
    logging.info("Counting regular-season games for %s", year)
    seen_event_ids = set()
    events_count = 0
    for wk in WEEK_RANGE:
        if year == 2025 and wk > 2:
            continue
        
        try:
            data = fetch_scoreboard(year, wk)
        except Exception as e:
            logging.warning("Failed to fetch year=%s week=%s : %s", year, wk, e)
            # polite back-off
            time.sleep(1.0)
            continue

        events = data.get("events", []) or []
        events_count += len(events)

        # be polite and avoid too many requests in quick succession
        time.sleep(0.6)

    return events_count

def main():
    per_year = {}
    grand_total = 0
    for year in range(START_YEAR, END_YEAR + 1):
        if year in EXCLUDE_YEARS:
            logging.info("Skipping excluded year %s", year)
            continue
        cnt = count_regular_games_for_season(year)
        per_year[year] = cnt
        grand_total += cnt
        logging.info("Year %s: %d regular-season FBS games", year, cnt)

    print("\n=== RESULTS ===")
    for y, c in per_year.items():
        print(f"{y}: {c} games")
    print(f"\nTotal (years {START_YEAR}-{END_YEAR} excluding {sorted(EXCLUDE_YEARS)}): {grand_total} games")

if __name__ == "__main__":
    main()
