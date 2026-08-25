from __future__ import annotations

import logging
import os
import re
from flask import Flask, jsonify, request

from query_engine import NBAQueryEngine
from response_generator import generate, generate_cards
from entity_extractor import extract as extract_entities

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
engine = NBAQueryEngine()

# Set HOOPMIND_PLAINTEXT=1 to disable rich cards entirely
# (diagnostics / fallback mode).

PLAINTEXT_MODE = bool(os.environ.get("HOOPMIND_PLAINTEXT"))


# ------------------------------------------------------------
# INTENT RESOLUTION
# ------------------------------------------------------------
#
# The deployed agent uses 11 consolidated intents. The engine
# still speaks fine-grained intents, so we map incoming intent
# + parameters + free text onto the right handler here.
# ------------------------------------------------------------
AWARD_WORDS = (
    "award",
    "mvp",
    "most valuable",
    "roy",
    "rookie of the year",
    "dpoy",
    "defensive player",
    "sixth man",
    "mip",
    "most improved",
    "scoring title",
    "won",
)

DRAFT_WORDS = (
    "draft",
    "drafted",
    "pick",
    "round",
    "lottery",
    "undrafted",
    "college",
    "prospect",
)

ALL_STAR_WORDS = (
    "all-star",
    "all star",
    "asg",
    "midseason classic",
    "all-star game",
    "selected to",
)

HONOR_WORDS = (
    "all-nba",
    "all nba",
    "all-defensive",
    "all defensive",
    "all-rookie",
    "all rookie",
    "first team",
    "second team",
    "third team",
    "end-of-season",
    "end of season",
)

CAREER_TOTAL_WORDS = (
    "career total",
    "total career",
    "his career",
    "their career",
    "all-time",
    "all time",
    "entire career",
    "whole career",
)

# e.g. 'Career points of Kareem' / 'career rebounds of Rodman'

STAT_NOUNS = (
    "points",
    "rebounds",
    "assists",
    "steals",
    "blocks",
    "turnovers",
    "scoring",
    "three-pointers",
    "threes",
    "field goals",
    "free throws",
    "games played",
)

ADVANCED_WORDS = (
    "advanced",
    "per",
    "ts%",
    "true shooting",
    "usg",
    "usage",
    "bpm",
    "vorp",
    "win share",
    "obpm",
    "dbpm",
    "efficiency",
    "rating",
    "raptor",
    "eFG%",
    "effective",
)

SHOOTING_WORDS = (
    "shoot",
    "shooting",
    "shot",
    "fg%",
    "field goal",
    "3p%",
    "three point",
    "3-point",
    "three-point",
    "ft%",
    "free throw",
    "2p%",
    "mid-range",
    "distance",
    "dunk",
    "layup",
    "attempt",
)

PBP_WORDS = (
    "play-by-play",
    "play by play",
    "pbp",
    "on-court",
    "on court",
    "on/off",
    "plus-minus",
    "+/-",
    "lineup",
    "possession",
)

OPPONENT_WORDS = (
    "opponent",
    "against",
    "allow",
    "allowed",
    "defensively",
    "defense",
    "give up",
    "surrender",
)

SUMMARY_WORDS = (
    "record",
    "wins and losses",
    "w-l",
    "how did",
    "season summary",
    "overall",
    "finish",
    "standings",
)


