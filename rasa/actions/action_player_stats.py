import logging
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from actions.data_loader import get_player_stats, _fuzzy_find_player, _PLAYER_SYNONYMS, _normalize_name, _ensure_loaded

logger = logging.getLogger(__name__)


class ActionPlayerStats(Action):
    def name(self) -> Text:
        return "action_player_stats"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        try:
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

            if not player_name:
                dispatcher.utter_message(text="I'm not sure which player you're asking about. Could you provide their full name?")
                return [SlotSet("player", None), SlotSet("season", None)]

            # Resolve nickname/synonym to full name
            resolved = _normalize_name(player_name)
            if resolved in _PLAYER_SYNONYMS:
                player_name = _PLAYER_SYNONYMS[resolved]
                logger.info(f"Resolved synonym to: {player_name}")

            # Try to find the player in the dataset first
            _ensure_loaded()
            found = _fuzzy_find_player(player_name)
            if not found:
                dispatcher.utter_message(text=f"I couldn't find a player named '{player_name}' in our database. Please check the name and try again.")
                return [SlotSet("player", None), SlotSet("season", None)]

            # Look up stats
            stats = get_player_stats(player_name, season)
            if stats is None:
                if season:
                    dispatcher.utter_message(text=f"I found {found} in our database, but there are no stats for the {season} season. They may not have played that year.")
                else:
                    dispatcher.utter_message(text=f"I found {found} but couldn't retrieve their stats. Try specifying a season year.")
                return [SlotSet("player", None), SlotSet("season", None)]

            response = self._format_response(stats)
            dispatcher.utter_message(text=response)
            return [SlotSet("player", None), SlotSet("season", None)]
        except Exception as e:
            logger.error(f"Error in action_player_stats: {e}", exc_info=True)
            dispatcher.utter_message(text="Sorry, I am having trouble looking up those stats. Please try again in a few minutes.")
            return [SlotSet("player", None), SlotSet("season", None)]

    @staticmethod
    def _extract_player_from_text(text: str, season: str = None) -> str:
        """Try to extract a player name from the raw message text."""
        import re
        cleaned = text.lower().strip()
        for phrase in ["what were", "show me", "how many", "what are", "what was",
                       "what is", "show", "give me", "how did", "how good was"]:
            cleaned = cleaned.replace(phrase, "")
        for word in ["stats", "statistics", "numbers", "career totals",
                     "per game", "per 100", "per 36", "'s", "'s"]:
            cleaned = cleaned.replace(word, "")
        if season:
            cleaned = cleaned.replace(season, "")
        # Remove 4-digit years (seasons) from the text
        cleaned = re.sub(r'\b\d{4}\b', '', cleaned)
        # Clean up extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned if cleaned else None

    @staticmethod
    def _extract_season_from_text(text: str) -> str:
        """Try to extract a season year from the raw message text."""
        import re
        # Look for 4-digit years (1900-2099)
        matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        if matches:
            # Return the last year found (most likely the season)
            return matches[-1]
        return None

    @staticmethod
    def _format_response(stats: dict) -> str:
        response = f"{stats['player']}'s {stats['season']} stats with {stats['team']}:\n"
        response += f"- Points Per Game (PPG): {stats['points']}\n"
        response += f"- Rebounds Per Game (RPG): {stats['rebounds']}\n"
        response += f"- Assists Per Game (APG): {stats['assists']}\n"
        if stats["steals"] > 0:
            response += f"- Steals Per Game (SPG): {stats['steals']}\n"
        if stats["blocks"] > 0:
            response += f"- Blocks Per Game (BPG): {stats['blocks']}\n"
        if stats["fg_pct"] is not None:
            response += f"- Field Goal Percentage (FG%): {stats['fg_pct']}%\n"
        if stats["three_pct"] is not None:
            response += f"- Three-Point Percentage (3P%): {stats['three_pct']}%\n"
        return response
