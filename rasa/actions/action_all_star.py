from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import get_all_star, get_player_info


class ActionAllStar(Action):
    def name(self) -> Text:
        return "action_all_star"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        player_name = tracker.get_slot("player")
        if not player_name:
            # Try to extract from message text
            cleaned = tracker.latest_message.get("text", "").lower().strip()
            for phrase in ["was", "how many", "all-star", "all star", "selections",
                           "does", "have", "did", "make", "is", "an", "the", "team",
                           "in", "end of season"]:
                cleaned = cleaned.replace(phrase, "")
            cleaned = cleaned.strip().strip("?").strip()
            if cleaned:
                # Try resolving via get_player_info (uses synonyms + fuzzy matching)
                info = get_player_info(cleaned)
                if info:
                    player_name = info["name"]
        if not player_name:
            dispatcher.utter_message(text="Which player's All-Star history would you like to see?")
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
