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
from actions.entity_extract import extract_player, extract_season
from actions.llm_answer import compose_answer

logger = logging.getLogger(__name__)

# "PER" the advanced stat, but not the "per" in "per game" / "per 36 minutes".
_PER_STAT_RE = re.compile(
    r'\bper\b(?!\s*-?\s*(?:game|min|minute|minutes|36|100|poss|possession|possessions))'
)

# Matched in order, most specific first. Word boundaries matter: the old
# substring map read "three-pointers" as "points" and "percentage" as nothing.
_SPECIFIC_STATS = [
    (re.compile(r'three[\s-]?point|3[\s-]?pt|\b3p%?\b'), 'three_pct'),
    (re.compile(r'free[\s-]?throw|\bft%'), 'ft_pct'),
    (re.compile(r'field[\s-]?goal|\bfg%'), 'fg_pct'),
    (re.compile(r'true[\s-]?shooting|\bts%'), 'ts_pct'),
    (re.compile(r'\busage\b|\busg%'), 'usg_pct'),
    (re.compile(r'win shares?'), 'ws'),
    (re.compile(r'offensive rating'), 'off_rating'),
    (re.compile(r'defensive rating'), 'def_rating'),
    (re.compile(r'\bvorp\b'), 'vorp'),
    (re.compile(r'\bbpm\b'), 'bpm'),
    (re.compile(r'\brebounds?\b|\brpg\b|\bboards\b'), 'rebounds'),
    (re.compile(r'\bassists?\b|\bapg\b'), 'assists'),
    (re.compile(r'\bsteals?\b|\bspg\b'), 'steals'),
    (re.compile(r'\bblocks?\b|\bbpg\b'), 'blocks'),
    (re.compile(r'\bturnovers?\b|\btov\b'), 'turnovers'),
    (re.compile(r'\bpoints?\b|\bppg\b|\bscoring\b|\bscored?\b'), 'points'),
    (re.compile(r'\bgames?\b'), 'games'),
    (re.compile(r'\bmpg\b|\bminutes\b'), 'minutes'),
]

# stat key -> (label, suffix)
_STAT_LABELS = {
    'points': ('Points', ''),
    'rebounds': ('Rebounds', ''),
    'assists': ('Assists', ''),
    'steals': ('Steals', ''),
    'blocks': ('Blocks', ''),
    'turnovers': ('Turnovers', ''),
    'games': ('Games Played', ''),
    'minutes': ('Minutes', ''),
    'fg_pct': ('FG%', '%'),
    'three_pct': ('3P%', '%'),
    'ft_pct': ('FT%', '%'),
    'fg_pct_from_2p': ('2P%', '%'),
    'fg_pct_from_3p': ('3P%', '%'),
    'corner_3_pct': ('Corner 3P%', '%'),
    'ts_pct': ('True Shooting%', ''),
    'usg_pct': ('Usage%', ''),
    'per': ('PER', ''),
    'ws': ('Win Shares', ''),
    'vorp': ('VORP', ''),
    'bpm': ('BPM', ''),
    'off_rating': ('Offensive Rating', ''),
    'def_rating': ('Defensive Rating', ''),
}


def _label_for(stat: str) -> tuple:
    return _STAT_LABELS.get(stat, (stat.replace('_', ' '), ''))


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
            response = compose_answer(tracker.latest_message.get("text", ""), response, response)
            dispatcher.utter_message(text=response)
            return [SlotSet("player", None), SlotSet("season", None), SlotSet("stat_type", None)]
        except Exception as e:
            logger.error(f"Error in action_player_stats: {e}", exc_info=True)
            dispatcher.utter_message(text="Sorry, I am having trouble looking up those stats. Please try again in a few minutes.")
            return [SlotSet("player", None), SlotSet("season", None), SlotSet("stat_type", None)]

    @staticmethod
    def _extract_player_from_text(text: str, season: str = None) -> str:
        return extract_player(text)

    @staticmethod
    def _extract_season_from_text(text: str) -> str:
        return extract_season(text)

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
        if re.search(r'\b(vorp|bpm|ws|ts%|true shooting|usage|win shares|offensive rating|defensive rating|warp)\b', lower):
            return "advanced"
        if _PER_STAT_RE.search(lower):
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
        # "PER" the advanced stat - not "points per game", "per 36", "per 100".
        if _PER_STAT_RE.search(lower):
            return 'per'
        for pattern, stat in _SPECIFIC_STATS:
            if pattern.search(lower):
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
                name, suffix = _label_for(specific)
                if val is not None and val == val:
                    return f"{player} had {val}{suffix} {name.lower()} in their career ({stats.get('seasons', '')})."
                return f"I found {player}'s career data, but {name.lower()} isn't available."
            response = f"{player}'s career totals ({stats.get('seasons', '')}):\n"
            for key, text in [("points", "Points"), ("rebounds", "Rebounds"),
                              ("assists", "Assists"), ("steals", "Steals"),
                              ("blocks", "Blocks")]:
                if stats.get(key) is not None:
                    response += f"- {text}: {stats[key]}\n"
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
                name, suffix = _label_for(specific)
                if val is not None and val == val:
                    return f"{player}'s {season} {name}: {val}{suffix}"
                return f"I found {player}'s advanced stats for {season}, but {name} isn't available."
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
                name, suffix = _label_for(specific)
                if val is not None and val == val:
                    return f"{player}'s {season} {name}: {val}{suffix}"
                return f"I found {player}'s shooting stats for {season}, but {name} isn't available."
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
            name, suffix = _label_for(specific)
            # "Per Game" is the default reading - only spell it out for the
            # rescaled tables, so this reads "Points" not "Per Game Points".
            qualifier = "" if stat_type in (None, "per_game") else f"{label} "
            if val is not None and val == val:
                return f"{player}'s {season} {qualifier}{name}: {val}{suffix}"
            return f"I found {player}'s {label.lower()} stats for {season}, but {name} isn't available."

        response = f"{player}'s {season} {label} stats with {team}:\n"
        # None means the stat was not recorded in that era - rebounds before
        # 1951, steals/blocks/turnovers before 1974 - so omit the line.
        for key, text in [("points", "Points"), ("rebounds", "Rebounds"),
                          ("assists", "Assists")]:
            if stats.get(key) is not None:
                response += f"- {text}: {stats[key]}\n"
        if stats.get("steals"):
            response += f"- Steals: {stats['steals']}\n"
        if stats.get("blocks"):
            response += f"- Blocks: {stats['blocks']}\n"
        if stats.get("turnovers"):
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
