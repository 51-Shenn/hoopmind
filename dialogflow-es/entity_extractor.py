"""
HoopMind - free-text entity extraction.

The deployed Dialogflow agent sends training phrases without
entity annotations, so parameters frequently arrive EMPTY at the
webhook. This module recovers players, teams and seasons
directly from the raw query text so the engine always receives
usable entities. Dialogflow-extracted values (when present)
always take precedence; this only fills the gaps.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from functools import lru_cache

from config import DATA_DIR


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9 ]+", " ", text.lower())

    return re.sub(r"\s+", " ", text).strip()


PLAYER_NICKS = {
    "shaq": "Shaquille O'Neal",
    "kobe": "Kobe Bryant",
    "magic": "Magic Johnson",
    "lebron": "LeBron James",
    "curry": "Stephen Curry",
    "jokic": "Nikola Jokic",
    "giannis": "Giannis Antetokounmpo",
    "embiid": "Joel Embiid",
    "wilt": "Wilt Chamberlain",
    "kareem": "Kareem Abdul-Jabbar",
    "tmac": "Tracy McGrady",
    "dirk": "Dirk Nowitzki",
    "yao": "Yao Ming",
    "hakeem": "Hakeem Olajuwon",
    "olajuwon": "Hakeem Olajuwon",
    "wade": "Dwyane Wade",
    "kawhi": "Kawhi Leonard",
    "leonard": "Kawhi Leonard",
    "cp3": "Chris Paul",
    "pg": "Paul George",
    "kd": "Kevin Durant",
    "durant": "Kevin Durant",
    "harden": "James Harden",
    "westbrook": "Russell Westbrook",
    "luka": "Luka Doncic",
    "doncic": "Luka Doncic",
    "kyrie": "Kyrie Irving",
    "irving": "Kyrie Irving",
    "stockton": "John Stockton",
    "nash": "Steve Nash",
    "rodman": "Dennis Rodman",
    "scottie": "Scottie Pippen",
    "garnett": "Kevin Garnett",
    "carmelo": "Carmelo Anthony",
    "melo": "Carmelo Anthony",
    "klay": "Klay Thompson",
    "korver": "Kyle Korver",
    "draymond": "Draymond Green",
    "butler": "Jimmy Butler",
    "beverley": "Patrick Beverley",
    "gobert": "Rudy Gobert",
    "trae": "Trae Young",
    "zion": "Zion Williamson",
    "derozan": "DeMar DeRozan",
    "manu": "Manu Ginobili",
    "wembanyama": "Victor Wembanyama",
    "lillard": "Damian Lillard",
    "dame": "Damian Lillard",
    "rondo": "Rajon Rondo",
    "porzingis": "Kristaps Porzingis",
    "reggie miller": "Reggie Miller",
    "bird": "Larry Bird",
    "jordan": "Michael Jordan",
    "mj": "Michael Jordan",
}

TEAM_NICKS = {
    "lakers": "Los Angeles Lakers",
    "boston": "Boston Celtics",
    "warriors": "Golden State Warriors",
    "bulls": "Chicago Bulls",
    "nuggets": "Denver Nuggets",
    "raptors": "Toronto Raptors",
    "76ers": "Philadelphia 76ers",
    "sixers": "Philadelphia 76ers",
    "grizzlies": "Memphis Grizzlies",
    "kings": "Sacramento Kings",
    "suns": "Phoenix Suns",
    "mavericks": "Dallas Mavericks",
    "mavs": "Dallas Mavericks",
    "pistons": "Detroit Pistons",
    "thunder": "Oklahoma City Thunder",
    "rockets": "Houston Rockets",
    "bucks": "Milwaukee Bucks",
    "heat": "Miami Heat",
    "spurs": "San Antonio Spurs",
    "pacers": "Indiana Pacers",
    "jazz": "Utah Jazz",
    "knicks": "New York Knicks",
    "nets": "Brooklyn Nets",
    "cavaliers": "Cleveland Cavaliers",
    "cavs": "Cleveland Cavaliers",
    "clippers": "Los Angeles Clippers",
    "blazers": "Portland Trail Blazers",
    "trail blazers": "Portland Trail Blazers",
    "timberwolves": "Minnesota Timberwolves",
    "wolves": "Minnesota Timberwolves",
    "pelicans": "New Orleans Pelicans",
    "hornets": "Charlotte Hornets",
    "wizards": "Washington Wizards",
    "hawks": "Atlanta Hawks",
}

_BOUNDARY_BEFORE = r"(?<![A-Za-z0-9])"

# Possessive is matched via lookahead so it stays OUT of the
# captured surface text.

_TAIL = r"(?=(?:'s?\b)?(?:[^A-Za-z0-9]|$))"

_CACHE: dict = {}


def _load_names() -> None:
    if _CACHE:
        return

    players: list[str] = []

    with open(
        DATA_DIR / "Player Career Info.csv", encoding="utf-8-sig", newline=""
    ) as fh:
        for row in csv.DictReader(fh):
            name = (row.get("player") or "").strip()
            if name:
                players.append(name)

    player_lookup = {p: p for p in set(players)}

    for nick, full in PLAYER_NICKS.items():
        if full in player_lookup:
            player_lookup[nick] = full

    # Unique surnames as fallback aliases.

    last_counts: dict[str, set] = {}

    for p in set(players):
        tokens = _norm(p).split()
        if tokens:
            last_counts.setdefault(tokens[-1], set()).add(p)

    surnames = {
        full: last
        for last, holders in last_counts.items()
        if len(holders) == 1 and len(last) >= 5
        for full in holders
    }

    team_lookup = {}

    with open(
        DATA_DIR / "Team Summaries.csv", encoding="utf-8-sig", newline=""
    ) as fh:
        for row in csv.DictReader(fh):
            name = (row.get("team") or "").strip()
            if name and name.lower() != "league average":
                team_lookup[name] = name

    for nick, full in TEAM_NICKS.items():
        if full in team_lookup:
            team_lookup[nick] = full

    _CACHE["player_pattern"] = re.compile(
        _BOUNDARY_BEFORE
        + "("
        + "|".join(
            sorted(
                (re.escape(k) for k in player_lookup), key=len, reverse=True
            )
        )
        + ")"
        + _TAIL,
        re.IGNORECASE,
    )

    _CACHE["player_values"] = {k.lower(): v for k, v in player_lookup.items()}

    surname_items = [(last, full) for full, last in surnames.items()]
    surname_items.sort(key=lambda t: len(t[0]), reverse=True)

    _CACHE["surname_pattern"] = re.compile(
        _BOUNDARY_BEFORE
        + "("
        + "|".join(re.escape(last) for last, _full in surname_items)
        + ")"
        + _TAIL,
        re.IGNORECASE,
    )

    _CACHE["surname_values"] = {
        last.lower(): full for last, full in surname_items
    }

    _CACHE["team_pattern"] = re.compile(
        _BOUNDARY_BEFORE
        + "("
        + "|".join(
            sorted((re.escape(k) for k in team_lookup), key=len, reverse=True)
        )
        + ")"
        + _TAIL,
        re.IGNORECASE,
    )

    _CACHE["team_values"] = {k.lower(): v for k, v in team_lookup.items()}


@lru_cache(maxsize=512)
def extract(query_text: str) -> dict:
    """
    Return {'player': [...], 'team': [...],
            'season': 'YYYY'} for whatever is found.
    """

    if not query_text:
        return {}
    _load_names()

    # Strip possessive "'s" or bare "'s" so "Currys" matches "Curry"
    _possessive = re.sub(r"['''\u2019]s\b", " ", query_text)

    candidates: list[tuple] = []

    for m in _CACHE["player_pattern"].finditer(_possessive):
        value = _CACHE["player_values"][m.group(1).lower()]
        candidates.append((m.start(), m.end(), "player", value))
    taken = {c[3] for c in candidates}

    for m in _CACHE["surname_pattern"].finditer(_possessive):
        value = _CACHE["surname_values"][m.group(1).lower()]
        if value not in taken:
            candidates.append((m.start(), m.end(), "player", value))

    for m in _CACHE["team_pattern"].finditer(_possessive):
        value = _CACHE["team_values"][m.group(1).lower()]
        candidates.append((m.start(), m.end(), "team", value))

    season_re = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")

    for m in season_re.finditer(query_text):
        candidates.append((m.start(), m.end(), "season", m.group(1)))

    # Earliest match wins; longer breaks ties.

    order = {"team": 0, "player": 1, "season": 2}
    candidates.sort(key=lambda c: (c[0], -(c[1] - c[0]), order[c[2]]))
    picked: list[tuple] = []
    last_end = -1

    for c in candidates:
        if c[0] >= last_end:
            picked.append(c)
            last_end = c[1]

    result: dict = {}

    for _s, _e, kind, value in picked:
        if kind == "season":
            result.setdefault("season", value)
        else:
            result.setdefault(kind, []).append(value)

    # ----------------------------------------------------------
    # Fuzzy player fallback: when no player was found via exact
    # regex, try close matches against the full player list so
    # misspellings / missing punctuation still resolve.
    #
    # Safety rules to avoid hallucinations (e.g. "games" → "LeBron
    # James"):
    #   * Single tokens (1-word chunks) only match if the token
    #     is ≥5 letters long (avoids short common words).
    #   * All chunks use a tighter 0.85 cutoff.
    #   * Longer chunks (≥2 tokens) are always preferred.
    # ----------------------------------------------------------
    if not result.get("player") and not result.get("team"):
        from difflib import get_close_matches
        tokens = _norm(query_text).split()
        candidates_long: list[str] = []  # from 2+ token chunks (preferred)
        candidates_short: list[str] = []  # from 1-token chunks (stricter)
        player_list = list(_CACHE.get("player_values", {}))
        for n in range(1, min(len(tokens) + 1, 5)):
            for i in range(len(tokens) - n + 1):
                chunk = " ".join(tokens[i : i + n])
                if n == 1 and len(chunk) < 5:
                    continue  # skip short single words
                matches = get_close_matches(
                    chunk, player_list, n=1, cutoff=0.85,
                )
                if matches:
                    resolved = _CACHE["player_values"][matches[0].lower()]
                    if n >= 2:
                        candidates_long.append(resolved)
                    else:
                        candidates_short.append(resolved)
        candidates = candidates_long or candidates_short
        if candidates:
            result["player"] = [candidates[0]]

    q = query_text.lower()
    attr_map = [
        (["how tall", "height", "tall is"], "height"),
        (["position", "what position", "plays"], "position"),
        (["weight", "how much does", "how heavy"], "weight"),
        (["born", "birthday", "birth date", "born when", "date of birth"], "born"),
        (["college", "university", "school", "where did", "where did he go"], "college"),
        (["career", "years active", "how long", "from.*to"], "career"),
        (["hall of fame", "hof"], "hall_of_fame"),
    ]
    for keywords, attr in attr_map:
        for kw in keywords:
            if kw in q:
                result["attribute"] = attr
                return result

    return result