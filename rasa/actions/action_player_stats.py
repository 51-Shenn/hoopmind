import re
import logging
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from actions.data_loader import (
    get_player_stats, get_per_36_stats, get_per_100_stats,
    get_advanced_stats, get_career_totals, get_shooting_stats,
    normalize_stat_type,
    _fuzzy_find_player, _PLAYER_SYNONYMS, _normalize_name, _ensure_loaded
)

logger = logging.getLogger(__name__)


class ActionPlayerStats(Action):
    def name(self) -> Text:
        return "action_player_stats"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        try:
            latest_msg = tracker.latest_message.get("text", "")
            player_name = self._extract_player_from_text(latest_msg)
            season = self._extract_season_from_text(latest_msg)
            stat_type_raw = self._extract_stat_type_from_text(latest_msg)
            logger.info(f"Extracted: player={player_name}, season={season}, stat_type={stat_type_raw}")

            if not player_name:
                player_name = tracker.get_slot("player")
            if not season:
                season = tracker.get_slot("season")
            if not stat_type_raw:
                stat_type_raw = tracker.get_slot("stat_type")

            if not stat_type_raw:
                for entity in tracker.latest_message.get("entities", []):
                    if entity.get("entity") == "stat_type":
                        stat_type_raw = entity.get("value")
                        break

            stat_type = normalize_stat_type(stat_type_raw)
            logger.info(f"Final: player={player_name}, season={season}, stat_type={stat_type}")

            if not player_name:
                dispatcher.utter_message(text="I'm not sure which player you're asking about. Could you provide their full name?")
                return [SlotSet("player", None), SlotSet("season", None), SlotSet("stat_type", None)]

            resolved = _normalize_name(player_name)
            if resolved in _PLAYER_SYNONYMS:
                player_name = _PLAYER_SYNONYMS[resolved]

            _ensure_loaded()
            found = _fuzzy_find_player(player_name)
            if not found:
                dispatcher.utter_message(text=f"I couldn't find a player named '{player_name}' in our database. Please check the name and try again.")
                return [SlotSet("player", None), SlotSet("season", None), SlotSet("stat_type", None)]

            stats = None
            if stat_type == "per_36":
                stats = get_per_36_stats(player_name, season)
            elif stat_type == "per_100":
                stats = get_per_100_stats(player_name, season)
            elif stat_type == "advanced":
                stats = get_advanced_stats(player_name, season)
            elif stat_type == "career_totals":
                stats = get_career_totals(player_name)
            elif stat_type == "shooting":
                stats = get_shooting_stats(player_name, season)
            else:
                stats = get_player_stats(player_name, season)

            if stats is None:
                if season:
                    dispatcher.utter_message(text=f"I found {found} in our database, but there are no {self._stat_type_label(stat_type)} stats for the {season} season.")
                else:
                    dispatcher.utter_message(text=f"I found {found} but couldn't retrieve their {self._stat_type_label(stat_type)} stats. Try specifying a season year.")
                return [SlotSet("player", None), SlotSet("season", None), SlotSet("stat_type", None)]

            response = self._format_response(stats, stat_type, latest_msg)
            dispatcher.utter_message(text=response)
            return [SlotSet("player", None), SlotSet("season", None), SlotSet("stat_type", None)]
        except Exception as e:
            logger.error(f"Error in action_player_stats: {e}", exc_info=True)
            dispatcher.utter_message(text="Sorry, I am having trouble looking up those stats. Please try again in a few minutes.")
            return [SlotSet("player", None), SlotSet("season", None), SlotSet("stat_type", None)]

    @staticmethod
    def _extract_player_from_text(text: str, season: str = None) -> str:
        cleaned = text.lower().strip()
        for phrase in ["what were", "show me", "how many", "what are", "what was",
                       "what is", "show", "give me", "how did", "how good was",
                       "how many points did", "how many assists did",
                       "how many rebounds did", "how many steals did",
                       "how many blocks did", "career points of",
                       "career stats for", "per 36 minutes stats for",
                       "per 36 stats for", "per 100 stats for",
                       "per 36 minutes for", "per 36 for"]:
            cleaned = cleaned.replace(phrase, "")
        for word in ["stats", "statistics", "numbers", "career totals",
                     "per game", "per 100", "per 36", "per 100 possessions",
                     "shooting splits for", "shooting splits",
                     "shooting", "splits", "points", "rebounds", "assists",
                     "steals", "blocks", "average", "career",
                     "per", "for", "in", "did", "was", "is", "season",
                     "warp", "vorp", "bpm", "ws", "ts", "true shooting",
                     "usage", "win shares", "offensive rating", "defensive rating"]:
            cleaned = cleaned.replace(word, "")
        cleaned = cleaned.replace("\u2019", "").replace("\u2018", "").replace("'", "")
        if season:
            cleaned = cleaned.replace(season, "")
        cleaned = re.sub(r'\b\d{4}\b', '', cleaned)
        cleaned = re.sub(r"[^\w\s-]", '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned if cleaned else None

    @staticmethod
    def _extract_season_from_text(text: str) -> str:
        matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        if matches:
            return matches[-1]
        return None

    @staticmethod
    def _extract_stat_type_from_text(text: str) -> str:
        lower = text.lower().strip()

        if 'per 36' in lower or 'per-36' in lower or 'per36' in lower:
            return "per_36"
        if 'per 100' in lower or 'per-100' in lower or 'per100' in lower:
            return "per_100"
        if 'career total' in lower or ('career' in lower and any(w in lower for w in ['points', 'rebounds', 'assists', 'steals', 'blocks'])):
            return "career_totals"
        if 'shooting split' in lower or 'shooting stat' in lower:
            return "shooting"
        if 'per minute' in lower or 'per-minute' in lower:
            return "per_36"

        if re.search(r'per[\s-]?36', lower):
            return "per_36"
        if re.search(r'per[\s-]?100', lower):
            return "per_100"
        if re.search(r'shooting\s+splits?', lower):
            return "shooting"
        if re.search(r'\badvanced\b', lower):
            return "advanced"
        if re.search(r'\b(per|vorp|bpm|ws|ts%|true shooting|usage|win shares|offensive rating|defensive rating|warp)\b', lower):
            return "advanced"
        return None

    @staticmethod
    def _stat_type_label(stat_type: str) -> str:
        labels = {
            "per_36": "per-36-minute",
            "per_100": "per-100-possession",
            "advanced": "advanced",
            "career_totals": "career total",
            "shooting": "shooting",
            "per_game": "per-game",
        }
        return labels.get(stat_type, stat_type)

    @staticmethod
    def _detect_specific_stat(text: str) -> str:
        lower = text.lower()
        # Check for "per" as standalone word (PER stat) but not "per 36" or "per 100"
        if re.search(r'\bper\b', lower) and not re.search(r'per[\s-]?(36|100)', lower):
            return 'per'
        stat_map = {
            'points': 'points', 'point': 'points', 'ppg': 'points', 'score': 'points',
            'rebounds': 'rebounds', 'rebound': 'rebounds', 'rpg': 'rebounds', 'boards': 'rebounds',
            'assists': 'assists', 'assist': 'assists', 'apg': 'assists',
            'steals': 'steals', 'steal': 'steals',
            'blocks': 'blocks', 'block': 'blocks',
            'turnovers': 'turnovers', 'turnover': 'turnovers',
            'field goal': 'fg_pct', 'fg%': 'fg_pct', 'fg percentage': 'fg_pct',
            'three point': 'three_pct', '3pt': 'three_pct', '3p%': 'three_pct',
            'free throw': 'ft_pct', 'ft%': 'ft_pct',
            'games': 'games', 'games played': 'games',
            'mpg': 'minutes',
            'true shooting': 'ts_pct', 'ts%': 'ts_pct',
            'usage': 'usg_pct', 'usage rate': 'usg_pct',
            'win shares': 'ws',
            'vorp': 'vorp', 'bpm': 'bpm',
            'offensive rating': 'off_rating', 'defensive rating': 'def_rating',
        }
        for keyword, stat in stat_map.items():
            if keyword in lower:
                return stat
        return None

    @staticmethod
    def _format_response(stats: dict, stat_type: str = "per_game", message: str = "") -> str:
        player = stats["player"]
        season = stats.get("season", "")
        team = stats.get("team", "")
        specific = ActionPlayerStats._detect_specific_stat(message) if message else None

        if stat_type == "career_totals":
            if specific:
                val = stats.get(specific)
                if val is not None:
                    return f"{player} had {val} {specific.replace('_', ' ')} in their career ({stats.get('seasons', '')})."
                return f"I found {player}'s career data, but {specific.replace('_', ' ')} isn't available."
            response = f"{player}'s career totals ({stats.get('seasons', '')}):\n"
            response += f"- Points: {stats['points']}\n"
            response += f"- Rebounds: {stats['rebounds']}\n"
            response += f"- Assists: {stats['assists']}\n"
            response += f"- Steals: {stats['steals']}\n"
            response += f"- Blocks: {stats['blocks']}\n"
            if stats.get("fg_pct") is not None:
                response += f"- FG%: {stats['fg_pct']}%\n"
            if stats.get("three_pct") is not None:
                response += f"- 3P%: {stats['three_pct']}%\n"
            if stats.get("ft_pct") is not None:
                response += f"- FT%: {stats['ft_pct']}%\n"
            return response

        if stat_type == "advanced":
            if specific:
                val = stats.get(specific)
                if val is not None:
                    return f"{player}'s {season} {specific.upper().replace('_', ' ')}: {val}"
                return f"I found {player}'s advanced stats for {season}, but {specific.upper().replace('_', ' ')} isn't available."
            response = f"{player}'s {season} advanced stats with {team}:\n"
            for key, label in [("per", "PER"), ("ts_pct", "True Shooting%"), ("usg_pct", "Usage%"),
                               ("ws", "Win Shares"), ("ws_48", "Win Shares/48"), ("bpm", "BPM"),
                               ("vorp", "VORP"), ("ast_pct", "Assist%"), ("trb_pct", "TRB%"),
                               ("stl_pct", "STL%"), ("blk_pct", "BLK%")]:
                if stats.get(key) is not None:
                    response += f"- {label}: {stats[key]}\n"
            return response

        if stat_type == "shooting":
            if specific:
                val = stats.get(specific)
                if val is not None:
                    return f"{player}'s {season} {specific.replace('_', ' ')}: {val}%"
                return f"I found {player}'s shooting stats for {season}, but {specific.replace('_', ' ')} isn't available."
            response = f"{player}'s {season} shooting stats with {team}:\n"
            for key, label in [("fg_pct", "FG%"), ("fg_pct_from_2p", "2P%"), ("fg_pct_from_3p", "3P%"),
                               ("corner_3_pct", "Corner 3P%"), ("pct_fga_from_3p", "% of FGA from 3P"),
                               ("num_dunks", "Dunks"), ("avg_dist_fga", "Avg Distance FGA")]:
                if stats.get(key) is not None:
                    suffix = " ft" if key == "avg_dist_fga" else ("%" if key != "num_dunks" else "")
                    response += f"- {label}: {stats[key]}{suffix}\n"
            return response

        if stat_type == "per_36":
            label = "Per 36 Minutes"
        elif stat_type == "per_100":
            label = "Per 100 Possessions"
        else:
            label = "Per Game"

        if specific:
            val = stats.get(specific)
            if val is not None:
                return f"{player}'s {season} {label} {specific.replace('_', ' ')}: {val}"
            return f"I found {player}'s {label.lower()} stats for {season}, but {specific.replace('_', ' ')} isn't available."

        response = f"{player}'s {season} {label} stats with {team}:\n"
        response += f"- Points: {stats['points']}\n"
        response += f"- Rebounds: {stats['rebounds']}\n"
        response += f"- Assists: {stats['assists']}\n"
        if stats["steals"] > 0:
            response += f"- Steals: {stats['steals']}\n"
        if stats["blocks"] > 0:
            response += f"- Blocks: {stats['blocks']}\n"
        if stats.get("turnovers") is not None and stats["turnovers"] > 0:
            response += f"- Turnovers: {stats['turnovers']}\n"
        if stats.get("fg_pct") is not None:
            response += f"- FG%: {stats['fg_pct']}%\n"
        if stats.get("three_pct") is not None:
            response += f"- 3P%: {stats['three_pct']}%\n"
        if stats.get("ft_pct") is not None:
            response += f"- FT%: {stats['ft_pct']}%\n"
        if stat_type == "per_100":
            if stats.get("off_rating") is not None:
                response += f"- Off Rating: {stats['off_rating']}\n"
            if stats.get("def_rating") is not None:
                response += f"- Def Rating: {stats['def_rating']}\n"
        return response
