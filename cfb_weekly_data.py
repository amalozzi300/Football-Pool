import argparse
import csv
import logging
import time
from datetime import datetime, timezone, timedelta
from dateutil import parser as dateparser
import requests
import pandas as pd
from urllib.parse import urlencode
from tqdm import tqdm
import pytz

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Constants
ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# CSV headers
CSV_HEADERS = [
    "Date", "Time (ET)", 'ESPN ID', "Home Team", "Away Team", "Neutral Site",
    "Weather", "ESPN Win Prob Home", "ESPN Win Prob Away", "Moneyline Home", 
    "Moneyline Away", "Spread", 'Home Spread Odds', 'Away Spread Odds', 
    "Over/Under", 'Over Odds', 'Under Odds', "Stadium",
]

def request_with_retry(url, params=None, headers=None, max_retries=3, backoff=1.0):
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp
        except Exception as e:
            logging.warning("Request failed (%s). Attempt %d/%d. Error: %s", url, attempt+1, max_retries, e)
            time.sleep(backoff * (2 ** attempt))
    
    raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts")


def fetch_scoreboard(year: int, week: int, season_type: int = 2):
    """
    Fetch ESPN scoreboard JSON for given year/week/season_type.
    season_type: 2 => regular season (ESPN)
    """
    params = {
        "groups": "80", 
        "year": year, 
        "week": week, 
        "seasontype": season_type
    }
    
    logging.info("Fetching scoreboard for year=%s week=%s season_type=%s", year, week, season_type)
    
    r = request_with_retry(ESPN_SCOREBOARD_URL, params=params)
    return r.json()


def fetch_event_summary(event_id: str):
    """
    Fetch event summary JSON (Gamecast/summary) which often contains matchup predictor
    and detailed info.
    """
    params = {"event": event_id}
    r = request_with_retry(ESPN_SUMMARY_URL, params=params)
    return r.json()


def extract_espn_probabilities(summary_json, competition_index=0):
    """
    Try to extract ESPN Gamecast / FPI matchup predictors from summary JSON.
    Returns (home_pct, away_pct) as floats or (None, None).
    ESPN structures vary between events; we try multiple known paths.
    """
    home_pct = None
    away_pct = None

    try:
        comps = summary_json.get("game", {}) or summary_json.get("header", {})  # fallback
    except Exception:
        comps = None

    # Try a few known locations where probabilities appear
    # 1) summary_json["game"]["probability"] or summary_json["probability"]
    # 2) summary_json["boxscore"]["teams"]... (less likely)
    # 3) summary_json["competitions"][0]["probabilities"] etc.

    # First attempt:
    try:
        # many ESPN event summaries include a "probability" block at top-level
        prob = summary_json.get("probability") or summary_json.get("game", {}).get("probability")
        if prob:
            # Some shapes: {"homeWinPercentage": 65.2, "awayWinPercentage": 34.8}
            # or {"home": {"winningPercentage": 65.2}, "away": {"winningPercentage": 34.8}}
            if "homeWinPercentage" in prob:
                home_pct = prob.get("homeWinPercentage")
                away_pct = prob.get("awayWinPercentage")
            elif "home" in prob and isinstance(prob["home"], dict) and "winningPercentage" in prob["home"]:
                home_pct = prob["home"]["winningPercentage"]
                away_pct = prob.get("away", {}).get("winningPercentage")
    except Exception:
        pass

    # Second attempt: check competitions -> probabilities or odds
    try:
        comps = summary_json.get("competitions") or []
        if comps and len(comps) > competition_index:
            comp = comps[competition_index]
            # some payloads include "probability" under competition
            p2 = comp.get("probability") or comp.get("probabilities")
            if p2:
                if isinstance(p2, dict) and "home" in p2 and "away" in p2:
                    # e.g. {"home":{"winPct":...}, ...}
                    if "winPct" in p2["home"]:
                        home_pct = p2["home"]["winPct"]
                        away_pct = p2["away"]["winPct"]
                    elif "winningPercentage" in p2["home"]:
                        home_pct = p2["home"]["winningPercentage"]
                        away_pct = p2["away"]["winningPercentage"]
            # another path: comp['probability']['home']...
            if not home_pct:
                p3 = comp.get("probability")
                if p3 and "home" in p3 and isinstance(p3["home"], dict):
                    home_pct = p3["home"].get("winPct") or p3["home"].get("winningPercentage")
                    away_pct = p3["away"].get("winPct") or p3["away"].get("winningPercentage")
    except Exception:
        pass

    # Final: try to find any numeric percentages in the JSON text (last resort)
    if home_pct is None or away_pct is None:
        # recurse small search
        import re, json
        s = json.dumps(summary_json)
        # look for patterns like "homeWinPercentage":65.2
        m = re.search(r'"homeWinPercentage"\s*:\s*([\d\.]+)', s)
        if m:
            try:
                home_pct = float(m.group(1))
            except:
                pass
        m2 = re.search(r'"awayWinPercentage"\s*:\s*([\d\.]+)', s)
        if m2:
            try:
                away_pct = float(m2.group(1))
            except:
                pass

    # Normalize to strings for CSV if present
    if home_pct is not None:
        home_pct = round(float(home_pct), 1)
    if away_pct is not None:
        away_pct = round(float(away_pct), 1)

    return home_pct, away_pct


