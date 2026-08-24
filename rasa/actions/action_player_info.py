from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from actions.data_loader import get_player_info


class ActionPlayerInfo(Action):
    def name(self) -> Text:
        return "action_player_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        player_name = tracker.get_slot("player")
        if not player_name:
            latest_msg = tracker.latest_message.get("text", "")
            parts = latest_msg.lower().replace("who is", "").replace("tell me about", "").replace("info on", "").replace("information about", "").strip()
            if parts:
                info = get_player_info(parts)
                if info:
                    ht = info["height_inches"]
                    height_str = f"{int(ht // 12)}'{int(ht % 12)}\"" if ht and ht > 0 else "Unknown"
                    response = f"{info['name']} is a {info['position']}, {height_str}, {int(info['weight_lbs'])} lbs."
                    if info["birth_date"] and info["birth_date"] != "Unknown":
                        response += f" Born {info['birth_date']}."
                    if info["college"] and info["college"] == info["college"]:
                        response += f" College: {info['college']}."
                    if info["career_from"] and info["career_to"]:
                        response += f" Career: {info['career_from']}-{info['career_to']}."
                    if info["teams_played"]:
                        response += f" Teams: {', '.join(info['teams_played'])}."
                    if info["hall_of_fame"]:
                        response += " Hall of Famer."
                    dispatcher.utter_message(text=response)
                    return [SlotSet("player", info["name"])]
            dispatcher.utter_message(text="I'm not sure which player you're asking about. Could you provide their full name?")
            return []

        info = get_player_info(player_name)
        if info is None:
            dispatcher.utter_message(text=f"I couldn't find information about {player_name}. Please check the name and try again.")
            return []

        ht = info["height_inches"]
        height_str = f"{int(ht // 12)}'{int(ht % 12)}\"" if ht and ht > 0 else "Unknown"

        response = f"{info['name']} is a {info['position']}, {height_str}, {int(info['weight_lbs'])} lbs."
        if info["birth_date"] and info["birth_date"] != "Unknown":
            response += f" Born {info['birth_date']}."
        if info["college"] and info["college"] == info["college"]:
            response += f" College: {info['college']}."
        if info["career_from"] and info["career_to"]:
            response += f" Career: {info['career_from']}-{info['career_to']}."
        if info["teams_played"]:
            response += f" Teams: {', '.join(info['teams_played'])}."
        if info["hall_of_fame"]:
            response += " Hall of Famer."

        dispatcher.utter_message(text=response)
        return [SlotSet("player", info["name"])]
