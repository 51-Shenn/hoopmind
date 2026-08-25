import logging
import re
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import get_team_stats, _normalize_name, _ensure_loaded

logger = logging.getLogger(__name__)

_TEAM_SYNONYMS = {
    "gsw": "Golden State Warriors",
    "warriors": "Golden State Warriors",
    "dubs": "Golden State Warriors",
    "golden state": "Golden State Warriors",
    "lakers": "Los Angeles Lakers",
    "lal": "Los Angeles Lakers",
    "celtics": "Boston Celtics",
    "bos": "Boston Celtics",
    "heat": "Miami Heat",
    "mia": "Miami Heat",
    "bulls": "Chicago Bulls",
    "chi": "Chicago Bulls",
    "knicks": "New York Knicks",
    "nyk": "New York Knicks",
    "sixers": "Philadelphia 76ers",
    "76ers": "Philadelphia 76ers",
    "philly": "Philadelphia 76ers",
    "cavs": "Cleveland Cavaliers",
    "cavaliers": "Cleveland Cavaliers",
    "clips": "Los Angeles Clippers",
    "clippers": "Los Angeles Clippers",
    "nets": "Brooklyn Nets",
    "raptors": "Toronto Raptors",
    "mavs": "Dallas Mavericks",
    "mavericks": "Dallas Mavericks",
    "nuggets": "Denver Nuggets",
    "bucks": "Milwaukee Bucks",
    "suns": "Phoenix Suns",
    "blazers": "Portland Trail Blazers",
    "spurs": "San Antonio Spurs",
    "hawks": "Atlanta Hawks",
    "hornets": "Charlotte Hornets",
    "pistons": "Detroit Pistons",
    "rockets": "Houston Rockets",
    "pacers": "Indiana Pacers",
    "grizzlies": "Memphis Grizzlies",
    "wolves": "Minnesota Timberwolves",
    "timberwolves": "Minnesota Timberwolves",
    "pelicans": "New Orleans Pelicans",
    "thunder": "Oklahoma City Thunder",
    "okc": "Oklahoma City Thunder",
    "magic": "Orlando Magic",
    "kings": "Sacramento Kings",
    "jazz": "Utah Jazz",
    "wizards": "Washington Wizards",
}


