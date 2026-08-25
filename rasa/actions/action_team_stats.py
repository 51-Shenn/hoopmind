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
            # Always extract from current message first
            latest_msg = tracker.latest_message.get("text", "")
            team_name = self._extract_team_from_text(latest_msg)
            season = self._extract_season_from_text(latest_msg)
            logger.info(f"Extracted from text: team={team_name}, season={season}")

            # Fallback to slots only if extraction failed
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

            # Resolve team synonym
            resolved = team_name.lower().strip()
            if resolved in _TEAM_SYNONYMS:
                team_name = _TEAM_SYNONYMS[resolved]
                logger.info(f"Resolved team synonym to: {team_name}")

            stats = get_team_stats(team_name, season)
            if stats is None:
                dispatcher.utter_message(text=f"I couldn't find stats for {team_name} in {season}. Please check and try again.")
                return []

            response = f"{stats['team']} {stats['season']} stats ({stats['games']} games):\n"
            response += f"- Points Per Game (PPG): {stats['points']}\n"
            response += f"- Rebounds Per Game (RPG): {stats['rebounds']}\n"
            response += f"- Assists Per Game (APG): {stats['assists']}\n"
            if stats["fg_pct"] is not None:
                response += f"- Field Goal Percentage (FG%): {stats['fg_pct']}%\n"
            if stats["three_pct"] is not None:
                response += f"- Three-Point Percentage (3P%): {stats['three_pct']}%\n"

            dispatcher.utter_message(text=response)
            return []
        except Exception as e:
            logger.error(f"Error in action_team_stats: {e}", exc_info=True)
            dispatcher.utter_message(text="Sorry, I am having trouble looking up those stats. Please try again.")
            return []

    @staticmethod
    def _extract_team_from_text(text: str) -> str:
        """Try to extract a team name from the raw message text."""
        cleaned = text.lower().strip()
        # Strip question prefixes
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
        # Remove stat-related words (longer first!)
        for word in ["stats", "statistics", "numbers", "shooting", "scoring",
                     "points per game", "points", "per game", "allowed",
                     "offensive", "defensive", "rating", "in"]:
            cleaned = cleaned.replace(word, "")
        # Remove 4-digit years
        cleaned = re.sub(r'\b\d{4}\b', '', cleaned)
        cleaned = re.sub(r'[^\w\s]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if cleaned:
            if cleaned in _TEAM_SYNONYMS:
                return _TEAM_SYNONYMS[cleaned]
        return cleaned if cleaned else None

    @staticmethod
    def _extract_season_from_text(text: str) -> str:
        """Try to extract a season year from the raw message text."""
        matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        if matches:
            return matches[-1]
        return None
