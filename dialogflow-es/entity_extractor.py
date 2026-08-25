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
    "james": "LeBron James",
    "curry": "Stephen Curry",
    "jokic": "Nikola Jokic",
    "giannis": "Giannis Antetokounmpo",
    "embiid": "Joel Embiid",
    "wilt": "Wilt Chamberlain",
    "kareem": "Kareem Abdul-Jabbar",
    "tmac": "Tracy McGrady",
    "dirk": "Dirk Nowitzki",
    "nowitzki": "Dirk Nowitzki",
    "yao ming": "Yao Ming",
    "yao": "Yao Ming",
    "hakeem": "Hakeem Olajuwon",
    "olajuwon": "Hakeem Olajuwon",
    "wade": "Dwyane Wade",
    "kawhi": "Kawhi Leonard",
    "leonard": "Kawhi Leonard",
    "cp3": "Chris Paul",
    "kd": "Kevin Durant",
    "durant": "Kevin Durant",
    "harden": "James Harden",
    "westbrook": "Russell Westbrook",
    "doncic": "Luka Doncic",
    "kyrie": "Kyrie Irving",
    "irving": "Kyrie Irving",
    "stockton": "John Stockton",
    "nash": "Steve Nash",
    "rodman": "Dennis Rodman",
    "pippen": "Scottie Pippen",
    "garnett": "Kevin Garnett",
    "carmelo": "Carmelo Anthony",
    "melo": "Carmelo Anthony",
    "anthony": "Carmelo Anthony",
    "klay": "Klay Thompson",
    "korver": "Kyle Korver",
    "draymond": "Draymond Green",
    "butler": "Jimmy Butler",
    "beverley": "Patrick Beverley",
    "gobert": "Rudy Gobert",
    "trae": "Trae Young",
    "young": "Trae Young",
    "zion": "Zion Williamson",
    "derozan": "DeMar DeRozan",
    "manu": "Manu Ginobili",
    "ginobili": "Manu Ginobili",
    "wembanyama": "Victor Wembanyama",
    "lillard": "Damian Lillard",
    "dame": "Damian Lillard",
    "rondo": "Rajon Rondo",
    "crawford": "Jamal Crawford",
    "howard": "Dwight Howard",
    "porzingis": "Kristaps Porzingis",
    "reggie miller": "Reggie Miller",
    "jordan": "Michael Jordan",
}

TEAM_NICKS = {
    "lakers": "Los Angeles Lakers",
    "celtics": "Boston Celtics",
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

    candidates: list[tuple] = []

    for m in _CACHE["player_pattern"].finditer(query_text):
        value = _CACHE["player_values"][m.group(1).lower()]
        candidates.append((m.start(), m.end(), "player", value))
    taken = {c[3] for c in candidates}

    for m in _CACHE["surname_pattern"].finditer(query_text):
        value = _CACHE["surname_values"][m.group(1).lower()]
        if value not in taken:
            candidates.append((m.start(), m.end(), "player", value))

    for m in _CACHE["team_pattern"].finditer(query_text):
        value = _CACHE["team_values"][m.group(1).lower()]
        candidates.append((m.start(), m.end(), "team", value))

    season_re = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")

    for m in season_re.finditer(query_text):
        candidates.append((m.start(), m.end(), "season", m.group(1)))

    # Earliest match wins; longer breaks ties.

    order = {"player": 0, "team": 1, "season": 2}
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
    return result