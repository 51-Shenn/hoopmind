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
    "awards",
    "mvp",
    "most valuable player",
    "most valuable",
    "roy",
    "rookie of the year",
    "dpoy",
    "defensive player of the year",
    "defensive player",
    "sixth man",
    "sixth man of the year",
    "mip",
    "most improved",
    "most improved player",
    "scoring title",
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
    "efg%",
    "effective",
)

ADVANCED_STATS = frozenset({
    "player efficiency rating",
    "true shooting percentage",
    "usage percentage",
    "win shares",
    "value over replacement player",
    "box plus/minus",
    "offensive rating",
    "defensive rating",
})

SHOOTING_WORDS = (
    "shoot",
    "shooting",
    "shot",
    "fg%",
    "field goal",
    "3p%",
    "three point",
    "3 point",
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

    # Foul-related play-by-play statistics
    "shooting foul",
    "shooting fouls",
    "offensive foul",
    "offensive fouls",
    "foul drawn",
    "fouls drawn",
    "foul committed",
    "fouls committed",
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
        r"\b(3[\s-]?point\s+percentage|three[\s-]?point\s+percentage|"
        r"three point shooting)\b|(?<![a-z])3p%(?![a-z])",
        "three-point percentage",
    ),
    (
        r"\b(field goal percentage|shooting percentage)\b|(?<![a-z])fg%(?![a-z])",
        "field goal percentage",
    ),
    (
        r"\b(free throw percentage)\b|(?<![a-z])ft%(?![a-z])",
        "free throw percentage",
    ),
    (r"\b(three.?pointers?|3p|threes|triple)\b", "three-pointers"),
    (r"\b(free throws?|ft)\b", "free throws"),
    (r"\bdunks?\b", "dunks"),
    (r"\b(points?|scoring|ppg)\b", "points"),
    (r"\b(rebounds?|boards?|rpg)\b", "rebounds"),
    (r"\b(assists?|dimes?|apg)\b", "assists"),
    (r"\b(steals?|spg)\b", "steals"),
    (r"\b(blocks?|bpg)\b", "blocks"),
    (r"\b(turnovers?|tpg)\b", "turnovers"),
    (r"\b(fouls?|personal fouls?)\b", "personal fouls"),
    (r"\b(minutes?|mpg|min)\b", "minutes"),
    (r"\b(fg|field goals?)\b", "field goals"),
    (r"\b(fga|field goal attempts?)\b", "field goal attempts"),
    (r"\b(free throw attempts?|fta)\b", "free throw attempts"),
    (r"\b(x3pa|three.?point attempts?)\b", "three-point attempts"),
]

STAT_CANONICAL = {v: v for _, v in STAT_INFERENCES}

_STAT_STOPWORDS = frozenset({
    "stats", "stat", "statistics", "number", "numbers",
    "show", "get", "give", "what", "were", "are", "was",
    "how", "the", "for", "in", "of", "and", "by", "all",
    "his", "her", "per", "season", "total", "totals",
    "career", "play", "game", "games", "year", "years",
})

