import logging
import requests
import time
import json

ESPN_SCOREBOARD_URL = 'https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard'
ESPN_SUMMARY_URL = 'https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary'

LEAGUE_DATA = {
    'mlb': {
        'sport': 'baseball',
    },
    'nba': {
        'sport': 'basketball',
    },
    'college-football': {
        'sport': 'football',
        'params': {
            'groups': 80,
        },
    },
    'nfl':{
        'sport': 'football',
    },
}


def request_with_retry(url, params=None, headers=None, max_retries=3, backoff=1.0):
    """ 
    Executes the HTTP request and returns the response.
    Built in retries. Raises RunTimeError if unsuccessful after {max_retries} attempts.
    """
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp
        except Exception as e:
            logging.warning(f'Request failed {url}. Attempt {attempt + 1}/{max_retries}. Error: {e}')
            time.sleep(backoff * (2 ** attempt))
    
    raise RuntimeError(f'Failed to fetch {url} after {max_retries} attempts')


def get_espn_scoreboard(sport, league, year=None, week=None, season_type=2):
    """ 
    Returns the HTTP response returned by the ESPN API for the given sport and league's scoreboard as a JSON.
    """
    sport_data = LEAGUE_DATA[league]
    params = sport_data.get('params', {})

    if league == 'college-football':
        params['year'] = year
        params['week'] = week
        params['seasontype'] = season_type
    elif league == 'nfl':
        pass
    elif league == 'nba':
        pass
    elif league == 'mlb':
        pass

    logging.info('Fetching scoreboard for year={year} week={week} season_type={season_type}')
    
    r = request_with_retry(ESPN_SCOREBOARD_URL.format(sport=sport, league=league), params=params)
    return r.json()


def get_espn_event_summary(sport, league, event_id):
    """
    Returns the HTTP response returned by the ESPN API for the given sport and league's event as a JSON.
    """
    r = request_with_retry(ESPN_SUMMARY_URL.format(sport=sport, league=league), params={'event': event_id})
    return r.json()


def main():
    league = input('League: ').lower()

    while league not in LEAGUE_DATA.keys():
        print(f'\n{league} is not a valid league selection.\nOptions:\n\t"college-football"\n\t"nfl"\n\t"mlb"\n\t"nba"\n')
        league = input('League: ').lower()

    output_file = input('Output File (must be ".csv"): ')

    while not output_file.endswith('.csv'):
        print(f'\nThe output file must be a CSV. Please use the ".csv" file extension\n')
        output_file = input('Output File (must be ".csv"): ')

    league_dict = LEAGUE_DATA[league]
    sport = league_dict['sport']
    scoreboards = []

    if sport == 'football':
        for year in range(2017, 2026):
            if year == 2020:
                continue
            elif league == 'college-football':
                if year <= 2018 or (year >= 2021 and year <= 2023):
                    num_weeks = 15
                elif year == 2019 or year == 2024:
                    num_weeks = 16
                elif year == 2025:
                    num_weeks = 2
            elif league == 'nfl':
                if year >= 2017 and year <= 2019:
                    num_weeks = 17
                elif year >= 2021 and year <= 2024:
                    num_weeks == 18
                elif year == 2025:
                    num_weeks = 1

            for i in range(num_weeks):
                week = i + 1
                scoreboards.append(get_espn_scoreboard(sport=sport, league=league, year=year, week=week))
    elif sport == 'baseball' or sport == 'basketball':
        pass

    all_events = []

    for scoreboard in scoreboards:
        events = scoreboard.get('events', [])
        
        for event in events:
            event_id = event.get('id')

            if not event_id:
                continue

            year = event.get('season', {}).get('year')
            week = event.get('week', {}).get('number')
            event_data = {
                'event_id': event_id,
                'year': year,
                'week': week,
            }
            all_events.append(event_data)

    print(len(all_events))

    with open(f'{league}_event_ids.json', 'w') as ids_file:
        json.dump(all_events, ids_file)


if __name__ == '__main__':
    main()