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

        # Remove multi-word phrases first (regex word boundaries)
        multi_phrases = [
            r'when\s+was',
            r'where\s+was',
            r'which\s+team\s+drafted',
            r'which\s+college\s+did',
            r'what\s+pick\s+was',
            r'what\s+round\s+was',
            r'what\s+was\s+the\s+draft\s+position\s+of',
            r'tell\s+me\s+about\s+the\s+draft\s+history\s+of',
            r'draft\s+info\s+for',
            r'who\s+got\s+picked\s+first\s+overall\s+in',
            r'who\s+was\s+the\s+first\s+overall\s+pick\s+in',
            r'who\s+was\s+the\s+second\s+overall\s+pick\s+in',
            r'where\s+did',
            r'get\s+drafted',
            r'drafted\s+in',
            r'nba\s+draft',
        ]
        for pattern in multi_phrases:
            cleaned = re.sub(pattern, ' ', cleaned)

        # Remove single words with word boundaries
        cleaned = re.sub(r'\b(draft|drafted|in|the|a|an|was|is|does|did|do)\b', ' ', cleaned)

        # Remove years
        cleaned = re.sub(r'\b\d{4}\b', '', cleaned)
        cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        if not cleaned:
            return None

        from actions.data_loader import player_per_game_df
        from actions.data_loader import _fuzzy_find_player
        found = _fuzzy_find_player(cleaned, player_per_game_df)
        return found

    @staticmethod
    def _extract_season_from_text(text: str) -> str:
        """Try to extract a season year from the raw message text."""
        matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        if matches:
            return matches[-1]
        return None