class ActionTeamStats(Action):
    def name(self) -> Text:
        return "action_team_stats"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        try:
            latest_msg = tracker.latest_message.get("text", "")
            team_name = self._extract_team_from_text(latest_msg)
            season = self._extract_season_from_text(latest_msg)
            logger.info(f"Extracted from text: team={team_name}, season={season}")

            if not team_name:
                team_name = tracker.get_slot("team")
            if not season:
                season = tracker.get_slot("season")
            logger.info(f"Final values: team={team_name}, season={season}")

            if not team_name:
                dispatcher.utter_message(text="Which team are you interested in?")
                return []
            if not season:
                dispatcher.utter_message(text="Which season?")
                return []

            resolved = team_name.lower().strip()
            if resolved in _TEAM_SYNONYMS:
                team_name = _TEAM_SYNONYMS[resolved]
                logger.info(f"Resolved team synonym to: {team_name}")

            stats = get_team_stats(team_name, season)
            if stats is None:
                dispatcher.utter_message(text=f"I couldn't find stats for {team_name} in {season}. Please check and try again.")
                return []

            response = self._format_response(stats, latest_msg)
            dispatcher.utter_message(text=response)
            return []
        except Exception as e:
            logger.error(f"Error in action_team_stats: {e}", exc_info=True)
            dispatcher.utter_message(text="Sorry, I am having trouble looking up those stats. Please try again.")
            return []

    @staticmethod
    def _detect_specific_stat(text: str) -> str:
        lower = text.lower()
        stat_map = {
            'points per game': 'points', 'ppg': 'points', 'points': 'points', 'scoring': 'points',
            'rebounds per game': 'rebounds', 'rpg': 'rebounds', 'rebounds': 'rebounds',
            'assists per game': 'assists', 'apg': 'assists', 'assists': 'assists',
            'field goal': 'fg_pct', 'fg%': 'fg_pct', 'fg percentage': 'fg_pct',
            'three point': 'three_pct', '3pt': 'three_pct', '3p%': 'three_pct', '3 point': 'three_pct',
            'three-point percentage': 'three_pct',
            'record': 'record', 'wins': 'record', 'wins and losses': 'record', 'win-loss': 'record',
            'games': 'games', 'games played': 'games',
            'offensive rating': 'offensive_rating', 'off rating': 'offensive_rating',
            'defensive rating': 'defensive_rating', 'def rating': 'defensive_rating',
            'net rating': 'net_rating',
            'pace': 'pace',
            'turnovers': 'turnovers', 'turnover': 'turnovers',
            'steals': 'steals', 'steal': 'steals',
            'blocks': 'blocks', 'block': 'blocks',
            'fouls': 'fouls', 'foul': 'fouls',
        }
        for keyword, stat in stat_map.items():
            if keyword in lower:
                return stat
        return None

    @staticmethod
    def _format_response(stats: dict, message: str = "") -> str:
        team = stats['team']
        season = stats['season']
        games = stats['games']
        specific = ActionTeamStats._detect_specific_stat(message) if message else None

        if specific == 'record':
            wins = stats.get('wins', '?')
            losses = stats.get('losses', '?')
            return f"{team}'s {season} record: {wins}-{losses}."

        if specific == 'points':
            return f"{team}'s {season} Points Per Game: {stats['points']}."

        if specific == 'rebounds':
            return f"{team}'s {season} Rebounds Per Game: {stats['rebounds']}."

        if specific == 'assists':
            return f"{team}'s {season} Assists Per Game: {stats['assists']}."

        if specific == 'fg_pct' and stats.get('fg_pct') is not None:
            return f"{team}'s {season} Field Goal Percentage: {stats['fg_pct']}%."

        if specific == 'three_pct' and stats.get('three_pct') is not None:
            return f"{team}'s {season} Three-Point Percentage: {stats['three_pct']}%."

        if specific == 'offensive_rating' and stats.get('offensive_rating') is not None:
            return f"{team}'s {season} Offensive Rating: {stats['offensive_rating']}."

        if specific == 'defensive_rating' and stats.get('defensive_rating') is not None:
            return f"{team}'s {season} Defensive Rating: {stats['defensive_rating']}."

        if specific == 'net_rating' and stats.get('net_rating') is not None:
            return f"{team}'s {season} Net Rating: {stats['net_rating']}."

        if specific == 'pace' and stats.get('pace') is not None:
            return f"{team}'s {season} Pace: {stats['pace']}."

        # Full stat line (no specific stat requested or unknown stat)
        response = f"{team} {season} stats ({games} games):\n"
        response += f"- Points Per Game (PPG): {stats['points']}\n"
        response += f"- Rebounds Per Game (RPG): {stats['rebounds']}\n"
        response += f"- Assists Per Game (APG): {stats['assists']}\n"
        if stats.get("fg_pct") is not None:
            response += f"- Field Goal Percentage (FG%): {stats['fg_pct']}%\n"
        if stats.get("three_pct") is not None:
            response += f"- Three-Point Percentage (3P%): {stats['three_pct']}%\n"
        return response

    @staticmethod
    def _extract_team_from_text(text: str) -> str:
        cleaned = text.lower().strip()
        for phrase in ["stats for the", "stats for", "statistics for the", "statistics for",
                       "numbers for the", "numbers for", "how did the", "how did",
                       "show me the", "show me", "show the", "show",
                       "what were the", "what were", "what are the", "what are",
                       "tell me about the", "tell me about", "info on the", "info on",
                       "points allowed by the", "points allowed by", "points allowed",
                       "points scored by the", "points scored by", "points scored",
                       "points per game for the", "points per game for",
                       "points per game for", "record for the", "record for",
                       "record of the", "record of", "record in", "record",
                       "the", "team"]:
            cleaned = cleaned.replace(phrase, "")
        for word in ["stats", "statistics", "numbers", "shooting", "scoring",
                     "points per game", "points", "per game", "allowed",
                     "offensive", "defensive", "rating", "in"]:
            cleaned = cleaned.replace(word, "")
        cleaned = re.sub(r'\b\d{4}\b', '', cleaned)
        cleaned = re.sub(r'[^\w\s]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if cleaned:
            if cleaned in _TEAM_SYNONYMS:
                return _TEAM_SYNONYMS[cleaned]
        return cleaned if cleaned else None

    @staticmethod
    def _extract_season_from_text(text: str) -> str:
        matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        if matches:
            return matches[-1]
        return None
