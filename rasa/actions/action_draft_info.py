from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import get_draft_info


class ActionDraftInfo(Action):
    def name(self) -> Text:
        return "action_draft_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        player_name = tracker.get_slot("player")
        if not player_name:
            dispatcher.utter_message(text="Which player are you interested in?")
            return []

        info = get_draft_info(player_name)
        if info is None:
            dispatcher.utter_message(text=f"I couldn't find draft information for {player_name}.")
            return []

        response = f"{info['player']} was drafted in {info['season']}, Pick #{info['overall_pick']} (Round {info['round']}) by {info['team']}."
        if info["college"] and info["college"] != "nan":
            response += f" College: {info['college']}."

        dispatcher.utter_message(text=response)
        return []
