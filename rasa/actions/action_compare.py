import logging
import re
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import (
    compare_players, get_team_stats,
    _fuzzy_find_player, _PLAYER_SYNONYMS, _normalize_name, _ensure_loaded
)
from actions.llm_answer import compose_answer

logger = logging.getLogger(__name__)

_TEAM_SYNONYMS = {
    "gsw": "Golden State Warriors", "warriors": "Golden State Warriors",
    "lakers": "Los Angeles Lakers", "celtics": "Boston Celtics",
    "heat": "Miami Heat", "bulls": "Chicago Bulls",
    "knicks": "New York Knicks", "sixers": "Philadelphia 76ers",
    "76ers": "Philadelphia 76ers", "nets": "Brooklyn Nets",
    "raptors": "Toronto Raptors", "mavs": "Dallas Mavericks",
    "mavericks": "Dallas Mavericks", "nuggets": "Denver Nuggets",
    "bucks": "Milwaukee Bucks", "suns": "Phoenix Suns",
    "blazers": "Portland Trail Blazers", "spurs": "San Antonio Spurs",
    "hawks": "Atlanta Hawks", "hornets": "Charlotte Hornets",
    "pistons": "Detroit Pistons", "rockets": "Houston Rockets",
    "pacers": "Indiana Pacers", "grizzlies": "Memphis Grizzlies",
    "wolves": "Minnesota Timberwolves", "thunder": "Oklahoma City Thunder",
    "magic": "Orlando Magic", "kings": "Sacramento Kings",
    "jazz": "Utah Jazz", "wizards": "Washington Wizards",
    "cavs": "Cleveland Cavaliers", "cavaliers": "Cleveland Cavaliers",
    "clips": "Los Angeles Clippers", "clippers": "Los Angeles Clippers",
    "pelicans": "New Orleans Pelicans", "okc": "Oklahoma City Thunder",
    "mia": "Miami Heat", "chi": "Chicago Bulls", "nyk": "New York Knicks",
    "bos": "Boston Celtics", "lal": "Los Angeles Lakers",
    "gsw": "Golden State Warriors",
}