# ------------------------------------------------------------
# Free-text STAT inference: the deployed phrases are not
# annotated, so 'Give me the rebounds for Nikola Jokic in
# 2023' arrives with stat EMPTY. Recover it from wording.
# (Award recovery lives inside the engine's winner path.)
# ------------------------------------------------------------
STAT_INFERENCES = [
    (r"\b(true shooting|ts%)\b", "true shooting percentage"),
    (r"\b(player efficiency rating|per rating)\b", "player efficiency rating"),
    (r"\b(usage percentage|usage rate|usg%)\b", "usage percentage"),
    (r"\b(win shares|\bws\b)\b", "win shares"),
    (
        r"\b(value over replacement|\bvorp\b)\b",
        "value over replacement player",
    ),
    (r"\b(box plus.?minus|\bbpm\b)\b", "box plus/minus"),
    (r"\b(offensive rating|ortg)\b", "offensive rating"),
    (r"\b(defensive rating|drtg)\b", "defensive rating"),
    (
        r"\b(three.?point percentage|3p%|three point shooting)\b",
        "three-point percentage",
    ),
    (
        r"\b(field goal percentage|fg%|shooting percentage)\b",
        "field goal percentage",
    ),
    (r"\b(free throw percentage|ft%)\b", "free throw percentage"),
    (r"\bdunks?\b", "dunks"),
    (r"\b(points?|scoring|ppg)\b", "points"),
    (r"\b(rebounds?|boards?|rpg)\b", "rebounds"),
    (r"\b(assists?|dimes?|apg)\b", "assists"),
    (r"\b(steals?|spg)\b", "steals"),
    (r"\b(blocks?|bpg)\b", "blocks"),
    (r"\b(turnovers?|tpg)\b", "turnovers"),
]


def _infer_stat_from_text(params: dict, query_text: str) -> dict:

    if params.get("stat") or not query_text:

        return params

    # ----------------------------------------------------
    # Acronyms are checked CASE-SENSITIVE on the raw text
    # so 'PER' never collides with 'per 36'/'per game'.
    # ----------------------------------------------------
    for pattern, value in (
        (r"(?<![A-Za-z])PER(?![A-Za-z])", "player efficiency rating"),
        (r"(?<![A-Za-z])VORP(?![A-Za-z])", "value over replacement player"),
        (r"(?<![A-Za-z])BPM(?![A-Za-z])", "box plus/minus"),
        (r"(?<![A-Za-z])OBPM(?![A-Za-z])", "offensive box plus/minus"),
        (r"(?<![A-Za-z])DBPM(?![A-Za-z])", "defensive box plus/minus"),
        (r"(?<![A-Za-z])WS(?![A-Za-z])", "win shares"),
        (r"\bUSG%\b", "usage percentage"),
        (r"\bTS%\b", "true shooting percentage"),
        (r"\beFG%\b|\bEFG%\b", "effective field goal percentage"),
    ):

        if re.search(pattern, query_text):
            params["stat"] = value

            return params

    q = query_text.casefold()

    for pattern, value in STAT_INFERENCES:

        if re.search(pattern, q):
            params["stat"] = value

            break

    return params


def _has(text: str, words) -> bool:
    t = f" {text.casefold()} "
    return any(w in t for w in words)


def _count_entities(params: dict) -> tuple[int, int]:
    players = params.get("player") or []

    if isinstance(players, str):
        players = [players] if players else []

    teams = params.get("team") or []

    if isinstance(teams, str):
        teams = [teams] if teams else []

    return len(players), len(teams)


def _normalise_params(params: dict) -> dict:
    """
    Consolidated intents collect both entities into ONE list
    parameter (e.g. {'team': ['Bulls', 'Lakers']}). The engine
    expects 'team'/'team2', so split lists of length >= 2 here.
    """
    out = dict(params)

    for key, first_key, second_key in (
        ("player", "player1", "player2"),
        ("team", "team1", "team2"),
    ):

        value = out.get(key)

        if isinstance(value, list) and len(value) >= 2:
            out[first_key] = value[0]
            out[second_key] = value[1]

            if len(value) > 2:

                logging.warning(
                    "More than 2 %s entities received; "
                    "using the first two.",
                    key,
                )

            out[key] = value[0]

        elif isinstance(value, str) and not out.get(first_key):

            # Single-entity queries: expose the alias the
            # comparison handlers read from, just in case.

            out[first_key] = value

    return out


