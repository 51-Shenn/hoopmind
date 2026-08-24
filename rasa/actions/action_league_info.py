from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import get_league_info


class ActionLeagueInfo(Action):
    def name(self) -> Text:
        return "action_league_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        info = get_league_info()
        response = f"The database covers {', '.join(info['leagues'])} records from {info['season_range']}. "
        response += f"It includes {info['total_players']} players and {info['total_teams']} teams."
        dispatcher.utter_message(text=response)
        return []
