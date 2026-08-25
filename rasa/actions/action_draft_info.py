import logging
import re
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import get_draft_info, get_draft_year, _fuzzy_find_player, _PLAYER_SYNONYMS, _normalize_name, _ensure_loaded, draft_df

logger = logging.getLogger(__name__)


class ActionDraftInfo(Action):
    def name(self) -> Text:
        return "action_draft_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Always extract from current message first
        latest_msg = tracker.latest_message.get("text", "")
        player_name = self._extract_player_from_text(latest_msg)
        season = self._extract_season_from_text(latest_msg)
        logger.info(f"Extracted from text: player={player_name}, season={season}")

        # Fallback to slots only if extraction failed
        if not player_name:
            player_name = tracker.get_slot("player")
        if not season:
            season = tracker.get_slot("season")
        logger.info(f"Final values: player={player_name}, season={season}")

        # Priority 1: Player-based lookup
        if player_name:
            resolved = _normalize_name(player_name)
            if resolved in _PLAYER_SYNONYMS:
                player_name = _PLAYER_SYNONYMS[resolved]

            _ensure_loaded()
            found = _fuzzy_find_player(player_name, draft_df, col="player")
            if not found:
                dispatcher.utter_message(text=f"I couldn't find draft information for '{player_name}'. Please check the name and try again.")
                return []

            info = get_draft_info(player_name)
            if info is None:
                dispatcher.utter_message(text=f"I couldn't find draft information for {player_name}.")
                return []

            response = f"{info['player']} was drafted in {info['season']}, Pick #{info['overall_pick']} (Round {info['round']}) by {info['team']}."
            if season and str(info['season']) != season:
                response = f"{info['player']} was not drafted in {season}. " + response
            if info["college"] and info["college"] not in ("nan", "Unknown", ""):
                response += f" College: {info['college']}."
            dispatcher.utter_message(text=response)
            return []

        # Priority 2: Year-based lookup
        if season:
            year_info = get_draft_year(season)
            if year_info:
                response = f"Top 5 picks in the {year_info['year']} NBA Draft:\n"
                for pick in year_info["top_5"]:
                    response += f"  #{pick['pick']}: {pick['player']} ({pick['team']})\n"
                response += f"Total picks: {year_info['total_picks']}"
                dispatcher.utter_message(text=response)
                return []
            else:
                dispatcher.utter_message(text=f"I don't have draft data for the {season} NBA Draft.")
                return []

        # Priority 3: No player or season - ask for clarification
        dispatcher.utter_message(text="I can help with draft info. Which player are you interested in, or which year's draft?")
        return []

    @staticmethod
    def _extract_player_from_text(text: str) -> str:
        """Try to extract a player name from the raw message text."""
        cleaned = text.lower().strip()
        for phrase in ["when was", "where was", "which team drafted", "which college did",
                       "what pick was", "what round was", "what was the draft position of",
                       "tell me about the draft history of", "draft info for",
                       "who got picked first overall in", "who was the first overall pick in",
                       "who was the second overall pick in", "where did", "get drafted",
                       "drafted in", "nba draft", "draft", "in"]:
            cleaned = cleaned.replace(phrase, "")
        # Remove 4-digit years
        cleaned = re.sub(r'\b\d{4}\b', '', cleaned)
        # Remove common filler words
        for word in ["the", "a", "an", "was", "is", "does", "did", "do"]:
            cleaned = cleaned.replace(word, "")
        cleaned = re.sub(r'\s+', ' ', cleaned).strip().strip("?").strip()
        return cleaned if cleaned else None

    @staticmethod
    def _extract_season_from_text(text: str) -> str:
        """Try to extract a season year from the raw message text."""
        matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        if matches:
            return matches[-1]
        return None