def resolve_intent(intent: str, params: dict, query_text: str) -> str:
    """Map a consolidated Dialogflow intent to an engine intent."""
    q = query_text or ""

    n_players, n_teams = _count_entities(params)
    has_season = bool(params.get("season"))

    if intent == "player_info":

        if _has(q, HONOR_WORDS):
            return "end_of_season_team"

        if _has(q, ALL_STAR_WORDS):
            return "all_star_selection"

        if _has(q, AWARD_WORDS):
            return "player_awards"

        if _has(q, DRAFT_WORDS):
            return "draft_information"

        cf = q.casefold()

        if "career" in cf and _has(q, STAT_NOUNS):
            return "player_career_totals"

        if _has(q, CAREER_TOTAL_WORDS):
            return "player_career_totals"

        # Stat-style questions trained into player_info,
        # e.g. "Show me Kawhi Leonard's numbers in 2017".

        if has_season and (
            params.get("stat")
            or _has(
                q,
                (
                    "stats",
                    "statistics",
                    "numbers",
                    "averages",
                    "averaged",
                    "per game",
                    "line",
                ),
            )
        ):
            return "player_season_stats"

        return "player_information"

    if intent == "player_stats":

        cf2 = q.casefold()

        if "career" in cf2 and _has(q, STAT_NOUNS):
            return "player_career_totals"
        if (
            "/36" in q
            or "per 36" in q.casefold()
            or "per-minute" in q.casefold()
            or "per minute" in q.casefold()
        ):
            return "player_per_36_stats"
        if (
            "/100" in q
            or "per 100" in q.casefold()
            or "per-possession" in q.casefold()
            or "per possession" in q.casefold()
        ):
            return "player_per_100_stats"

        if _has(q, PBP_WORDS):
            return "player_play_by_play_stats"
        if _has(q, SHOOTING_WORDS):
            return "player_shooting_stats"
        if _has(q, ADVANCED_WORDS):
            return "player_advanced_stats"
        if _has(q, CAREER_TOTAL_WORDS):
            return "player_career_totals"

        return "player_season_stats"

    if intent == "team_info":

        if _has(q, OPPONENT_WORDS):
            return "team_opponent_stats"
        if _has(q, SUMMARY_WORDS) or has_season:
            return "team_summary"

        return "team_information"

    if intent == "team_stats":

        if n_teams >= 2 or _has(q, (" vs ", " versus ", "compared to")):
            return "compare_teams"

        return "team_season_stats"

    if intent == "compare":

        if n_players >= 2:
            return "compare_players"
        if n_teams >= 2:
            return "compare_teams"

        # Fall back to free-text heuristics.
        if re.search(r"\band\b", q.casefold()) and n_players == 1:
            return "compare_players"
        if n_players == 1 and n_teams == 0 and not has_season:
            return "compare_players"

        return "compare_teams"

    if intent == "all_star":

        if _has(q, HONOR_WORDS):
            return "end_of_season_team"
        return "all_star_selection"

    if intent == "draft_info":
        return "draft_information"
    if intent == "league_info":
        return "league_information"
    if intent == "dataset_scope":
        return "dataset_scope"
    if intent == "greeting":
        return "greeting"
    if intent == "goodbye":
        return "goodbye"

    # Unknown name (e.g. Default Fallback): let the engine
    # report it gracefully.
    return intent


# ------------------------------------------------------------
# RESPONSE BUILDING
# ------------------------------------------------------------

# ------------------------------------------------------------
# CHIP PHRASE RULES
#
# Suggestion buttons send templated sentences ('All stats of
# X in Y'). Classifiers sometimes misread these, so route the
# known templates deterministically.
# ------------------------------------------------------------

