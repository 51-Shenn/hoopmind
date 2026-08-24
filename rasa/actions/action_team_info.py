from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from actions.data_loader import get_team_info


class ActionTeamInfo(Action):
    def name(self) -> Text:
        return "action_team_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        team_name = tracker.get_slot("team")
        if not team_name:
            dispatcher.utter_message(text="Which team are you interested in?")
            return []

        info = get_team_info(team_name)
        if info is None:
            dispatcher.utter_message(text=f"I couldn't find information about {team_name}. Please check the name and try again.")
            return []

        response = f"{info['name']} ({info['abbreviation']}) - {info['season']} season.\n"
        response += f"- Record: {info['wins']}-{info['losses']}\n"
        if info["arena"] and info["arena"] != "nan":
            response += f"- Arena: {info['arena']}\n"
        if info["off_rating"] is not None:
            response += f"- Off Rtg: {info['off_rating']}, Def Rtg: {info['def_rating']}, Net Rtg: {info['net_rating']}\n"
        if info["attendance"] > 0:
            response += f"- Attendance: {info['attendance']:,}\n"

        dispatcher.utter_message(text=response)
        return [SlotSet("team", info["name"])]
