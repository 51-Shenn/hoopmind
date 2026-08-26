from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from actions.data_loader import get_award_winner, get_player_awards
from actions.entity_extract import extract_player, extract_season
from actions.llm_answer import compose_answer


class ActionAwardWinner(Action):
    """Get the winner of a specific award in a given season."""

    def name(self) -> Text:
        return "action_award_winner"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        # Always extract from current message first
        text = tracker.latest_message.get("text", "").lower()

        season = extract_season(text)

        award = None
        award_keywords = {
            'mvp': 'MVP',
            'most valuable player': 'MVP',
            'dpoy': 'DPOY',
            'defensive player of the year': 'DPOY',
            'defensive player': 'DPOY',
            'roy': 'ROY',
            'rookie of the year': 'ROY',
            'sixth man': 'SMOY',
            'sixth man of the year': 'SMOY',
            'smoy': 'SMOY',
            'most improved': 'MIP',
            'most improved player': 'MIP',
            'mip': 'MIP',
            'finals mvp': 'Finals MVP',
            'finals most valuable': 'Finals MVP',
        }
        for keyword, award_name in award_keywords.items():
            if keyword in text:
                award = award_name
                break

        # Fallback to slots only if extraction failed
        if not award:
            award = tracker.get_slot("award")
        if not season:
            season = tracker.get_slot("season")

        if not award:
            dispatcher.utter_message(text="Which award are you asking about? (e.g., MVP, DPOY, ROY)")
            return []

        if not season:
            dispatcher.utter_message(text="Which season? (e.g., 2016)")
            return []

        try:
            season_int = int(season)
        except (ValueError, TypeError):
            dispatcher.utter_message(text="Please provide a valid season year (e.g., 2016).")
            return []

        result = get_award_winner(award, season_int)

        if not result:
            dispatcher.utter_message(
                text=f"I couldn't find who won {award} in {season_int}."
            )
            return []

        response = f"{result['player']} won the {result['award'].upper()} in the {result['season']} season."
        response = compose_answer(tracker.latest_message.get("text", ""), response, response)
        dispatcher.utter_message(text=response)

        return [
            SlotSet("player", result['player']),
            SlotSet("award", award),
            SlotSet("season", str(season_int)),
        ]


class ActionPlayerAwards(Action):
    """Get all awards won by a player."""

    def name(self) -> Text:
        return "action_player_awards"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        # Always extract from current message first
        player = extract_player(tracker.latest_message.get("text", ""))

        # Fallback to slot only if message extraction failed
        if not player:
            player = tracker.get_slot("player")

        if not player:
            dispatcher.utter_message(text="Which player are you asking about?")
            return []

        result = get_player_awards(player)

        if not result:
            dispatcher.utter_message(
                text=f"I couldn't find award information for {player}."
            )
            return []

        if result['count'] == 0:
            response = f"{result['player']} has not won any major NBA awards."
        else:
            award_lines = []
            for award_name, count in result['award_counts'].items():
                award_lines.append(f"- {award_name}: {count}")

            awards_text = "\n".join(award_lines)
            response = (
                f"{result['player']} has won {result['count']} award(s):\n"
                f"{awards_text}"
            )

        response = compose_answer(tracker.latest_message.get("text", ""), response, response)
        dispatcher.utter_message(text=response)

        return [SlotSet("player", result['player'])]
