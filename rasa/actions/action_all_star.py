from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import get_all_star


class ActionAllStar(Action):
    def name(self) -> Text:
        return "action_all_star"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        player_name = tracker.get_slot("player")
        if not player_name:
            dispatcher.utter_message(text="Which player are you interested in?")
            return []

        info = get_all_star(player_name)
        if info is None:
            dispatcher.utter_message(text=f"I couldn't find All-Star information for {player_name}.")
            return []

        response = f"{info['player']} was selected as an All-Star {info['count']} time(s)."
        if info["seasons"]:
            recent = info["seasons"][-5:]
            response += f" Recent selections: {', '.join(str(s) for s in recent)}"
            if len(info["seasons"]) > 5:
                response += f" and {len(info['seasons']) - 5} more"

        dispatcher.utter_message(text=response)
        return []