CHIP_PATTERNS = (
    (
        re.compile(r"^all stats of\b|^full stats of\b", re.IGNORECASE),
        "player_stats",
    ),
    (re.compile(r"^career totals of\b", re.IGNORECASE), "player_info"),
    (re.compile(r"^awards (of|won by)\b", re.IGNORECASE), "player_info"),
    (re.compile(r"^draft info of\b", re.IGNORECASE), "draft_info"),
    (re.compile(r"latest season record$", re.IGNORECASE), "team_stats"),
    (re.compile(r"^opponent stats of\b", re.IGNORECASE), "team_info"),
    (re.compile(r"stats that season$", re.IGNORECASE), "team_stats"),
    (
        re.compile(r"^(player stats|team stats|awards)$", re.IGNORECASE),
        "dataset_scope",
    ),
    (
        re.compile(r"^what statistics can you provide\?$", re.IGNORECASE),
        "dataset_scope",
    ),
)


# Phrasings the offline classifier gets wrong; route them
# before any NLU runs.
OVERRIDE_PATTERNS = (
    (
        re.compile(
            r"injury\s+replacements?\b|\bwho\s+replaced\b", re.IGNORECASE
        ),
        "all_star",
    ),
)


def chip_intent(text: str) -> str | None:

    if not text:
        return None

    for pattern, intent in CHIP_PATTERNS:

        if pattern.search(text.strip()):

            return intent

    return None


# Season-aware team templates ('Bulls stats in 1996',
# 'Opponent stats of Boston Celtics in 2008'). Only forced
# when entity extraction actually finds a TEAM, so player
# sentences like 'Curry stats in 2016' stay with the NLU.

CHIP_SEASON_RULES = (
    (
        re.compile(
            r"^(?P<who>.+?)\s+stats\s+in\s+(?P<season>\d{4})$", re.IGNORECASE
        ),
        "team_stats",
    ),
    (
        re.compile(
            r"^opponent\s+stats\s+of\s+(?P<who>.+?)"
            r"(?:\s+in\s+(?P<season>\d{4}))?$",
            re.IGNORECASE,
        ),
        "team_info",
    ),
)


def chip_rule(text: str) -> tuple[str, dict] | None:
    """
    Deterministic routing for suggestion-chip templates.
    Returns (intent, extra_params) or None.
    """

    t = (text or "").strip()

    if not t:
        return None

    for pattern, intent in CHIP_SEASON_RULES:

        match = pattern.search(t)

        if not match:
            continue

        found = extract_entities(t)
        teams = found.get("team") or []

        if isinstance(teams, str):
            teams = [teams]

        if not teams:
            break

        params: dict = {}
        season = match.groupdict().get("season")

        if season:
            params["season"] = season

        return intent, params

    for pattern, intent in CHIP_PATTERNS:
        if pattern.search(t):

            return intent, {}

    return None


@app.get("/")
def health() -> tuple:
    return jsonify({"status": "ok", "service": "HoopMind webhook"})


# ------------------------------------------------------------
# STREAMLIT CHAT ENDPOINT
#
# Streamlit POSTs {'message': str, 'session_id': str} here.
# Intent + entities come from Dialogflow ES (or the local
# fallback classifier), then flow through process_message.
# Response is structured JSON: {intent, text, rich, source}
# ------------------------------------------------------------