def _fuzzy_stat(q: str) -> str | None:
    from difflib import get_close_matches
    tokens = [t for t in q.split() if t not in _STAT_STOPWORDS]
    for n in range(1, min(len(tokens) + 1, 4)):
        for i in range(len(tokens) - n + 1):
            chunk = " ".join(tokens[i : i + n])
            matches = get_close_matches(
                chunk, list(STAT_CANONICAL), n=1, cutoff=0.65,
            )
            if matches:
                return STAT_CANONICAL[matches[0]]
    return None


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

    if not params.get("stat"):
        from query_engine import NBAQueryEngine
        qe = NBAQueryEngine()
        for key in sorted(qe.STAT_SYNONYMS, key=len, reverse=True):
            if re.search(
                r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])",
                q,
            ):
                params["stat"] = qe.STAT_SYNONYMS[key]
                break

    if not params.get("stat"):
        fuzzy = _fuzzy_stat(q)
        if fuzzy:
            params["stat"] = fuzzy

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

    n_players, n_teams = len(players), len(teams)

    # If both halves of a pair are present, that's 2 entities
    # regardless of what 'player' / 'team' collapsed to.
    if params.get("player1") and params.get("player2"):
        n_players = max(n_players, 2)
    if params.get("team1") and params.get("team2"):
        n_teams = max(n_teams, 2)

    return n_players, n_teams


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

        elif isinstance(value, list) and len(value) == 1 and not out.get(first_key):
            """
            Exactly one entity recognised (e.g. {'team': ['Los Angeles Lakers']} 
            for "Compare the Lakers and someone else").
            # Without this, first_key never gets set and the query
            # engine's compare_* guards see it as "nothing found"
            # even though one half is known.
            """
            out[first_key] = value[0]
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

    is_comparison = intent == "compare" or n_players >= 2 or n_teams >= 2

    if _has(q, AWARD_WORDS) and not is_comparison:
        return "player_awards"
    
    if intent == "player_info":

        if _has(q, HONOR_WORDS):
            return "end_of_season_team"

        if _has(q, ALL_STAR_WORDS):
            return "all_star_selection"

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

    if intent == "award_winner":
            return "award_winner"

    if intent == "player_awards":
            return "player_awards"
    
    if intent == "player_stats":

        cf2 = q.casefold()

        if "career" in cf2 and _has(q, STAT_NOUNS):
            return "player_career_totals"
        # PER-36 MINUTES
        if (
            "/36" in cf2
            or "per 36" in cf2
            or "per-minute" in cf2
            or "per minute" in cf2
            or re.search(
                r"\b(?:per|every)\s+(?:36|thirty[- ]six)\s+minutes?\b",
                cf2,
            )
        ):
            return "player_per_36_stats"
        # PER-100 POSSESSIONS
        if (
            "/100" in cf2
            or "per 100" in cf2
            or "per 100 possession" in cf2
            or "per hundred" in cf2
            or "per one hundred" in cf2
            or "per-possession" in cf2
            or "per possession" in cf2
            or re.search(
                r"\bper\s+(?:100|hundred|one\s+hundred)\s+possessions?\b",
                cf2,
            )
        ):
            return "player_per_100_stats"
        # PLAY-BY-PLAY
        if _has(q, PBP_WORDS):
            return "player_play_by_play_stats"
        # ADVANCED STATS
        if params.get("stat") in ADVANCED_STATS:
            return "player_advanced_stats"
        if _has(q, ADVANCED_WORDS):
            return "player_advanced_stats"
        # SHOOTING
        if _has(q, SHOOTING_WORDS) and "total" not in q:
            return "player_shooting_stats"
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
        # Mirror of the check above: one recognised team and no
        # player should route the same way.
        if n_teams == 1 and n_players == 0:
            return "compare_teams"

        # No named player/team at all - use the word itself to
        # decide which comparison the chips should offer, instead
        # of always silently defaulting to teams.
        ql = q.casefold()
        mentions_player = bool(re.search(r"\bplayers?\b", ql))
        mentions_team = bool(re.search(r"\bteams?\b", ql))
        if mentions_player and not mentions_team:
            return "compare_players"
        if mentions_team and not mentions_player:
            return "compare_teams"

        # Still ambiguous - default to player-vs-player.
        return "compare_players"


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
    (re.compile(r"^awards (of|won by)\b", re.IGNORECASE), "player_awards"),
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
# Each tuple is (regex, forced_intent). Use these to short-circuit
# misclassifications where the wording is unambiguous even without
# named entities.
OVERRIDE_PATTERNS = (
    (
        re.compile(
            r"injury\s+replacements?\b|\bwho\s+replaced\b", re.IGNORECASE
        ),
        "all_star",
    ),
    # --- PLAYER / TEAM COMPARES without named entities ---
    (
        re.compile(
            r"\b(better|best)\s+(between|among)\b|\bcompare\s+(two|both)\b|"
            r"\b(who|which)\s+(player|team)?\s*"
            r"(?:had|has|was|is|won|averaged|scored|recorded|holds|has)\s+"
            r"(more|less|most|least|better|worse|higher|lower|scored|"
            r"averaged|stronger|weaker|faster|slower|older|younger|taller|"
            r"shorter|fewer|greatest)",
            re.IGNORECASE,
        ),
        "compare",
    ),
    (
        re.compile(
            r"\b(who|which)\s+(player|team)\s+(is|was|had|has|won)\s+"
            r"(better|worse|best|worst|stronger|weaker|greater|good|bad|"
            r"superior|inferior|more successful|less successful|more titles|"
            r"more championships|more rings|more awards|more mvps|more trophies)",
            re.IGNORECASE,
        ),
        "compare",
    ),
    (
        re.compile(
            r"\b(which|what)\s+(team|player)\s+(had|has|was|is|won)\s+the\s+"
            r"(better|best|worse|worst|most|least|highest|lowest|top)\b",
            re.IGNORECASE,
        ),
        "compare",
    ),
    (
        re.compile(
            r"\bvs\b|\bversus\b|(\bplayer1\b|\bplayer2\b|\bteam1\b|\bteam2\b)",
            re.IGNORECASE,
        ),
        "compare",
    ),
    (
        re.compile(
            r"more\s+(mvp|mvps|award|awards|troph?ies?|championships?|rings?|"
            r"roty|dpoy|roy|mip|smoy|sixth man)\b|"
            r"most\s+(mvp|mvps|award|awards|troph?ies?|championships?|rings?)\b",
            re.IGNORECASE,
        ),
        "compare",
    ),
    # --- TEAM SEASON STATS / stat questions without a team name ---
    # "What was the team's scoring average?" / "team average rebounds"
    # / "how many games did the team play that season"
    (
        re.compile(
            r"(?:^|\W)the\s+team(?:'s)?\s+(?:scoring|average|stat|stats|"
            r"averaged|record|defense|offense|turnovers?|rebounds?|points?|"
            r"assists?|blocks?|steals?|fg%|3p%|ft%|games\s+played|win\s+loss|"
            r"wins?|losses?|pace|rating|differential|play\s+that\s+season|"
            r"play\s+in\s+(?:19|20)\d{2})\b|"
            r"\bteam(?:'s)?\s+(?:average|averaged|scoring|per\s+game|"
            r"stats?|record|how\s+many\s+games)\b",
            re.IGNORECASE,
        ),
        "team_stats",
    ),
    # --- PLAYER SEASON STATS without named player ---
    # "How many points did the player average?"
    (
        re.compile(
            r"(?:^|\W)the\s+player(?:'s)?\s+(?:scoring|average|stat|stats|"
            r"averaged|points?|rebounds?|assists?|blocks?|steals?|"
            r"games\s+played|per\s+game|turnovers?|play\s+that\s+season|"
            r"play\s+in\s+(?:19|20)\d{2})\b|"
            r"\bplayer(?:'s)?\s+(?:average|averaged|scoring|per\s+game|"
            r"stats?|how\s+many\s+games)\b",
            re.IGNORECASE,
        ),
        "player_stats",
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


def _missing_entity_chips(
    missing: str,
    have: list[str] | None = None,
    *,
    intent_name: str | None = None,
    stat: str | None = None,
    season: str | None = None,
) -> list[str]:
    """
    Build clickable suggestion-chip labels that fill in the entities
    the user forgot to name. Random players / teams / seasons are drawn
    from the live dataset.

    Parameters
    ----------
    missing : str
        The missing-entity key from query_engine guards:
        ``player | team | player_pair | team_pair | season``.
    have : list[str] | None
        Entities the user *did* name (e.g. one player when
        ``missing == "player_pair"``).  Preserved in the first chips.
    intent_name : str | None
        The *resolved* engine-level intent (e.g. ``team_season_stats``,
        ``compare_players``).  Used to shape chips so they match the
        question the user actually asked.
    stat : str | None
        Canonical stat name already extracted from the question
        (e.g. ``"rebounds"``, ``"turnovers"``, ``"points"``).
        If present, it is *locked in* — chips will use the exact
        same stat instead of a random one.
    season : str | None
        Season already extracted (e.g. ``"2022"``).  If present,
        chips reuse that season rather than picking a random one.

    Returns
    -------
    list[str]
        Exactly 4 chip label strings.  Each label, when clicked,
        produces a full question that the engine can answer
        directly — i.e. it has no further missing entities.
    """
    from response_generator import (
        _random_player,
        _random_team,
        _available_seasons,
    )
    import random as _rnd

    have = have or []
    have_strs = [str(x) for x in have if x]
    labels: list[str] = []
    seasons = _available_seasons()

    def _pick_season() -> str:
        return season or (_rnd.choice(seasons) if seasons else "2023")

    def _four(lst: list[str]) -> list[str]:
        out = [l for l in lst if l]
        return out[:4]

    # ---------------------------------------------------------------
    # player / team STAT CHIPS — intent-aware shape
    # ---------------------------------------------------------------
    STAT_SHAPES_PLAYER = {
        "player_season_stats", "player_advanced_stats",
        "player_per_36_stats", "player_per_100_stats",
        "player_shooting_stats", "player_play_by_play_stats",
    }
    STAT_SHAPES_TEAM = {
        "team_season_stats", "team_summary", "team_opponent_stats",
    }

    # ---------------------------------------------------------------
    # 1) Single PLAYER missing
    # ---------------------------------------------------------------
    if missing == "player":
        s = _pick_season()
        p1 = _random_player()
        p2 = _random_player(exclude=p1)
        p3 = _random_player(exclude=p1)
        p4 = _random_player(exclude=p1)

        if intent_name in STAT_SHAPES_PLAYER or intent_name == "player_stats":
            # Lock the stat in if user already asked for one.
            locked = stat
            if locked:
                labels.append(f"{p1} {locked} in {s}")
                labels.append(f"{p2} {locked} in {s}")
                labels.append(f"{p3} averaged {locked} in {s}")
                labels.append(f"Full stats of {p4} in {s}")
            else:
                labels.append(f"{p1} stats in {s}")
                labels.append(f"{p2} points in {s}")
                labels.append(f"{p3} PER in {s}")
                labels.append(f"{p4} rebounds in {s}")
        elif intent_name == "player_awards":
            labels.append(f"Awards won by {p1}")
            labels.append(f"Awards won by {p2}")
            labels.append(f"Did {p3} win MVP?")
            labels.append(f"All-Star selections of {p4}")
        elif intent_name == "all_star_selection":
            labels.append(f"Was {p1} an All-Star in {s}?")
            labels.append(f"Was {p2} an All-Star in {s}?")
            labels.append(f"All-Star team of {p3} in {s}")
            labels.append(f"{p4} All-Star {s}")
        elif intent_name == "draft_information":
            labels.append(f"Where was {p1} drafted?")
            labels.append(f"Draft position of {p2}")
            labels.append(f"Draft info of {p3}")
            labels.append(f"What pick was {p4}?")
        elif intent_name == "end_of_season_team":
            labels.append(f"All-NBA team for {p1} in {s}")
            labels.append(f"{p2} All-Defense {s}")
            labels.append(f"End-of-season honors {p3} {s}")
            labels.append(f"Was {p4} on an All-NBA team in {s}?")
        else:
            # Default / player_information shape
            labels.append(f"Tell me about {p1}")
            labels.append(f"Player profile of {p2}")
            labels.append(f"Career totals of {p3}")
            labels.append(f"Where did {p4} go to college?")

    # ---------------------------------------------------------------
    # 2) Single TEAM missing
    # ---------------------------------------------------------------
    elif missing == "team":
        s = _pick_season()
        t1 = _random_team()
        t2 = _random_team(exclude=t1)
        t3 = _random_team(exclude=t1)
        t4 = _random_team(exclude=t1)

        if intent_name in STAT_SHAPES_TEAM or intent_name == "team_stats":
            locked = stat
            if intent_name == "team_opponent_stats":
                prefix = "Opponent stats of"
            elif intent_name == "team_summary":
                prefix = "Season summary for"
            else:
                prefix = "Team stats of"

            if locked:
                labels.append(f"{prefix} {t1} in {s} ({locked})")
                labels.append(f"{prefix} {t2} in {s} ({locked})")
                labels.append(f"{t3} average {locked} in {s}")
                labels.append(f"{t4} team {locked} in {s}")
            else:
                labels.append(f"{prefix} {t1} in {s}")
                labels.append(f"{prefix} {t2} in {s}")
                labels.append(f"{t3} record in {s}")
                labels.append(f"{t4} stats that season in {s}")
        else:
            # team_information / generic
            labels.append(f"Tell me about the {t1}")
            labels.append(f"{t2} record in {s}")
            labels.append(f"Team stats of {t3} in {s}")
            labels.append(f"Opponent stats of {t4} in {s}")

    # ---------------------------------------------------------------
    # 3) PLAYER PAIR missing (0 or 1 players given) → compare_players
    # ---------------------------------------------------------------
    elif missing == "player_pair":
        s = _pick_season()
        locked = stat
        p_existing = have_strs[0] if have_strs else None

        p1a = p_existing or _random_player()
        p1b = _random_player(exclude=p1a)
        p2a = _random_player(exclude=p1a)
        p2b = _random_player(exclude=p2a)
        p3a = p_existing or _random_player()
        p3b = _random_player(exclude=p3a)
        p4a = _random_player()
        p4b = _random_player(exclude=p4a)

        if locked:
            labels.append(f"Compare {p1a} and {p1b} {locked}")
            if season:
                labels.append(f"Compare {p2a} and {p2b} {locked} in {s}")
                labels.append(f"Who had more {locked}, {p3a} or {p3b} in {s}?")
                labels.append(f"{p4a} vs {p4b} {locked} in {s}")
            else:
                labels.append(f"{p2a} vs {p2b} career {locked}")
                labels.append(f"Who had more {locked}, {p3a} or {p3b}?")
                labels.append(f"{p4a} vs {p4b} {locked}")
        elif season:
            labels.append(f"Compare {p1a} and {p1b} in {s}")
            labels.append(f"{p2a} vs {p2b} in {s}")
            labels.append(f"Who was better, {p3a} or {p3b} in {s}?")
            labels.append(f"Compare {p4a} and {p4b} stats in {s}")
        else:
            labels.append(f"Compare {p1a} and {p1b}")
            labels.append(f"Compare {p2a} and {p2b} career points")
            labels.append(f"{p3a} vs {p3b} — who is better?")
            labels.append(f"{p4a} vs {p4b} scoring titles")

    # ---------------------------------------------------------------
    # 4) TEAM PAIR missing (0 or 1 teams given) → compare_teams
    # ---------------------------------------------------------------
    elif missing == "team_pair":
        s = _pick_season()
        locked = stat
        t_existing = have_strs[0] if have_strs else None

        t1a = t_existing or _random_team()
        t1b = _random_team(exclude=t1a)
        t2a = _random_team(exclude=t1a)
        t2b = _random_team(exclude=t2a)
        t3a = t_existing or _random_team()
        t3b = _random_team(exclude=t3a)
        t4a = _random_team()
        t4b = _random_team(exclude=t4a)

        if locked:
            if season:
                labels.append(f"Compare {t1a} and {t1b} {locked} in {s}")
                labels.append(f"Which team had more {locked}, {t2a} or {t2b} in {s}?")
                labels.append(f"{t3a} vs {t3b} {locked} in {s}")
                labels.append(f"{t4a} or {t4b} — better {locked} in {s}?")
            else:
                labels.append(f"Compare {t1a} and {t1b} {locked}")
                labels.append(f"Which team had more {locked}, {t2a} or {t2b}?")
                labels.append(f"{t3a} vs {t3b} {locked}")
                labels.append(f"{t4a} or {t4b} — better {locked}?")
        elif season:
            labels.append(f"Compare {t1a} and {t1b} in {s}")
            labels.append(f"{t2a} vs {t2b} in {s}")
            labels.append(f"Which team was better, {t3a} or {t3b} in {s}?")
            labels.append(f"Compare {t4a} and {t4b} record in {s}")
        else:
            labels.append(f"Compare {t1a} and {t1b}")
            labels.append(f"Compare {t2a} and {t2b} best seasons")
            labels.append(f"{t3a} vs {t3b} — which franchise is better?")
            labels.append(f"{t4a} or {t4b} — titles comparison")

    # ---------------------------------------------------------------
    # 5) SEASON missing → attach season to known entities
    # ---------------------------------------------------------------
    elif missing == "season":
        s1 = _rnd.choice(seasons) if seasons else "2016"
        s2 = _rnd.choice(seasons) if seasons else "2020"
        s3 = _rnd.choice(seasons) if seasons else "2010"
        s4 = _rnd.choice(seasons) if seasons else "2023"

        who = have_strs[0] if have_strs else None
        locked = stat

        if who and intent_name in STAT_SHAPES_PLAYER:
            suffix = f" {locked}" if locked else " stats"
            labels.append(f"{who}{suffix} in {s1}")
            labels.append(f"{who}{suffix} in {s2}")
            labels.append(f"{who}{suffix} in {s3}")
            labels.append(f"{who}{suffix} in {s4}")
        elif who and intent_name in STAT_SHAPES_TEAM:
            suffix = f" {locked}" if locked else " stats"
            labels.append(f"{who}{suffix} in {s1}")
            labels.append(f"{who} record in {s2}")
            labels.append(f"{who} summary {s3}")
            labels.append(f"Opponent stats of {who} in {s4}")
        elif locked:
            p = _random_player()
            t = _random_team()
            labels.append(f"{p} {locked} in {s1}")
            labels.append(f"{t} {locked} in {s2}")
            labels.append(f"League leader in {locked} {s3}")
            labels.append(f"Award for {locked} in {s4}")
        elif intent_name == "draft_information":
            p = _random_player()
            labels.append(f"Draft information in {s1}")
            labels.append(f"Draft information in {s2}")
            labels.append(f"Draft information in {s3}")
            labels.append(f"Draft information in {s4}")
        else:
            p = _random_player()
            t = _random_team()
            labels.append(f"{p} stats in {s1}")
            labels.append(f"{t} record in {s2}")
            labels.append(f"NBA MVP winner in {s3}")
            labels.append(f"Draft class of {s4}")

    return _four(labels)


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
    # HEURISTIC OVERRIDE: when the offline classifier (or
    # even Dialogflow!) misroutes a structurally obvious
    # question — e.g. "better between two players" →
    # draft_info — force the correct consolidated intent
    # BEFORE entity extraction.  These patterns are the
    # same ones used at the /chat endpoint.
    # ----------------------------------------------------
    _forced = None
    if query_text:
        for pattern, forced_intent in OVERRIDE_PATTERNS:
            if pattern.search(query_text):
                _forced = forced_intent
                break
    if _forced and raw_intent != _forced:
        logging.info(
            "[chat] heuristic override: %s -> %s (q=%s)",
            raw_intent or "(none)", _forced, query_text[:60],
        )
        raw_intent = _forced

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
        "award_winner",
        "player_awards"
    }:

        found = extract_entities(query_text)

        for key, value in found.items():
            existing = params.get(key)
            is_empty = not existing or existing == [] or existing == ""

            existing_count = len(existing) if isinstance(existing, list) else (1 if existing else 0)
            found_count = len(value) if isinstance(value, list) else (1 if value else 0)
            is_partial = key in ("player", "team") and found_count > existing_count

            if is_empty or is_partial:
                params[key] = value

    if not raw_intent:
        from response_generator import _chips, _random_player, _random_team, _available_seasons
        import random as _rnd
        p1 = _random_player()
        p2 = _random_player(exclude=p1)
        t1 = _random_team()
        season = _rnd.choice(_available_seasons())
        fallback_chips = _chips([
            f"Tell me about {p1}",
            f"{p2} stats in {season}",
            f"{t1} record in {season}",
            f"Compare {p1} and {p2}",
        ])
        return {
            "intent": "fallback",
            "source": source,
            "rich": [[fallback_chips]] if fallback_chips else None,
            "text": (
                "Sorry, I can only answer NBA-related questions "
                "about players, teams, stats, awards, All-Stars, "
                "and drafts. Try one of these:"
            ),
        }

    params = _normalise_params(params)
    params = _infer_stat_from_text(params, query_text)

    intent = resolve_intent(raw_intent, params, query_text)

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

    # Attribute-based intent override: if the user is clearly
    # asking about a player attribute (height, position, etc.),
    # force the intent to the correct handler.
    _player_attrs = {
        "height", "position", "weight", "born",
        "college", "hall_of_fame",
    }
    if params.get("attribute") in _player_attrs and not intent.startswith("player_"):
        intent = "player_information"
    if params.get("attribute") == "career" and not intent.startswith("compare"):
        intent = "player_career_totals"

    logging.info("[chat] %s -> %s | Params=%s", raw_intent, intent, params)

    result = engine.query(intent, params, query_text)

    if not result.ok:
        missing = (result.answer_data or {}).get("missing")
        error_text = result.error or "I couldn't find that in my NBA dataset."
        rich = None

        if missing:
            GENERIC_MARKERS = (
                "I couldn't find that player",
                "I couldn't find that team",
                "I couldn't find that in my NBA",
            )
            _engine_said_generic = any(
                m in error_text for m in GENERIC_MARKERS
            )

            _prompts = {
                "player": (
                    "Please name the NBA player you'd like to know about "
                    "— for example 'Tell me about Stephen Curry'."
                ),
                "team": (
                    "Please tell me which NBA team you're asking about "
                    "— for example 'Team stats of the Boston Celtics in 2008'."
                ),
                "season": (
                    "Please specify a season year — for example 'Lakers stats "
                    "in 2010'."
                ),
            }
            if _engine_said_generic and missing in _prompts:
                error_text = _prompts[missing]

            CHIP_MISSING_INTENTS = {
                "player_information",
                "player_career_totals",
                "player_season_stats",
                "player_advanced_stats",
                "player_per_36_stats",
                "player_per_100_stats",
                "player_shooting_stats",
                "player_play_by_play_stats",
                "team_information",
                "team_summary",
                "team_opponent_stats",
                "team_season_stats",
                "compare_players",
                "compare_teams",
                "all_star_selection",
                "end_of_season_team",
                "draft_information",
            }
            _missing_allows_chips = intent in CHIP_MISSING_INTENTS or missing in (
                "player_pair",
                "team_pair",
            )

            if _missing_allows_chips:
                from response_generator import _chips
                labels = _missing_entity_chips(
                    missing,
                    (result.answer_data or {}).get("have"),
                    intent_name=intent,
                    stat=params.get("stat"),
                    season=params.get("season"),
                )
                chips = _chips(labels)
                if chips:
                    rich = [[chips]]
                    error_text = error_text + "\n\nOr tap one of these:"

        return {
            "intent": intent,
            "source": source,
            "rich": rich,
            "text": error_text,
        }

    answer_data = result.answer_data or {}

    if params.get("attribute"):
        answer_data["attribute"] = params["attribute"]

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

        # ------------------------------------------------
        # Chip templates bypass NLU entirely (100% confidence).
        # ------------------------------------------------
        ruled = chip_rule(message)

        if not ruled:
            for pattern, forced in OVERRIDE_PATTERNS:
                if pattern.search(message):
                    ruled = (forced, {})

                    break

        if ruled:
            raw_intent, extra_params = ruled
            params: dict = extra_params or {}
            return jsonify(
                process_message(raw_intent, params, message, source="chip-rule")
            )

        # ------------------------------------------------
        # 1. Try Dialogflow first.
        # ------------------------------------------------
        detected = detect_via_dialogflow(message, session_id)

        if detected:
            raw_intent, df_confidence, params, query_text = detected

            if raw_intent == "Default Fallback Intent":
                df_confidence = 0.0

            logging.info(
                "[chat] dialogflow intent=%s conf=%.2f", raw_intent, df_confidence
            )

            # Dialogflow confidence >= 0.70: accept directly.
            if df_confidence >= 0.70:
                return jsonify(
                    process_message(
                        raw_intent, params or {}, message, source="dialogflow"
                    )
                )

            # Dialogflow 0.40-0.69: try local classifier for a better match.
            if df_confidence >= 0.40:
                local = classify_locally(message)
                if local:
                    local_intent, local_conf = local
                    logging.info(
                        "[chat] local intent=%s conf=%.2f (df=%.2f)",
                        local_intent,
                        local_conf,
                        df_confidence,
                    )
                    if local_conf >= 0.10:
                        return jsonify(
                            process_message(
                                local_intent, {}, message, source="local-classifier"
                            )
                        )
                # Neither source is confident enough: ask clarification.
                return jsonify(
                    {
                        "intent": "clarification",
                        "source": "confidence-check",
                        "rich": None,
                        "text": (
                            "I'm not sure what you're asking. "
                            "Could you rephrase your NBA question?"
                        ),
                    }
                )

            # Dialogflow < 0.40: fall through to local classifier.
            raw_intent = ""

        # ------------------------------------------------
        # 2. Local classifier.
        # ------------------------------------------------
        local = classify_locally(message)
        source = "local-classifier"
        params = {}

        if local:
            raw_intent, local_conf = local

            # Boost: if entity extraction found a valid player/team,
            # accept even at low confidence — the entity is real.
            has_entity_boost = False
            if raw_intent in {
                "player_info", "player_stats", "team_info",
                "team_stats", "compare", "all_star",
            }:
                from entity_extractor import extract
                found = extract(message)
                if found.get("player") or found.get("team"):
                    has_entity_boost = True
                    params.update(found)

            logging.info(
                "[chat] local intent=%s conf=%.2f entity_boost=%s",
                raw_intent, local_conf, has_entity_boost,
            )

            if local_conf >= 0.10 or has_entity_boost:
                pass  # accept

            elif local_conf >= 0.03:
                return jsonify(
                    {
                        "intent": "clarification",
                        "source": "confidence-check",
                        "rich": None,
                        "text": (
                            "I'm not sure what you're asking. "
                            "Could you rephrase your NBA question?"
                        ),
                    }
                )

            else:
                raw_intent = ""
        else:
            raw_intent = ""

        # ------------------------------------------------
        # 3. Low confidence / nothing matched: fallback.
        # ------------------------------------------------
        if not raw_intent:
            from response_generator import _chips, _random_player, _random_team, _available_seasons
            import random as _rnd
            p1 = _random_player()
            p2 = _random_player(exclude=p1)
            t1 = _random_team()
            season = _rnd.choice(_available_seasons())
            fallback_chips = _chips([
                f"Tell me about {p1}",
                f"{p2} stats in {season}",
                f"{t1} record in {season}",
                f"Compare {p1} and {p2}",
            ])
            return jsonify(
                {
                    "intent": "fallback",
                    "source": "no-match",
                    "rich": [[fallback_chips]] if fallback_chips else None,
                    "text": (
                        "Sorry, I can only answer NBA-related questions "
                        "about players, teams, stats, awards, All-Stars, "
                        "and drafts. Try one of these:"
                    ),
                }
            )

        # ------------------------------------------------
        # 4. Process the matched intent + validate entities.
        # ------------------------------------------------
        result = process_message(raw_intent, params or {}, message, source=source)

        # ------------------------------------------------
        # 5. Second layer: entity validation.
        # If the engine returned an error about missing
        # entity, relay it as a clarification.
        # ------------------------------------------------
        if result.get("text") and not result.get("rich"):
            error_text = result["text"]
            missing_keywords = (
                "could not find",
                "couldn't find",
                "not in the",
                "no data",
                "no results",
            )
            if any(kw in error_text.lower() for kw in missing_keywords):
                from response_generator import _chips, _random_player, _random_team, _available_seasons
                import random as _rnd
                p1 = _random_player()
                p2 = _random_player(exclude=p1)
                t1 = _random_team()
                season = _rnd.choice(_available_seasons())
                chips = _chips([
                    f"Tell me about {p1}",
                    f"{p2} stats in {season}",
                    f"{t1} record in {season}",
                    f"Compare {p1} and {p2}",
                ])
                result["intent"] = "entity-not-found"
                result["source"] = source
                result["rich"] = [[chips]] if chips else None
                result["text"] = result["text"] + "\n\nTry one of these:"

        return jsonify(result)

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
    app.run(host="0.0.0.0", port=5000, debug=False)