from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import get_draft_info, get_draft_year


class ActionDraftInfo(Action):
    def name(self) -> Text:
        return "action_draft_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        player_name = tracker.get_slot("player")
        season = tracker.get_slot("season")

        if not player_name and season:
            year_info = get_draft_year(season)
            if year_info:
                response = f"Top 5 picks in the {year_info['year']} NBA Draft:\n"
                for pick in year_info["top_5"]:
                    response += f"  #{pick['pick']}: {pick['player']} ({pick['team']})\n"
                response += f"Total picks: {year_info['total_picks']}"
                dispatcher.utter_message(text=response)
                return []

        if not player_name:
            latest_msg = tracker.latest_message.get("text", "").lower()
            import re
            year_match = re.search(r'\b(19|20)\d{2}\b', latest_msg)
            if year_match:
                year_info = get_draft_year(year_match.group())
                if year_info:
                    response = f"Top 5 picks in the {year_info['year']} NBA Draft:\n"
                    for pick in year_info["top_5"]:
                        response += f"  #{pick['pick']}: {pick['player']} ({pick['team']})\n"
                    response += f"Total picks: {year_info['total_picks']}"
                    dispatcher.utter_message(text=response)
                    return []
            dispatcher.utter_message(text="I can help with draft info. Which player are you interested in, or which year's draft?")
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
