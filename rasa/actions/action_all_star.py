import logging
import re
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import get_all_star, get_player_info, _ensure_loaded
from actions.entity_extract import extract_player, extract_season
from actions.llm_answer import compose_answer
import actions.data_loader as data_loader

logger = logging.getLogger(__name__)


class ActionAllStar(Action):
    def name(self) -> Text:
        return "action_all_star"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        try:
            latest_msg = tracker.latest_message.get("text", "")
            player_name = self._extract_player_from_text(latest_msg)
            season = self._extract_season_from_text(latest_msg)
            logger.info(f"Extracted: player={player_name}, season={season}")

            # Roster queries ("who played in the 2010 All-Star Game") - only
            # when no specific player was named, so "was X an All-Star in Y"
            # still answers about X.
            if not player_name and self._is_roster_query(latest_msg) and season:
                _ensure_loaded()
                roster = self._get_roster_by_season(int(season))
                if roster:
                    from collections import defaultdict
                    teams = defaultdict(list)
                    for p, t in roster:
                        teams[t].append(p)
                    response = f"The {season} NBA All-Star Game featured:\n"
                    for team_name, players in teams.items():
                        response += f"{team_name}: {', '.join(players)}\n"
                    dispatcher.utter_message(text=response.strip())
                else:
                    dispatcher.utter_message(text=f"I couldn't find All-Star roster data for {season}.")
                return []

            # Handle All-NBA queries
            if 'all-nba' in latest_msg.lower():
                dispatcher.utter_message(text="I don't have All-NBA team data available. I can help with All-Star selections, player stats, or team stats.")
                return []

            if not player_name:
                player_name = tracker.get_slot("player")

            if not player_name:
                dispatcher.utter_message(text="Which player's All-Star history would you like to see?")
                return []

            _ensure_loaded()
            info = get_all_star(player_name)
            if info is None:
                dispatcher.utter_message(text=f"I couldn't find All-Star information for {player_name}.")
                return []

            # Year-specific query: answer Yes/No
            if season:
                year = int(season)
                if year in info["seasons"]:
                    response = f"Yes, {info['player']} was an All-Star in {year}."
                else:
                    response = f"No, {info['player']} was not an All-Star in {year}."
                response = compose_answer(tracker.latest_message.get("text", ""), response, response)
                dispatcher.utter_message(text=response)
                return []

            # General query: show total count and recent selections
            response = f"{info['player']} was selected as an All-Star {info['count']} time(s)."
            if info["seasons"]:
                recent = info["seasons"][-5:]
                response += f" Recent selections: {', '.join(str(s) for s in recent)}"
                if len(info["seasons"]) > 5:
                    response += f" and {len(info['seasons']) - 5} more"

            response = compose_answer(tracker.latest_message.get("text", ""), response, response)
            dispatcher.utter_message(text=response)
            return []
        except Exception as e:
            logger.error(f"Error in action_all_star: {e}", exc_info=True)
            dispatcher.utter_message(text="Sorry, I am having trouble looking up that information. Please try again.")
            return []

    @staticmethod
    def _is_roster_query(text: str) -> bool:
        return bool(re.search(r'played\s+in|\broster\b|who\s+(was|were)\s+', text.lower()))

    @staticmethod
    def _get_roster_by_season(season: int) -> List[tuple]:
        _ensure_loaded()
        mask = data_loader.all_star_df["season"] == season
        players = data_loader.all_star_df[mask][["player", "team"]].values.tolist()
        return players

    @staticmethod
    def _extract_player_from_text(text: str) -> str:
        cleaned = text.lower().strip()

        # Handle non-player queries first
        if re.match(r'^(who\s+)?played\s+in\b', cleaned):
            return None
        if 'all-nba' in cleaned:
            return None

        return extract_player(text)

    @staticmethod
    def _extract_season_from_text(text: str) -> str:
        return extract_season(text)
