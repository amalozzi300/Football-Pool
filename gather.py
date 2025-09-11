import requests

ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/summary"

LEAGUE_DATA = {
    'mlb': {
        'sport': 'baseball',
        'league': 'mlb',
        'params': {},
    },
    'nba': {
        'sport': 'basketball',
        'league': 'nba',
        'params': {},
    },
    'ncaaf': {
        'sport': 'football',
        'league': 'college-football',
        'params': {},
    },
    'nfl':{
        'sport': 'football',
        'league': 'nfl',
        'params': {},
    },
}