def build_match_rows_from_scoreboard(scoreboard_json, year, week, season_type):
    """
    Parse scoreboard JSON and yield match dicts for each event that is a college-football event.
    We'll include anything in the JSON feed (ESPN returns only college-football here).
    """
    events = scoreboard_json.get("events", [])
    rows = []
    for ev in events:
        try:
            # competitions[0] usually holds the matchup and site info
            comps = ev.get("competitions", [])
            if not comps:
                continue
            comp = comps[0]
            # teams
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue

            event_id = ev.get('id')

            # Find home and away (ESPN marks 'home'/'away' in competitor['homeAway'])
            home = next((c for c in competitors if c.get("homeAway") == "home"), None)
            away = next((c for c in competitors if c.get("homeAway") == "away"), None)

            if not (home and away):
                logging.info(f"Home/Away not found for game ID: {comp.get('id')}")

            home_team = home.get("team", {}).get("shortDisplayName") or home.get("team", {}).get("displayName") or 'Not Found'
            away_team = away.get("team", {}).get("shortDisplayName") or home.get("team", {}).get("displayName") or 'Not Found'
            home_rank = home.get("curatedRank", {}).get('current')
            home_rank = home_rank if home_rank is not None and home_rank <= 25 else ''
            away_rank = away.get("curatedRank", {}).get('current')
            away_rank = away_rank if away_rank is not None and away_rank <=25 else ''

            # date/time; event['date'] is in ISO with tz; convert to ET for CSV
            event_date = ev.get("date") or comp.get("date")
            if event_date:
                dt = dateparser.parse(event_date)
                # ESPN times often in local timezone or Z; normalize to ET for CSV display
                eastern = pytz.timezone("US/Eastern")
                dt_et = dt.astimezone(eastern)
                date_str = dt_et.strftime("%Y-%m-%d")
                time_str = dt_et.strftime("%H:%M")
            else:
                date_str = ""
                time_str = ""

            # stadium & neutral site
            venue = comp.get("venue", {}) or {}
            stadium = venue.get("fullName") or venue.get("name", '')
            city = venue.get("address", {}).get("city", '')
            state = venue.get("address", {}).get("state", '')
            indoor = venue.get('indoor', '')
            neutral_site_flag = comp.get("neutralSite", False)

            # weather
            weather = ev.get('weather') if not indoor else 'N/A -- Indoor'

            rows.append({
                'ESPN ID': event_id,
                "Date": date_str,
                "Time (ET)": time_str,
                "Home Team": f'[{home_rank}] {home_team}' if home_rank else home_team,
                "Away Team": f'[{away_rank}] {away_team}' if away_rank else away_team,
                "Neutral Site": "Yes" if neutral_site_flag else "No",
                "Weather at Kickoff (Short)": weather,
                "ESPN Win Prob Home": "",
                "ESPN Win Prob Away": "",
                "Moneyline Home": "",
                "Moneyline Away": "",
                "Spread (with odds)": "",
                "Over/Under (with odds)": "",
                "Stadium": stadium,
                "Indoor": indoor,
                "City": city,
                "State": state,
            })
        except Exception as e:
            logging.exception("Failed to parse event: %s", e)
    return rows


