"""Entity-first extraction of players, teams and seasons from raw utterances.

The custom actions used to recover entities by stripping hand-listed question
phrases off the utterance and treating whatever survived as the name. That only
worked for the exact phrasings present in ``data/nlu.yml``: any paraphrase leaked
question words into the name ("what can you tell me about the boston celtics"),
and the stop-word pass used unbounded ``str.replace`` so it also chewed through
real names ("Kevin Durant" -> "kev durant", "percentage" -> "centage").

This module inverts the approach - instead of deleting question words, it scans
the utterance for names that actually exist in the loaded CSVs. Everything that
is not a known player, team or season is simply ignored, so phrasing does not
matter. The same strategy is what ``dialogflow-es/entity_extractor.py`` uses.
"""

import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

import actions.data_loader as data_loader
from actions.data_loader import _PLAYER_SYNONYMS, _ensure_loaded

logger = logging.getLogger(__name__)

# Hand-curated team nicknames. These win over anything derived from the CSVs.
TEAM_SYNONYMS = {
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
    "trail blazers": "Portland Trail Blazers",
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

# Player nicknames that are also stat or position abbreviations. Matching these
# as names does more harm than good ("PG" is a position, "AI" is not a query
# about Allen Iverson).
_AMBIGUOUS_PLAYER_ALIASES = {"pg", "ai"}

# A surname only becomes an alias when exactly one player in the dataset carries
# it and it is long enough not to collide with ordinary English.
_MIN_SURNAME_LEN = 5

# Aliases derived from the CSVs (mascots, city prefixes, surnames) are rejected
# when they are ordinary English. Without this, "The Floridians" contributes the
# alias "the" and matches every utterance in the dataset.
_STOPWORD_ALIASES = {
    "a", "all", "an", "and", "any", "are", "as", "at", "be", "best", "by",
    "can", "did", "do", "does", "for", "from", "game", "games", "had", "has",
    "have", "he", "her", "him", "his", "how", "in", "is", "it", "its", "many",
    "me", "more", "most", "much", "my", "new", "no", "not", "of", "on", "one",
    "or", "per", "play", "played", "player", "players", "plays", "point",
    "points", "season", "seasons", "she", "show", "so", "stat", "stats", "team",
    "teams", "tell", "that", "the", "their", "them", "there", "they", "this",
    "to", "top", "two", "up", "us", "was", "we", "were", "what", "when",
    "where", "which", "who", "why", "win", "wins", "with", "won", "you", "your",
}

# CSV team abbreviations are matched case-sensitively against the original text:
# lowercased they collide with English ("WAS" -> "was", "AND" -> "and").
_MIN_ABBR_LEN = 2
_MAX_ABBR_LEN = 4

# Possessives are matched with a lookahead so they stay out of the captured span.
_BOUNDARY_BEFORE = r"(?<![A-Za-z0-9])"
_TAIL = r"(?=(?:'s?\b)?(?:[^A-Za-z0-9]|$))"

_SEASON_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")

_CACHE: Dict[str, Any] = {}


def _fold(text: str) -> str:
    """Lowercase and strip accents while preserving character offsets.

    Offsets have to survive so a match against the folded text can be reported
    against the original. Decomposing the whole string with NFKD would shift
    them, so each character is folded on its own and collapsed back to one.
    """
    out = []
    for ch in text:
        decomposed = unicodedata.normalize("NFKD", ch)
        base = "".join(c for c in decomposed if not unicodedata.combining(c))
        out.append(base[0].lower() if base else ch.lower())
    return "".join(out)


def _alias_variants(name: str) -> List[str]:
    """Folded spellings a user might plausibly type for `name`."""
    folded = _fold(name)
    variants = {folded}
    if "'" in folded:
        variants.add(folded.replace("'", ""))
    if "-" in folded:
        variants.add(folded.replace("-", " "))
        variants.add(folded.replace("-", ""))
    if "." in folded:
        variants.add(folded.replace(".", ""))
    return [v for v in variants if v.strip()]


def _compile_alias_pattern(aliases: Dict[str, str]) -> Optional[re.Pattern]:
    if not aliases:
        return None
    # Longest first so "los angeles lakers" wins over "lakers".
    ordered = sorted(aliases, key=len, reverse=True)
    return re.compile(
        _BOUNDARY_BEFORE + "(" + "|".join(re.escape(a) for a in ordered) + ")" + _TAIL
    )


def _build_player_aliases() -> tuple:
    """Return ``(aliases, weak_aliases)``.

    Weak aliases are the ones derived from bare surnames. Some of those are also
    ordinary English words - "Which major honors ..." should not resolve to
    Renaldo Major - so they carry less authority than a full name or a curated
    nickname. See `extract_entities` for how that is applied.
    """
    names = set()
    for df in (data_loader.player_per_game_df, data_loader.player_career_df):
        if df is not None and "player" in df.columns:
            names.update(
                str(n).strip() for n in df["player"].dropna().unique() if str(n).strip()
            )

    aliases: Dict[str, str] = {}
    for name in names:
        for variant in _alias_variants(name):
            aliases.setdefault(variant, name)

    # Unique surnames, e.g. "Antetokounmpo" -> "Giannis Antetokounmpo".
    holders: Dict[str, set] = {}
    for name in names:
        tokens = _fold(name).split()
        if tokens:
            holders.setdefault(tokens[-1], set()).add(name)
    weak = set()
    for surname, owners in holders.items():
        if (
            len(owners) == 1
            and len(surname) >= _MIN_SURNAME_LEN
            and surname not in _STOPWORD_ALIASES
            and surname not in aliases
        ):
            aliases[surname] = next(iter(owners))
            weak.add(surname)

    # Hand-curated nicknames win over derived surnames.
    canonical = {_fold(n): n for n in names}
    for alias, full in _PLAYER_SYNONYMS.items():
        folded_alias = _fold(alias)
        if folded_alias in _AMBIGUOUS_PLAYER_ALIASES:
            continue
        resolved = canonical.get(_fold(full))
        if resolved:
            aliases[folded_alias] = resolved
            weak.discard(folded_alias)
    return aliases, weak


def _build_team_aliases() -> tuple:
    """Return ``(name_aliases, abbrev_aliases)``.

    Name aliases are matched case-insensitively; abbreviations are matched
    case-sensitively against the original text so "WAS" does not swallow "was".
    """
    # alias -> (team, most recent season using it); newest wins collisions so
    # "Lakers" resolves to Los Angeles rather than Minneapolis.
    best: Dict[str, tuple] = {}
    abbrevs: Dict[str, tuple] = {}

    def offer(store: Dict[str, tuple], alias: str, team: str, season: int) -> None:
        alias = alias.strip()
        if not alias:
            return
        current = store.get(alias)
        if current is None or season > current[1]:
            store[alias] = (team, season)

    for df in (data_loader.team_summaries_df, data_loader.team_stats_df):
        if df is None or "team" not in df.columns:
            continue
        for team, season, abbr in zip(
            df["team"], df["season"], df.get("abbreviation", df["team"])
        ):
            team = str(team).strip()
            if not team or team.lower() == "league average":
                continue
            try:
                season = int(season)
            except (TypeError, ValueError):
                season = 0
            for variant in _alias_variants(team):
                offer(best, variant, team, season)
            tokens = _fold(team).split()
            if len(tokens) >= 2:
                mascot = tokens[-1]
                city = " ".join(tokens[:-1])
                if mascot not in _STOPWORD_ALIASES:
                    offer(best, mascot, team, season)
                if city not in _STOPWORD_ALIASES:
                    offer(best, city, team, season)
            abbr = str(abbr).strip().upper()
            if abbr.isalnum() and _MIN_ABBR_LEN <= len(abbr) <= _MAX_ABBR_LEN:
                offer(abbrevs, abbr, team, season)

    aliases = {alias: team for alias, (team, _season) in best.items()}

    canonical = {_fold(t): t for t, _s in best.values()}
    for alias, full in TEAM_SYNONYMS.items():
        resolved = canonical.get(_fold(full))
        if resolved:
            aliases[_fold(alias)] = resolved

    return aliases, {a: team for a, (team, _s) in abbrevs.items()}


def _load() -> None:
    if _CACHE:
        return
    _ensure_loaded()

    player_aliases, weak_player_aliases = _build_player_aliases()
    team_aliases, team_abbrevs = _build_team_aliases()

    _CACHE["weak_player_aliases"] = weak_player_aliases
    _CACHE["player_aliases"] = player_aliases
    _CACHE["team_aliases"] = team_aliases
    _CACHE["team_abbrevs"] = team_abbrevs
    _CACHE["player_pattern"] = _compile_alias_pattern(player_aliases)
    _CACHE["team_pattern"] = _compile_alias_pattern(team_aliases)
    _CACHE["team_abbrev_pattern"] = _compile_alias_pattern(team_abbrevs)
    logger.info(
        "entity_extract: %d player aliases, %d team aliases, %d abbreviations",
        len(player_aliases),
        len(team_aliases),
        len(team_abbrevs),
    )


def extract_entities(text: str) -> Dict[str, Any]:
    """Return ``{'players': [...], 'teams': [...], 'season': 'YYYY'}``.

    Overlapping matches are resolved by position - earliest start wins, longer
    span breaks ties - so "Orlando Magic" is read as a team rather than as the
    "magic" nickname for Magic Johnson.
    """
    result: Dict[str, Any] = {"players": [], "teams": [], "season": None}
    if not text or not text.strip():
        return result
    _load()

    folded = _fold(text)
    candidates = []

    pattern = _CACHE["player_pattern"]
    if pattern:
        weak_aliases = _CACHE["weak_player_aliases"]
        player_hits = []
        for m in pattern.finditer(folded):
            alias = m.group(1)
            # A bare surname only counts as a name when it is capitalised, or
            # when nothing stronger was found: "Which major honors belong to
            # James Harden?" must not resolve to Renaldo Major.
            weak = alias in weak_aliases and not text[m.start()].isupper()
            player_hits.append(
                (m.start(), m.end(), "players", _CACHE["player_aliases"][alias], weak)
            )
        if any(not hit[4] for hit in player_hits):
            player_hits = [hit for hit in player_hits if not hit[4]]
        candidates.extend(hit[:4] for hit in player_hits)

    pattern = _CACHE["team_pattern"]
    if pattern:
        for m in pattern.finditer(folded):
            candidates.append(
                (m.start(), m.end(), "teams", _CACHE["team_aliases"][m.group(1)])
            )

    # Abbreviations run against the original text so only uppercase "WAS"
    # counts as Washington, never the verb.
    pattern = _CACHE["team_abbrev_pattern"]
    if pattern:
        for m in pattern.finditer(text):
            candidates.append(
                (m.start(), m.end(), "teams", _CACHE["team_abbrevs"][m.group(1)])
            )

    candidates.sort(key=lambda c: (c[0], -(c[1] - c[0])))
    last_end = -1
    for start, end, kind, value in candidates:
        if start < last_end:
            continue
        if value not in result[kind]:
            result[kind].append(value)
        last_end = end

    seasons = _SEASON_RE.findall(folded)
    if seasons:
        result["season"] = seasons[-1]
    return result


def extract_player(text: str) -> Optional[str]:
    players = extract_entities(text)["players"]
    return players[0] if players else None


def extract_players(text: str) -> List[str]:
    return extract_entities(text)["players"]


def extract_team(text: str) -> Optional[str]:
    teams = extract_entities(text)["teams"]
    return teams[0] if teams else None


def extract_teams(text: str) -> List[str]:
    return extract_entities(text)["teams"]


def extract_season(text: str) -> Optional[str]:
    matches = _SEASON_RE.findall(text or "")
    return matches[-1] if matches else None


def extract_seasons(text: str) -> List[str]:
    """Every season mentioned, in order. "the 2016 Warriors or the 1996 Bulls"
    is two comparisons, not one."""
    seen = []
    for season in _SEASON_RE.findall(text or ""):
        if season not in seen:
            seen.append(season)
    return seen
