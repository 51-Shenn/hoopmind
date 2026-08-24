from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from actions.data_loader import get_team_info

# Team nickname synonyms for text-parsing fallback
_TEAM_SYNONYMS = {
    "gsw": "Golden State Warriors",
    "warriors": "Golden State Warriors",
    "dubs": "Golden State Warriors",
    "golden state": "Golden State Warriors",
    "lakers": "Los Angeles Lakers",
    "lal": "Los Angeles Lakers",
    "celtics": "Boston Celtics",
    "bos": "Boston Celtics",
    "heat": "Miami Heat",
    "mia": "Miami Heat",
    "bulls": "Chicago Bulls",
    "chi": "Chicago Bulls",
    "knicks": "New York Knicks",
    "nyk": "New York Knicks",
    "sixers": "Philadelphia 76ers",
    "76ers": "Philadelphia 76ers",
    "philly": "Philadelphia 76ers",
    "cavs": "Cleveland Cavaliers",
    "cavaliers": "Cleveland Cavaliers",
    "clips": "Los Angeles Clippers",
    "clippers": "Los Angeles Clippers",
    "nets": "Brooklyn Nets",
    "raptors": "Toronto Raptors",
    "mavs": "Dallas Mavericks",
    "mavericks": "Dallas Mavericks",
    "nuggets": "Denver Nuggets",
    "bucks": "Milwaukee Bucks",
    "suns": "Phoenix Suns",
    "blazers": "Portland Trail Blazers",
    "spurs": "San Antonio Spurs",
    "hawks": "Atlanta Hawks",
    "hornets": "Charlotte Hornets",
    "pistons": "Detroit Pistons",
    "rockets": "Houston Rockets",
    "pacers": "Indiana Pacers",
    "grizzlies": "Memphis Grizzlies",
    "wolves": "Minnesota Timberwolves",
    "timberwolves": "Minnesota Timberwolves",
    "pelicans": "New Orleans Pelicans",
    "thunder": "Oklahoma City Thunder",
    "okc": "Oklahoma City Thunder",
    "magic": "Orlando Magic",
    "kings": "Sacramento Kings",
    "jazz": "Utah Jazz",
    "wizards": "Washington Wizards",
}


class ActionTeamInfo(Action):
    def name(self) -> Text:
        return "action_team_info"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        team_name = tracker.get_slot("team")

        # Fallback: extract team name from message text
        if not team_name:
            latest_msg = tracker.latest_message.get("text", "").strip()
            cleaned = latest_msg.lower()
            for phrase in ["tell me about the", "tell me about", "info on the", "info on",
                           "information about the", "information about", "what about the",
                           "what about", "details about the", "details about", "team"]:
                cleaned = cleaned.replace(phrase, "")
            cleaned = cleaned.strip().strip("?").strip()
            if cleaned:
                # Check team synonyms first
                if cleaned in _TEAM_SYNONYMS:
                    cleaned = _TEAM_SYNONYMS[cleaned]
                team_name = cleaned

        if not team_name:
            dispatcher.utter_message(text="I'm not sure which team you're asking about. Could you provide the team name or abbreviation?")
            return [SlotSet("team", None)]

        # Resolve synonym if it's a known nickname
        resolved = team_name.lower().strip()
        if resolved in _TEAM_SYNONYMS:
            team_name = _TEAM_SYNONYMS[resolved]

        info = get_team_info(team_name)
        if info is None:
            dispatcher.utter_message(text=f"I couldn't find information about {team_name}. Please check the name and try again.")
            return [SlotSet("team", None)]

        response = self._format_response(info)
        dispatcher.utter_message(text=response)
        return [SlotSet("team", None)]

    @staticmethod
    def _format_response(info: dict) -> str:
        response = f"{info['name']} ({info['abbreviation']}) - {info['season']} season.\n"
        response += f"- Record: {info['wins']}-{info['losses']}\n"
        if info["arena"] and str(info["arena"]) != "nan":
            response += f"- Arena: {info['arena']}\n"
        if info["off_rating"] is not None:
            response += f"- Offensive Rating: {info['off_rating']}\n"
            response += f"- Defensive Rating: {info['def_rating']}\n"
            response += f"- Net Rating: {info['net_rating']}\n"
        if info["attendance"] > 0:
            response += f"- Total Home Attendance: {info['attendance']:,}\n"
        return response