def populate_details(rows, year, week, season_type, pause_between=0.5):
    """
    For each row attempt to:
     - fetch ESPN event summary (via event id parsed from notes),
     - extract matchup probabilities,
     - geocode city/state to lat/lon and fetch weather for kickoff hour.
    """
    updated = []
    for row in tqdm(rows, desc="Processing games"):
        try:
            notes = row.get("Notes", "")
            event_id = None
            import re
            m = re.search(r"event id=(\d+)", notes)
            if m:
                event_id = m.group(1)
            else:
                # try to search scoreboard again to find event id by team names (fallback)
                logging.debug("No event id in notes for row, skipping summary fetch.")

            # fetch summary JSON if we have event id
            if event_id:
                try:
                    summary = fetch_event_summary(event_id)
                    # extract probabilities
                    home_pct, away_pct = extract_espn_probabilities(summary)
                    row["ESPN Win Prob Home"] = f"{home_pct}%" if home_pct is not None else ""
                    row["ESPN Win Prob Away"] = f"{away_pct}%" if away_pct is not None else ""
                    # If stadium not set, try to get from summary
                    try:
                        comps = summary.get("competitions", [])
                        if comps and comps[0].get("venue"):
                            venue = comps[0]["venue"]
                            row["Stadium"] = venue.get("fullName") or row["Stadium"]
                            row["City"] = venue.get("address", {}).get("city") or row["City"]
                            row["State"] = venue.get("address", {}).get("state") or row["State"]
                    except Exception:
                        pass
                except Exception as e:
                    logging.warning("Could not fetch summary for event %s: %s", event_id, e)
            # Geocode using City/State (if available)
            lat = lon = None
            if row.get("City"):
                lat, lon = geocode_place(row["City"], row.get("State", None))
            # If geocode successful and we have kickoff time, compute kickoff UTC to request weather
            if lat and lon and row.get("Date") and row.get("Time (ET)"):
                # combine Date + Time (ET) into aware datetime in ET, then convert to UTC for Open-Meteo
                et = pytz.timezone("US/Eastern")
                local_dt_naive = dateparser.parse(f"{row['Date']} {row['Time (ET)']}")
                if local_dt_naive.tzinfo is None:
                    local_dt = et.localize(local_dt_naive)
                else:
                    local_dt = local_dt_naive.astimezone(et)
                kickoff_utc = local_dt.astimezone(pytz.UTC)
                w_short, w_flag = fetch_weather_open_meteo(lat, lon, kickoff_utc)
                row["Weather at Kickoff (Short)"] = w_short
                row["Weather at Kickoff (Rain/NoRain)"] = w_flag
            else:
                # fallback: leave empty or set unknown
                if not row["Weather at Kickoff (Short)"]:
                    row["Weather at Kickoff (Short)"] = ""
                if not row["Weather at Kickoff (Rain/NoRain)"]:
                    row["Weather at Kickoff (Rain/NoRain)"] = ""
            time.sleep(pause_between)
        except Exception as e:
            logging.exception("Failed to populate details for row: %s", e)
        updated.append(row)
    return updated

def main(argv=None):
    year = 2025
    week = int(input('Week: '))
    season_type = int(input('Season Type (2 for regular season): '))
    out = f'cfb_{year}_{season_type}_week{week}.csv'
    pause = 0.5

    # Step 1: fetch scoreboard
    sb = fetch_scoreboard(year, week, season_type)
    rows = build_match_rows_from_scoreboard(sb, year, week, season_type)
    logging.info("Found %d events on scoreboard", len(rows))

    # Step 2: populate details (ESPN probabilities, stadium, weather)
    rows = populate_details(rows, year, week, season_type, pause_between=pause)

    # Step 3: Write CSV with exact headers
    df = pd.DataFrame(rows)
    # ensure all headers present; if any missing add empty
    for h in CSV_HEADERS:
        if h not in df.columns:
            df[h] = ""
    out_df = df[CSV_HEADERS]  # enforce order
    out_df.to_csv(out, index=False)
    logging.info("Wrote output CSV to %s (rows=%d)", out, len(out_df))


if __name__ == "__main__":
    main()
