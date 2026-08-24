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
            latest_msg = tracker.latest_message.get("text", "")
            parts = latest_msg.lower().strip()
            for phrase in ["tell me about", "info on", "information about", "what about"]:
                parts = parts.replace(phrase, "")
            parts = parts.strip()
            if parts:
                info = get_team_info(parts)
                if info:
                    response = f"{info['name']} ({info['abbreviation']}) - {info['season']} season.\n"
                    response += f"- Record: {info['wins']}-{info['losses']}\n"
                    if info["arena"] and info["arena"] != "nan":
                        response += f"- Arena: {info['arena']}\n"
                    if info["off_rating"] is not None:
                        response += f"- Offensive Rating: {info['off_rating']}\n"
                        response += f"- Defensive Rating: {info['def_rating']}\n"
                        response += f"- Net Rating: {info['net_rating']}\n"
                    if info["attendance"] > 0:
                        response += f"- Total Home Attendance: {info['attendance']:,}\n"
                    dispatcher.utter_message(text=response)
                    return [SlotSet("team", info["name"])]
            dispatcher.utter_message(text="I'm not sure which team you're asking about. Could you provide the team name or abbreviation?")
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
            response += f"- Offensive Rating: {info['off_rating']}\n"
            response += f"- Defensive Rating: {info['def_rating']}\n"
            response += f"- Net Rating: {info['net_rating']}\n"
        if info["attendance"] > 0:
            response += f"- Total Home Attendance: {info['attendance']:,}\n"

        dispatcher.utter_message(text=response)
        return [SlotSet("team", info["name"])]
