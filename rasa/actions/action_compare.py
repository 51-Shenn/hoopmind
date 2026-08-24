from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import compare_players


class ActionCompare(Action):
    def name(self) -> Text:
        return "action_compare"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        player1 = tracker.get_slot("player")
        player2 = tracker.get_slot("player2")

        if not player1 or not player2:
            dispatcher.utter_message(text="Please specify two players to compare.")
            return []

        result = compare_players(player1, player2)
        if result is None:
            dispatcher.utter_message(text=f"I couldn't find stats for {player1} or {player2}. Please check the names and try again.")
            return []

        p1 = result["player1"]
        p2 = result["player2"]

        response = f"{p1['player']} ({p1['season']}) vs {p2['player']} ({p2['season']}):\n"
        response += f"- Points Per Game (PPG): {p1['points']} vs {p2['points']}\n"
        response += f"- Rebounds Per Game (RPG): {p1['rebounds']} vs {p2['rebounds']}\n"
        response += f"- Assists Per Game (APG): {p1['assists']} vs {p2['assists']}\n"
        response += f"- Steals Per Game (SPG): {p1['steals']} vs {p2['steals']}\n"
        response += f"- Blocks Per Game (BPG): {p1['blocks']} vs {p2['blocks']}\n"
        if p1["fg_pct"] is not None and p2["fg_pct"] is not None:
            response += f"- Field Goal Percentage (FG%): {p1['fg_pct']}% vs {p2['fg_pct']}%\n"
        if p1["three_pct"] is not None and p2["three_pct"] is not None:
            response += f"- Three-Point Percentage (3P%): {p1['three_pct']}% vs {p2['three_pct']}%\n"

        dispatcher.utter_message(text=response)
        return []
