import logging
import re
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import get_team_stats, _normalize_name, _ensure_loaded
from actions.entity_extract import extract_season, extract_team
from actions.llm_answer import compose_answer

logger = logging.getLogger(__name__)

# Matched in order, most specific first. Word boundaries matter: the old
# substring map read "three-pointers" as "points". "record" is matched last
# because it is also a verb - "how many steals did the Bulls record in 1996"
# is a question about steals, not about the win-loss record.
_SPECIFIC_STATS = [
    (re.compile(r'three[\s-]?point|3[\s-]?pt|\b3p%?\b'), 'three_pct'),
    (re.compile(r'free[\s-]?throw|\bft%'), 'ft_pct'),
    (re.compile(r'field[\s-]?goal|\bfg%'), 'fg_pct'),
    (re.compile(r'offensive rating|\boff rating\b'), 'offensive_rating'),
    (re.compile(r'defensive rating|\bdef rating\b'), 'defensive_rating'),
    (re.compile(r'net rating'), 'net_rating'),
    (re.compile(r'\bpace\b'), 'pace'),
    (re.compile(r'\brebounds?\b|\brpg\b|\bboards\b'), 'rebounds'),
    (re.compile(r'\bassists?\b|\bapg\b'), 'assists'),
    (re.compile(r'\bsteals?\b|\bspg\b'), 'steals'),
    (re.compile(r'\bblocks?\b|\bbpg\b'), 'blocks'),
    (re.compile(r'\bturnovers?\b|\btov\b'), 'turnovers'),
    (re.compile(r'\bfouls?\b'), 'fouls'),
    (re.compile(r'\bpoints?\b|\bppg\b|\bscoring\b|\bscored?\b'), 'points'),
    (re.compile(r'\bgames? played\b'), 'games'),
    (re.compile(r'\brecords?\b|\bwins?\b|\bwin-loss\b|\blosses\b'), 'record'),
]

# stat key -> (label, suffix)
_STAT_LABELS = {
    'points': ('Points Per Game', ''),
    'rebounds': ('Rebounds Per Game', ''),
    'assists': ('Assists Per Game', ''),
    'steals': ('Steals Per Game', ''),
    'blocks': ('Blocks Per Game', ''),
    'turnovers': ('Turnovers Per Game', ''),
    'fouls': ('Fouls Per Game', ''),
    'games': ('Games Played', ''),
    'fg_pct': ('Field Goal Percentage', '%'),
    'three_pct': ('Three-Point Percentage', '%'),
    'ft_pct': ('Free-Throw Percentage', '%'),
    'offensive_rating': ('Offensive Rating', ''),
    'defensive_rating': ('Defensive Rating', ''),
    'net_rating': ('Net Rating', ''),
    'pace': ('Pace', ''),
}

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
            response = compose_answer(tracker.latest_message.get("text", ""), response, response)
            dispatcher.utter_message(text=response)
            return []
        except Exception as e:
            logger.error(f"Error in action_team_stats: {e}", exc_info=True)
            dispatcher.utter_message(text="Sorry, I am having trouble looking up those stats. Please try again.")
            return []

    @staticmethod
    def _detect_specific_stat(text: str) -> str:
        lower = text.lower()
        for pattern, stat in _SPECIFIC_STATS:
            if pattern.search(lower):
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

        if specific in _STAT_LABELS:
            value = stats.get(specific)
            if value is not None and value == value:  # not None, not NaN
                label, suffix = _STAT_LABELS[specific]
                return f"{team}'s {season} {label}: {value}{suffix}."

        # Full stat line (no specific stat requested, or it isn't available)
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
        return extract_team(text)

    @staticmethod
    def _extract_season_from_text(text: str) -> str:
        return extract_season(text)
