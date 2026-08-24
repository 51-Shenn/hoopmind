from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import get_team_stats


class ActionTeamStats(Action):
    def name(self) -> Text:
        return "action_team_stats"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        team_name = tracker.get_slot("team")
        season = tracker.get_slot("season")

        if not team_name:
            dispatcher.utter_message(text="Which team are you interested in?")
            return []
        if not season:
            dispatcher.utter_message(text="Which season?")
            return []

        stats = get_team_stats(team_name, season)
        if stats is None:
            dispatcher.utter_message(text=f"I couldn't find stats for {team_name} in {season}. Please check and try again.")
            return []

        response = f"{stats['team']} {stats['season']} stats ({stats['games']} games):\n"
        response += f"- Points Per Game (PPG): {stats['points']}\n"
        response += f"- Rebounds Per Game (RPG): {stats['rebounds']}\n"
        response += f"- Assists Per Game (APG): {stats['assists']}\n"
        if stats["fg_pct"] is not None:
            response += f"- Field Goal Percentage (FG%): {stats['fg_pct']}%\n"
        if stats["three_pct"] is not None:
            response += f"- Three-Point Percentage (3P%): {stats['three_pct']}%\n"

        dispatcher.utter_message(text=response)
        return []
