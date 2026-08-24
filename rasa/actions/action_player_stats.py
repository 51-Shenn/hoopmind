from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.data_loader import get_player_stats


class ActionPlayerStats(Action):
    def name(self) -> Text:
        return "action_player_stats"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        player_name = tracker.get_slot("player")
        season = tracker.get_slot("season")

        if not player_name:
            latest_msg = tracker.latest_message.get("text", "").lower()
            for prefix in ["what were", "show me", "how many", "what are", "what was", "show"]:
                latest_msg = latest_msg.replace(prefix, "")
            for word in ["stats", "statistics", "numbers", "points", "rebounds", "assists"]:
                latest_msg = latest_msg.replace(word, "")
            if season:
                latest_msg = latest_msg.replace(season, "")
            parts = latest_msg.strip().strip("'s").strip()
            if parts:
                stats = get_player_stats(parts, season)
                if stats:
                    response = f"{stats['player']}'s {stats['season']} stats with {stats['team']}:\n"
                    response += f"- Points: {stats['points']} PPG\n"
                    response += f"- Rebounds: {stats['rebounds']} RPG\n"
                    response += f"- Assists: {stats['assists']} APG\n"
                    if stats["steals"] > 0:
                        response += f"- Steals: {stats['steals']} SPG\n"
                    if stats["blocks"] > 0:
                        response += f"- Blocks: {stats['blocks']} BPG\n"
                    if stats["fg_pct"] is not None:
                        response += f"- FG%: {stats['fg_pct']}%\n"
                    if stats["three_pct"] is not None:
                        response += f"- 3P%: {stats['three_pct']}%\n"
                    dispatcher.utter_message(text=response)
                    return []
            dispatcher.utter_message(text="I'm not sure which player you're asking about. Could you provide their full name?")
            return []

        stats = get_player_stats(player_name, season)
        if stats is None:
            dispatcher.utter_message(text=f"I couldn't find stats for {player_name}. Please check the name and try again.")
            return []

        response = f"{stats['player']}'s {stats['season']} stats with {stats['team']}:\n"
        response += f"- Points: {stats['points']} PPG\n"
        response += f"- Rebounds: {stats['rebounds']} RPG\n"
        response += f"- Assists: {stats['assists']} APG\n"
        if stats["steals"] > 0:
            response += f"- Steals: {stats['steals']} SPG\n"
        if stats["blocks"] > 0:
            response += f"- Blocks: {stats['blocks']} BPG\n"
        if stats["fg_pct"] is not None:
            response += f"- FG%: {stats['fg_pct']}%\n"
        if stats["three_pct"] is not None:
            response += f"- 3P%: {stats['three_pct']}%\n"

        dispatcher.utter_message(text=response)
        return []
