from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import get_dataset_scope
from actions.llm_answer import compose_answer


class ActionDatasetScope(Action):
    def name(self) -> Text:
        return "action_dataset_scope"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        info = get_dataset_scope()
        response = f"Our NBA database covers {info['season_range']} ({', '.join(info['leagues'])}). "
        response += f"It contains {info['total_players']} players, {info['total_teams']} teams, "
        response += f"and {info['total_seasons']} seasons of data."
        response = compose_answer(tracker.latest_message.get("text", ""), response, response)
        dispatcher.utter_message(text=response)
        return []
