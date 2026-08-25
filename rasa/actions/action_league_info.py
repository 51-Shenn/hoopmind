import re
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import get_league_info, _fuzzy_find_player, player_per_game_df, _ensure_loaded
from actions.llm_answer import compose_answer


class ActionLeagueInfo(Action):
    def name(self) -> Text:
        return "action_league_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        text = tracker.latest_message.get("text", "").lower()

        if "difference" in text and ("nba" in text or "aba" in text):
            response = (
                "The NBA (National Basketball Association) and ABA (American Basketball Association) "
                "were rival professional basketball leagues until they merged in 1976.\n\n"
                "Key differences:\n"
                "- The ABA used a red, white, and blue ball; the NBA used an orange ball.\n"
                "- The ABA had a 3-point line; the NBA adopted it later (1979).\n"
                "- The ABA was known for a more exciting, above-the-rim style of play.\n"
                "- The ABA had teams like the Indiana Pacers, Denver Nuggets, San Antonio Spurs, "
                "and New York Nets (now Brooklyn Nets), which joined the NBA after the merger.\n"
                "- The ABA operated from 1967 to 1976. The NBA was founded in 1946."
            )
            response = compose_answer(tracker.latest_message.get("text", ""), response, response)
            dispatcher.utter_message(text=response)
            return []

        player_name = self._extract_player_from_text(text)
        if player_name:
            _ensure_loaded()
            found = _fuzzy_find_player(player_name, player_per_game_df)
            if found:
                response = f"{found} played in the NBA."
                response = compose_answer(tracker.latest_message.get("text", ""), response, response)
                dispatcher.utter_message(text=response)
                return []

        info = get_league_info()
        response = f"The database covers {', '.join(info['leagues'])} records from {info['season_range']}. "
        response += f"It includes {info['total_players']} players and {info['total_teams']} teams."
        response = compose_answer(tracker.latest_message.get("text", ""), response, response)
        dispatcher.utter_message(text=response)
        return []

    @staticmethod
    def _extract_player_from_text(text: str) -> str:
        cleaned = text.lower().strip()
        for phrase in ["what league did", "which league did", "what league does",
                       "which league does", "what league"]:
            cleaned = cleaned.replace(phrase, " ")
        cleaned = re.sub(r'\b(the|a|an|play|plays|played|do|does|did|is|was|in|for)\b', ' ', cleaned)
        cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if not cleaned:
            return None
        return cleaned