class ActionCompare(Action):
    def name(self) -> Text:
        return "action_compare"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        try:
            latest_msg = tracker.latest_message.get("text", "")
            extracted = self._extract_names_from_text(latest_msg)
            season = self._extract_season_from_text(latest_msg)
            logger.info(f"Extracted: {extracted}, season={season}")

            name1 = extracted[0] if extracted and len(extracted) > 0 else None
            name2 = extracted[1] if extracted and len(extracted) > 1 else None

            if not name1:
                name1 = tracker.get_slot("player")
            if not name2:
                name2 = tracker.get_slot("player2")

            if not name1 or not name2:
                dispatcher.utter_message(text="Please specify two players or teams to compare. For example: 'compare LeBron James and Michael Jordan'")
                return []

            _ensure_loaded()

            # Try player comparison first
            result = compare_players(name1, name2)
            if result is not None:
                p1 = result["player1"]
                p2 = result["player2"]
                response = f"{p1['player']} ({p1['season']}) vs {p2['player']} ({p2['season']}):\n"
                response += f"- Points Per Game (PPG): {p1['points']} vs {p2['points']}\n"
                response += f"- Rebounds Per Game (RPG): {p1['rebounds']} vs {p2['rebounds']}\n"
                response += f"- Assists Per Game (APG): {p1['assists']} vs {p2['assists']}\n"
                response += f"- Steals Per Game (SPG): {p1['steals']} vs {p2['steals']}\n"
                response += f"- Blocks Per Game (BPG): {p1['blocks']} vs {p2['blocks']}\n"
                if p1["fg_pct"] is not None and p2["fg_pct"] is not None:
                    response += f"- Field Goal Percentage (FG%): {p1['fg_pct']}% vs {p2['fg_pct']}%\n"
                if p1["three_pct"] is not None and p2["three_pct"] is not None:
                    response += f"- Three-Point Percentage (3P%): {p1['three_pct']}% vs {p2['three_pct']}%\n"
                response = compose_answer(tracker.latest_message.get("text", ""), response, response)
                dispatcher.utter_message(text=response)
                return []

            # Try team comparison
            resolved1 = self._resolve_team(name1)
            resolved2 = self._resolve_team(name2)
            if resolved1 and resolved2:
                if not season:
                    season = "2024"
                t1 = get_team_stats(resolved1, season)
                t2 = get_team_stats(resolved2, season)
                if t1 and t2:
                    response = f"{t1['team']} ({t1['season']}) vs {t2['team']} ({t2['season']}):\n"
                    response += f"- Points Per Game (PPG): {t1['points']} vs {t2['points']}\n"
                    response += f"- Rebounds Per Game (RPG): {t1['rebounds']} vs {t2['rebounds']}\n"
                    response += f"- Assists Per Game (APG): {t1['assists']} vs {t2['assists']}\n"
                    if t1.get("fg_pct") is not None and t2.get("fg_pct") is not None:
                        response += f"- Field Goal Percentage (FG%): {t1['fg_pct']}% vs {t2['fg_pct']}%\n"
                    if t1.get("three_pct") is not None and t2.get("three_pct") is not None:
                        response += f"- Three-Point Percentage (3P%): {t1['three_pct']}% vs {t2['three_pct']}%\n"
                    response = compose_answer(tracker.latest_message.get("text", ""), response, response)
                    dispatcher.utter_message(text=response)
                    return []

            dispatcher.utter_message(text=f"I couldn't find stats for {name1} or {name2}. Please check the names and try again.")
            return []
        except Exception as e:
            logger.error(f"Error in action_compare: {e}", exc_info=True)
            dispatcher.utter_message(text="Sorry, I am having trouble comparing those. Please try again.")
            return []

    @staticmethod
    def _resolve_team(name: str):
        n = name.lower().strip()
        if n in _TEAM_SYNONYMS:
            return _TEAM_SYNONYMS[n]
        _ensure_loaded()
        from actions.data_loader import team_stats_df, _fuzzy_find_player
        found = _fuzzy_find_player(n, team_stats_df, col="team")
        return found

    @staticmethod
    def _extract_names_from_text(text: str) -> list:
        cleaned = text.lower().strip()
        parts = None
        for sep in [" and ", " or ", " vs ", " versus ", " with "]:
            if sep in cleaned:
                parts = [p.strip() for p in cleaned.split(sep) if p.strip()]
                break
        if not parts or len(parts) < 2:
            parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        if not parts or len(parts) < 2:
            return None

        _ensure_loaded()
        from actions.data_loader import player_per_game_df, team_stats_df
        validated = []
        for part in parts:
            for phrase in ["compare", "who scored more", "who has more", "who had more",
                           "who is better", "who was better", "which team", "which player",
                           "how do", "how did", "stats", "better", "worse",
                           "best seasons", "best season",
                           "scoring", "points", "rebounds", "assists",
                           "steals", "blocks", "numbers"]:
                part = part.replace(phrase, " ")
            part = re.sub(r'\b(the|a|an|was|is|did|does|do|in|of|for)\b', ' ', part)
            part = re.sub(r'\b\d{4}\b', '', part)
            part = re.sub(r'[^\w\s]', ' ', part)
            part = re.sub(r'\s+', ' ', part).strip()
            if not part:
                continue
            # Try player first
            found = _fuzzy_find_player(part, player_per_game_df)
            if found:
                validated.append(found)
                continue
            # Try team
            found = _fuzzy_find_player(part, team_stats_df, col="team")
            if found:
                validated.append(found)
        return validated if len(validated) >= 2 else None

    @staticmethod
    def _extract_season_from_text(text: str) -> str:
        matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        if matches:
            return matches[-1]
        return None
