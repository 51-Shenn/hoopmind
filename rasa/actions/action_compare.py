import logging
import re
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import compare_players, _fuzzy_find_player, _PLAYER_SYNONYMS, _normalize_name, _ensure_loaded

logger = logging.getLogger(__name__)


class ActionCompare(Action):
    def name(self) -> Text:
        return "action_compare"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        try:
            player1 = tracker.get_slot("player")
            player2 = tracker.get_slot("player2")
            logger.info(f"action_compare called: player1={player1}, player2={player2}")

            # If either player is missing, extract from text
            if not player1 or not player2:
                extracted = self._extract_players_from_text(tracker.latest_message.get("text", ""))
                logger.info(f"Extracted players from text: {extracted}")
                if extracted:
                    if not player1:
                        player1 = extracted[0]
                    if not player2 and len(extracted) > 1:
                        player2 = extracted[1]

            if not player1 or not player2:
                dispatcher.utter_message(text="Please specify two players to compare. For example: 'compare LeBron James and Michael Jordan'")
                return []

            # Resolve synonyms
            _ensure_loaded()
            resolved1 = _normalize_name(player1)
            if resolved1 in _PLAYER_SYNONYMS:
                player1 = _PLAYER_SYNONYMS[resolved1]
            resolved2 = _normalize_name(player2)
            if resolved2 in _PLAYER_SYNONYMS:
                player2 = _PLAYER_SYNONYMS[resolved2]

            result = compare_players(player1, player2)
            if result is None:
                dispatcher.utter_message(text=f"I couldn't find stats for {player1} or {player2}. Please check the names and try again.")
                return []

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

            dispatcher.utter_message(text=response)
            return []
        except Exception as e:
            logger.error(f"Error in action_compare: {e}", exc_info=True)
            dispatcher.utter_message(text="Sorry, I am having trouble comparing those players. Please try again.")
            return []

    @staticmethod
    def _extract_players_from_text(text: str) -> list:
        """Try to extract two player names from the raw message text."""
        cleaned = text.lower().strip()

        # Remove common phrases
        for phrase in ["compare", "vs", "versus", "and", "or", "with",
                       "who scored more", "who has more", "who had more",
                       "who is better", "who was better", "which player",
                       "how do", "how did", "stats"]:
            cleaned = cleaned.replace(phrase, " ")

        # Remove 4-digit years
        cleaned = re.sub(r'\b\d{4}\b', '', cleaned)

        # Clean up
        cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Split by common separators
        # Try "and" first, then "vs", then space
        parts = None
        for sep in [" and ", " or ", " vs ", " with "]:
            if sep in cleaned:
                parts = [p.strip() for p in cleaned.split(sep) if p.strip()]
                break

        if not parts or len(parts) < 2:
            # Try splitting by comma
            parts = [p.strip() for p in cleaned.split(",") if p.strip()]

        if not parts or len(parts) < 2:
            return None

        # Validate each part is a valid player name using fuzzy matching
        _ensure_loaded()
        from actions.data_loader import player_per_game_df
        validated = []
        for part in parts:
            # Remove filler words
            for word in ["the", "a", "an", "was", "is", "did", "does", "do"]:
                part = part.replace(word, "")
            part = part.strip()
            if not part:
                continue
            found = _fuzzy_find_player(part, player_per_game_df)
            if found:
                validated.append(found)

        return validated if len(validated) >= 2 else None