def process_message(
    raw_intent: str, params_in: dict, query_text: str, source: str = "test"
) -> dict:
    """
    Shared pipeline: entity recovery -> intent fan-out ->
    query engine -> card generation.

    Used by the /chat endpoint and by regression suites.
    """

    params = params_in or {}

    # ----------------------------------------------------
    # The agent's training phrases are not entity
    # annotated, so parameters are often EMPTY. Recover
    # players/teams/seasons from the raw question BEFORE
    # resolving sub-shapes so 'compare' can see two
    # entities. Dialogflow values always win.
    # ----------------------------------------------------

    if raw_intent in {
        "player_info",
        "player_stats",
        "team_info",
        "team_stats",
        "compare",
        "all_star",
        "draft_info",
        "league_info",
    }:

        found = extract_entities(query_text)

        for key, value in found.items():

            existing = params.get(key)

            is_empty = not existing or existing == [] or existing == ""

            if is_empty:

                params[key] = value

    intent = resolve_intent(raw_intent or "greeting", params, query_text)

    # ----------------------------------------------------
    # Local-classifier safety net: entity evidence beats
    # a wrong label. A detected PLAYER must never land in
    # a team handler (and vice versa).
    # ----------------------------------------------------

    if source == "local-classifier":

        if (
            params.get("player")
            and not params.get("team")
            and intent.startswith("team_")
        ):

            intent = {
                "team_information": "player_information",
                "team_summary": "player_season_stats",
                "team_opponent_stats": "player_season_stats",
                "team_season_stats": "player_season_stats",
            }.get(intent, intent)

        elif (
            params.get("team")
            and not params.get("player")
            and intent.startswith("player_")
        ):

            intent = {
                "player_information": "team_information",
                "player_career_totals": "team_summary",
                "player_awards": "team_summary",
                "player_season_stats": "team_season_stats",
            }.get(intent, intent)

    params = _normalise_params(params)
    params = _infer_stat_from_text(params, query_text)

    logging.info("[chat] %s -> %s | Params=%s", raw_intent, intent, params)

    result = engine.query(intent, params, query_text)

    if not result.ok:

        return {
            "intent": intent,
            "source": source,
            "rich": None,
            "text": result.error
            or ("I couldn't find that in my NBA dataset."),
        }

    answer_data = result.answer_data or {}

    if getattr(engine, "_fuzzy_note", None):

        answer_data["fuzzy_matched"] = engine._fuzzy_note

    try:

        rich = generate_cards(answer_data, intent, query_text)

        rows = None
        text = None

        for m in rich:

            if "payload" in m:
                rows = m["payload"]["richContent"]

            elif "text" in m:
                text = m["text"]["text"][0]

        return {"intent": intent, "source": source, "rich": rows, "text": text}

    except TypeError:

        logging.exception("Card payload build failed")

        return {
            "intent": intent,
            "source": source,
            "rich": None,
            "text": generate(answer_data, intent, query_text),
        }


@app.post("/chat")
def streamlit_chat():
    try:
        req = request.get_json(silent=False) or {}
        message = str(req.get("message") or "").strip()
        session_id = str(req.get("session_id") or "ui")

        if not message:
            return jsonify({"error": "empty message"}), 400

        from dialogflow_client import detect_via_dialogflow, classify_locally

        # Chip templates bypass NLU entirely.

        ruled = chip_rule(message)

        if not ruled:
            for pattern, forced in OVERRIDE_PATTERNS:
                if pattern.search(message):
                    ruled = ("all_star", {})

                    break

        source = "dialogflow"
        raw_intent = ""
        params: dict = {}

        query_text = message

        detected = (
            None if ruled else detect_via_dialogflow(message, session_id)
        )

        if ruled:
            raw_intent, extra_params = ruled
            params.update(extra_params or {})
            source = "chip-rule"

        elif detected:
            raw_intent, params, query_text = detected

            if raw_intent == "Default Fallback Intent":

                local = classify_locally(message)

                if local:
                    raw_intent, params = local, {}

                    source = "local-classifier"
                else:
                    raw_intent = ""

        else:
            local = classify_locally(message)
            source = "local-classifier"

            if local:
                raw_intent, params = local, {}
            else:

                raw_intent = ""

        params = params or {}

        # ---- shared pipeline (also used by tests) ----

        return jsonify(
            process_message(raw_intent, params, message, source=source)
        )

    except Exception:

        logging.exception("[chat] error")

        return (
            jsonify(
                {
                    "intent": None,
                    "source": "error",
                    "rich": None,
                    "text": "Sorry, I couldn't process that "
                    "request right now.",
                }
            ),
            200,
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)