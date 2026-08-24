"""
HoopMind response generator.

Renders engine results as one of six reusable UI components:

  InfoCard         player/team/draft profile boxes
  StatTable        single-entity statistic tables
  AwardTable       award / honour listings
  ComparisonTable  side-by-side player or team comparisons
  SummaryCard      season summary boxes
  TextResponse     conversational replies

Design rules:
  single value      -> mini stat card
  multiple stats    -> stat table
  two entities      -> comparison table + verdict line
  profile           -> info card
  conversation      -> plain text
"""

from __future__ import annotations

import logging
import random

from typing import Any

AWARD_UPPER = {"nba", "mvp", "dpoy", "roy", "mip", "smoy"}

# Canonical team names (match the CSVs) used for the random
# comparison partner in suggestion chips.

NBA_TEAM_NAMES = (
    "Atlanta Hawks",
    "Boston Celtics",
    "Brooklyn Nets",
    "Charlotte Hornets",
    "Chicago Bulls",
    "Cleveland Cavaliers",
    "Dallas Mavericks",
    "Denver Nuggets",
    "Detroit Pistons",
    "Golden State Warriors",
    "Houston Rockets",
    "Indiana Pacers",
    "Los Angeles Clippers",
    "Los Angeles Lakers",
    "Memphis Grizzlies",
    "Miami Heat",
    "Milwaukee Bucks",
    "Minnesota Timberwolves",
    "New Orleans Pelicans",
    "New York Knicks",
    "Oklahoma City Thunder",
    "Orlando Magic",
    "Philadelphia 76ers",
    "Phoenix Suns",
    "Portland Trail Blazers",
    "Sacramento Kings",
    "San Antonio Spurs",
    "Toronto Raptors",
    "Utah Jazz",
    "Washington Wizards",
)


def _random_team(exclude: str | None = None) -> str:
    name = (exclude or "").casefold()
    pool = [team for team in NBA_TEAM_NAMES if team.casefold() != name]

    return random.choice(pool)


BOX_W = 46  # default inner width of box cards

# Pretty display names for canonical statistics.
STAT_PRETTY = {
    "points": "Points",
    "points_per_game": "Points per game",
    "rebounds": "Rebounds",
    "assists": "Assists",
    "steals": "Steals",
    "blocks": "Blocks",
    "field goal percentage": "Field goal %",
    "three-pointers": "Three-Pointers",
    "turnovers": "Turnovers",
    "minutes": "Minutes",
    "per": "Player Efficiency Rating",
    "player efficiency rating": "Player Efficiency Rating",
    "efficiency": "Player Efficiency Rating",
    "true shooting percentage": "True shooting %",
    "true shooting": "True shooting %",
    "ts": "True shooting %",
    "ts%": "True shooting %",
    "effective field goal percentage": "Effective field goal %",
    "efg": "Effective field goal %",
    "usage percentage": "Usage %",
    "usg%": "Usage %",
    "win shares": "Win shares",
    "ws": "Win shares",
    "box plus/minus": "Box plus/minus",
    "bpm": "Box plus/minus",
    "value over replacement player": "Value over replacement",
    "vorp": "VORP",
}


# ============================================================
# FULL-WORD EXPANSION
#
# The engine and datasets use short forms (PPG, REB, FG%...).
# Every user-facing string is passed through _fw() so the UI
# always shows full words, regardless of where the label came
# from.
# ============================================================
_FULL_PHRASES = (
    ("Point Diff.", "Point differential"),
    ("Off Rating", "Offensive rating"),
    ("Def Rating", "Defensive rating"),
    ("Win %", "Win percentage"),
)

_FULL_WORDS = {
    "PPG": "Points per game",
    "RPG": "Rebounds per game",
    "APG": "Assists per game",
    "SPG": "Steals per game",
    "BPG": "Blocks per game",
    "TPG": "Turnovers per game",
    "MPG": "Minutes per game",
    "PTS": "Points",
    "REB": "Rebounds",
    "AST": "Assists",
    "STL": "Steals",
    "BLK": "Blocks",
    "TOV": "Turnovers",
    "GP": "Games played",
    "GS": "Games started",
    "PER": "Player Efficiency Rating",
    "TS%": "True shooting %",
    "eFG%": "Effective field goal %",
    "FG%": "Field goal %",
    "3P%": "Three-point %",
    "2P%": "Two-point %",
    "FT%": "Free throw %",
    "USG%": "Usage %",
    "WS": "Win shares",
    "BPM": "Box plus/minus",
    "VORP": "Value over replacement",
}

import re as _re

_FW_TOKEN = _re.compile(
    "(?<![A-Za-z0-9])("
    + "|".join(
        sorted((_re.escape(k) for k in _FULL_WORDS), key=len, reverse=True)
    )
    + ")(?![A-Za-z0-9])"
)


def _fw(text: str) -> str:
    if not text:
        return text

    for find, replace in _FULL_PHRASES:
        text = text.replace(find, replace)

    return _FW_TOKEN.sub(lambda m: _FULL_WORDS[m.group(1)], text)


def _expand_rich(rows):
    """Apply _fw() to every string inside rich cards."""
    if not rows:
        return rows

    expanded = []

    for row in rows:
        new_row = []
        for card in row:
            card = dict(card)
            for key in ("title", "subtitle"):
                value = card.get(key)
                if isinstance(value, str):
                    card[key] = _fw(value)

            texts = card.get("text")

            if isinstance(texts, list):
                card["text"] = [_fw(str(line)) for line in texts]

            new_row.append(card)

        expanded.append(new_row)

    return expanded


# ============================================================
# LOW-LEVEL FORMATTERS
# ============================================================


def _clean(v: Any) -> Any:
    """Normalize dataset noise: None / NaN / empty / booleans."""
    if v is None or v is False:
        return None

    text = str(v).strip()

    if text.lower() in ("", "nan", "none", "false"):
        return None

    return text


def _fmt(v: Any) -> str:
    if v is None:
        return "N/A"
    return str(v)


def _num(v: Any) -> str:
    try:
        f = float(v)
        return str(int(f)) if f.is_integer() else str(round(f, 3))
    except (TypeError, ValueError):
        return _fmt(v)


def _thousand(v: Any) -> str:
    """Integer formatting with thousands separators (career totals)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _fmt(v)

    if f.is_integer() and abs(f) >= 1000:
        return f"{int(f):,}"

    return _num(f)


def _stat_value(stat: Any, v: Any) -> str:
    """Format a stat value, converting ratios to percentages safely."""
    if isinstance(v, str) and v.strip().endswith("%"):
        return v

    try:
        f = float(v)
    except (TypeError, ValueError):
        return _fmt(v)

    label = str(stat or "").lower()
    if "percent" in label or "%" in label:
        scaled = f * 100 if abs(f) <= 1.5 else f
        return f"{round(scaled, 1)}%"

    if abs(f) >= 1000 and float(f).is_integer():
        return f"{int(f):,}"

    return _num(f)


DATASET_LABELS = {
    "Advanced.csv": "Advanced",
    "Per 100 Poss.csv": "Per 100 Possessions",
    "Per 36 Minutes.csv": "Per 36 Minutes",
    "Player Shooting.csv": "Shooting",
    "Player Play By Play.csv": "Play-by-Play",
    "Player Totals.csv": "Career Totals",
}


def _pretty_stat(stat: Any, dataset: str = "") -> str:
    """Human label for a canonical stat name."""
    s = STAT_PRETTY.get(str(stat or "").casefold())

    if s:
        return s

    text = str(stat or "that statistic").replace("_", " ")
    return text[:1].upper() + text[1:]


AWARD_PRETTY = {
    "nba mvp": "NBA MVP",
    "nba dpoy": "NBA DPOY",
    "nba mip": "NBA MIP",
    "nba roy": "NBA ROY",
    "nba smoy": "NBA SMOY",
    "nba clutch_poy": "NBA Clutch POY",
    "aba mvp": "ABA MVP",
    "aba roy": "ABA ROY",
    "baa roy": "BAA ROY",
}


def _pretty_award(name: Any) -> str:
    text = _clean(name)

    if not text:
        return "N/A"

    key = " ".join(text.lower().replace("_", " ").split())

    if key in AWARD_PRETTY:
        return AWARD_PRETTY[key]

    words = []
    for word in text.replace("_", " ").split():
        words.append(
            word.upper() if word.lower() in AWARD_UPPER else word.capitalize()
        )

    return " ".join(words)


def _ordinal(n: Any) -> str:
    try:
        n = int(float(str(n).strip()))
    except (TypeError, ValueError):
        return str(n)
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _feet_inches(total_inches: Any) -> str | None:
    try:
        inches = int(float(total_inches))
    except (TypeError, ValueError):
        return None
    return f"{inches // 12}'{inches % 12}\""


def _share(v: Any) -> str:
    """Voting share with consistent 3-decimal precision."""
    try:
        return f"{float(v):.3f}"
    except (TypeError, ValueError):
        return _fmt(v)


def _same_val(a: Any, b: Any) -> bool:
    """Loose numeric/string equality for deduping stat rows."""
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return str(a).strip() == str(b).strip()


def _playoffs_txt(raw: Any) -> Any:
    """Turn boolean-ish playoff flags into friendly text."""
    text = str(raw).strip().lower()

    if text in {"true", "1", "yes"}:
        return "Yes"
    if text in {"false", "0", "no"}:
        return "No"
    return _clean(raw)


def _subject(row: dict[str, Any]) -> str:
    return row.get("player") or row.get("team") or "Unknown"


def _name(row: dict[str, Any]) -> str:
    """Subject with article: players bare, teams prefixed with 'the'."""
    player = row.get("player")

    if player:
        return str(player)

    team = row.get("team")

    return f"the {team}" if team else "Unknown"


def _sentence(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def _verdict(a: dict[str, Any], b: dict[str, Any], stat: str) -> str:
    va, vb = a.get("value"), b.get("value")
    try:
        fa, fb = float(str(va).rstrip("%")), float(str(vb).rstrip("%"))
    except (TypeError, ValueError):
        return (
            f"{_name(a)} recorded {_fmt(va)}, while {_name(b)} "
            f"recorded {_fmt(vb)}."
        )
    if fa == fb:
        return (
            f"It's dead even: {_name(a)} and {_name(b)} both "
            f"recorded {_stat_value(stat, fa)}."
        )

    winner, loser = (a, b) if fa > fb else (b, a)

    return (
        f"Result: {_sentence(_name(winner))} leads with "
        f"{_stat_value(stat, max(fa, fb))} versus "
        f"{_stat_value(stat, min(fa, fb))} for {_name(loser)}."
    )


# ============================================================
# BOX-DRAWING COMPONENTS
# ============================================================
def _disp_len(text: str) -> int:
    """Visual width: emoji/symbols count as 2 columns."""

    return sum(2 if ord(ch) >= 0x2300 else 1 for ch in text)


def _pad(text: str, width: int) -> str:
    gap = max(0, width - _disp_len(text))
    return text + " " * gap


def _box(
    title: str,
    lines: list[tuple[str, Any]],
    subtitle: str | None = None,
    width: int = BOX_W,
    footer: str | None = None,
) -> str:
    """
    Render an InfoCard-style box:
    ┌──────────────────────────────┐
    │ 🏀 LeBron James              │
    ├──────────────────────────────┤
    │ Position:   SF/PF            │
    │ Height:     6'9"             │
    └──────────────────────────────┘
    """

    # Widen to fit the longest content line.

    longest = max(
        [_disp_len(title)]
        + ([_disp_len(subtitle)] if subtitle else [])
        + [_disp_len(f"{lab}: {val}") + 2 for lab, val in lines]
        + ([_disp_len(footer)] if footer else []),
        default=width - 4,
    )

    inner = max(width - 4, min(longest + 2, 60))
    top = "┌" + "─" * inner + "┐"
    sep = "├" + "─" * inner + "┤"
    bottom = "└" + "─" * inner + "┘"
    out = [top, "│ " + _pad(title, inner - 2) + " │"]

    if subtitle:
        out.append("│ " + _pad(subtitle, inner - 2) + " │")
    out.append(sep)

    for lab, val in lines:
        val_text = _fmt(val)
        out.append("│ " + _pad(f"{lab}: {val_text}", inner - 2) + " │")

    if footer:
        out.append(sep)
        out.append("│ " + _pad(footer, inner - 2) + " │")

    out.append(bottom)

    return "\n".join(out)


def _table_box(
    title: str,
    headers: list[str],
    data_rows: list[list[Any]],
    width: int = BOX_W,
    footer: list[str] | None = None,
) -> str:
    """
    Render a multi-column comparison table inside a box.
    First column left-aligned; remaining columns right-aligned.
    """
    col_widths = []

    for i, h in enumerate(headers):
        cells = [_disp_len(h)] + [_disp_len(_fmt(r[i])) for r in data_rows]
        col_widths.append(max(cells))

    total = sum(col_widths) + 2 * len(col_widths)
    inner = max(width - 4, min(total + 2, 62))

    def row_line(cells: list[Any]) -> str:
        parts = [_pad(_fmt(cells[0]), col_widths[0])]

        for i, cell in enumerate(cells[1:], start=1):
            parts.append(_fmt(cell).rjust(col_widths[i]))

        return "  ".join(parts).rstrip()

    top = "┌" + "─" * inner + "┐"
    sep = "├" + "─" * inner + "┤"
    bottom = "└" + "─" * inner + "┘"

    out = [
        top,
        "│ " + _pad(title, inner - 2) + " │",
        sep,
        "│ " + _pad(row_line(headers), inner - 2) + " │",
    ]

    for r in data_rows:
        out.append("│ " + _pad(row_line(r), inner - 2) + " │")

    for extra in footer or []:
        out.append(sep)
        out.append("│ " + _pad(extra, inner - 2) + " │")

    out.append(bottom)

    return "\n".join(out)


def _two_col_grid(items: list[str], header: str) -> str:
    """Two-column alphabetical grid (roster lists). No borders."""
    items = sorted(items)
    half = (len(items) + 1) // 2
    left = items[:half]
    right = items[half:] + [""] * (half - len(items[half:]))
    lw = max((_disp_len(i) for i in left), default=0)
    lines = [header]

    for l_name, r_name in zip(left, right):
        lines.append(f"{_pad(l_name, lw)}    {r_name}".rstrip())
    return "\n".join(lines)


# ============================================================
# PUBLIC ENTRY POINT
# ============================================================
def _flatten_rich(rows: list | None) -> str | None:
    """
    Flatten the rich-card structure into plain text so
    curl / logs show EXACTLY what the Streamlit widget
    shows (minus chips). Single source of truth for UI.
    """
    if not rows:
        return None
    out: list[str] = []

    for row in rows:
        for card in row:
            ctype = card.get("type")
            if ctype == "info":
                title = (card.get("title") or "").strip()
                subtitle = (card.get("subtitle") or "").strip()

                if title:
                    out.append(title)
                if subtitle:
                    out.append(subtitle)

            elif ctype == "description":
                title = (card.get("title") or "").strip()
                if title:
                    out.append(title)

                out.extend(str(line) for line in (card.get("text") or []))

            # chips are interactive-only: skipped
        out.append("")

    text = "\n".join(out).strip()

    return text or None


def generate(result: dict[str, Any], intent: str, query_text: str = "") -> str:
    """
    Falls back to the legacy
    template only if the rich builder fails. Appends a
    transparency note whenever the engine auto-corrected a
    misspelled player name.
    """
    try:
        rows = _build_rich(result, intent, query_text)
    except Exception:  # pragma: no cover - safety net
        logging.exception("Rich build failed for text path")

        rows = None

    text = _flatten_rich(rows)
    if not text:
        text = _generate_template(result, intent, query_text)
    text = _fw(text)

    corrected = result.get("fuzzy_matched")

    if corrected:
        text += f"\n\n(Note: I assumed you meant {corrected}.)"

    return text


def _generate_template(
    result: dict[str, Any], intent: str, query_text: str = ""
) -> str:
    kind = result.get("kind")

    # ============================================================
    # TEXT RESPONSE: greeting / goodbye
    # ============================================================
    if intent == "greeting":
        return (
            "👋 Hello! I'm HoopMind.\n"
            "I can help you explore NBA players, teams, statistics, "
            "awards and more.\nWhat would you like to know?"
        )

    if intent == "goodbye":
        return "👋 Thanks for using HoopMind!\nSee you next time! 🏀"

    # ============================================================
    # CATEGORY CARD: dataset_scope
    # ============================================================

    if kind == "dataset_scope":
        datasets = result.get("datasets", [])

        seasons_note = ""
        if datasets:
            seasons_note = (
                f"\n📅 Coverage: NBA seasons from 1947 to recent, "
                f"across {len(datasets)} datasets."
            )

        return (
            "📚 HoopMind Knowledge Base\n"
            "I can provide information about:\n\n"
            "👤 Players\n"
            "• Player profiles & career info\n"
            "• Season, per-36, per-100, advanced,\n"
            "   shooting & play-by-play statistics\n"
            "• Career totals\n\n"
            "🏀 Teams\n"
            "• Team summaries & season stats\n"
            "• Opponent statistics\n\n"
            "🏆 History\n"
            "• Awards & All-Star selections\n"
            "• All-NBA / All-Defensive teams\n"
            "• Draft history"
            + seasons_note
            + '\n\nTry: "How many points did Michael Jordan average '
            'in 1991?" or "Compare the Lakers and Celtics in 2010".'
        )

    # ============================================================
    # TEXT RESPONSE: league_information
    # ============================================================
    if kind == "league_information":
        if result.get("player_leagues"):
            leagues = result["player_leagues"]
            name = result.get("player")
            span = result.get("span")
            tail = f" ({span})" if span else ""

            return f"🌎 {name} played in " f"{' and '.join(leagues)}{tail}."

        league = result.get("league", "NBA")
        return (
            f"🏀 HoopMind currently covers {league} history from the first "
            "season through recent seasons, spanning player, team and "
            "awards data. Ask me about any player, team or season!"
        )

    # ============================================================
    # INFOCARD: player_information / player_career_information
    # ============================================================
    if kind == "player_information":
        r = result["row"]
        name = r.get("player") or "That player"

        pos = str(_clean(r.get("pos")) or "").replace("-", "/")
        height = _feet_inches(r.get("ht_in_in"))
        weight = r.get("wt")
        born = _clean(r.get("birth_date"))
        colleges = _clean(r.get("colleges"))
        hof = "Yes 🏆" if str(r.get("hof")).lower() == "true" else "No"

        career_span = None
        if r.get("from") and r.get("to"):
            career_span = f"{_num(r.get('from'))}–{_num(r.get('to'))}"
        debut = _num(r.get("from")) if r.get("from") else None

        lines = []
        if pos:
            lines.append(("Position", pos))
        if height:
            lines.append(("Height", height))
        if weight:
            lines.append(("Weight", f"{_num(weight)} lb"))
        if born:
            lines.append(("Born", born))
        if colleges:
            lines.append(("College", colleges))

        if career_span:
            footer = f"Career span: {career_span}"
        elif debut:
            footer = f"NBA debut: {debut}"
        else:
            footer = None

        return _box(f"🏀 {name}", lines, footer=footer)

    # ============================================================
    # STATTABLE: player_career_totals
    # ============================================================
    if kind == "player_career_total":
        player = result["player"]
        stat = result.get("stat")
        value = result.get("value")
        seasons = result.get("seasons")
        span = result.get("span")
        teams_count = result.get("teams_count")

        # Single-number question -> mini card.

        if result.get("stat_requested"):
            sub = f"Career {_pretty_stat(stat)}"
            footer_bits = []

            if span:
                footer_bits.append(f"Career span: {span}")
            if teams_count is not None and teams_count > 0:
                footer_bits.append(f"Teams: {teams_count}")

            return _box(
                f"👑 {player}",
                [("Career Total", f"{_thousand(value)}")],
                subtitle=sub,
                footer="  •  ".join(footer_bits) or None,
            )

        # Full career totals table.
        context = result.get("context") or []
        rows = [(_clean(c["label"]), _thousand(c["value"])) for c in context]

        if not any(str(lab).casefold() == "games" for lab, _ in rows):
            pass  # games may already be in bundle

        footer = f"Seasons played: {seasons}"

        if span:
            footer += f" ({span})"

        return _box(f"👑 {player} — Career Totals", rows, footer=footer)

    # ============================================================
    # STATTABLE / COMPARISON: player_stat family
    # ============================================================
    if kind == "player_stat":
        rows_out = result["rows"]
        stat = result.get("stat")
        measure = result.get("measure")
        dataset = result.get("dataset", "")
        pretty = _pretty_stat(stat, dataset)

        # --------------------------------------------------------
        # COMPARISON TABLE (two players)
        # --------------------------------------------------------
        if len(rows_out) > 1:
            a, b = rows_out[0], rows_out[1]
            headers = ["Statistic", a["player"], b["player"]]
            data_rows = [
                [
                    "★ " + pretty,
                    _stat_value(stat, a["value"]),
                    _stat_value(stat, b["value"]),
                ]
            ]

            # Secondary shared metrics from context bundles.
            ctx_a = {c["label"]: c["value"] for c in (a.get("context") or [])}
            ctx_b = {c["label"]: c["value"] for c in (b.get("context") or [])}

            for label in ctx_a:
                if (
                    label in ctx_b
                    and label != pretty
                    and not (
                        _same_val(ctx_a[label], a["value"])
                        and _same_val(ctx_b[label], b["value"])
                    )
                ):
                    data_rows.append(
                        [
                            label,
                            _stat_value(label, ctx_a[label]),
                            _stat_value(label, ctx_b[label]),
                        ]
                    )
            footers = []

            if measure == "career totals":
                footers.append("Based on career totals.")
            elif result.get("mode") == "best_season":
                footers.append("Each team's best season used.")
            elif not result.get("season_requested", True):
                footers.append("Latest recorded season used (none specified).")

            conclusion = _verdict(a, b, stat)

            return (
                _table_box(
                    f"⚔️ {a['player']} vs {b['player']}",
                    headers,
                    data_rows,
                    footer=footers,
                )
                + "\n🏆 "
                + conclusion
            )

        # --------------------------------------------------------
        # SINGLE PLAYER
        # --------------------------------------------------------
        r = rows_out[0]

        team = _clean(r.get("team_name") or _clean(r.get("team")))
        age = _clean(r.get("age"))
        games = r.get("g")

        # Mini card when the user asked for exactly one number
        # of one specific season.

        if result.get("stat_requested") and result.get("season_requested"):
            sub_bits = []

            if team:
                sub_bits.append(team)

            dataset_label = DATASET_LABELS.get(dataset)

            if measure == "career totals":
                sub_bits.insert(0, "Career totals")
            elif dataset_label and dataset_label != "Career Totals":
                sub_bits.insert(0, dataset_label)

            title_season = _clean(r.get("season")) or "Career"

            return _box(
                f"📊 {r['player']} — {title_season}",
                [(pretty, _stat_value(stat, r["value"]))],
                subtitle=", ".join(sub_bits) or None,
                footer=(
                    f"Games: {games}"
                    + (f"  •  Age: {_num(age)}" if age else "")
                    if games is not None
                    else None
                ),
            )

        # Fuller stat table otherwise (no explicit stat, or no season).
        context = r.get("context") or []

        data_rows = [
            (c["label"], _stat_value(c["label"], c["value"])) for c in context
        ]

        # Make sure the requested stat appears even if absent
        # from the standard bundle.

        if data_rows and result.get("stat_requested"):
            data_rows[0] = ("★ " + str(data_rows[0][0]), data_rows[0][1])
        if not data_rows:

            return (
                f"📊 {r['player']} — {_clean(r.get('season'))}\n"
                f"{pretty}: {_stat_value(stat, r['value'])}"
            )

        footer_bits = []

        if team:
            footer_bits.append(f"Team: {team}")
        if games is not None:
            footer_bits.append(f"Games: {games}")
        if measure == "career totals":
            footer_bits.append("Career totals")
        elif DATASET_LABELS.get(dataset):
            footer_bits.append(DATASET_LABELS[dataset])

        title_season = _clean(r.get("season")) or "Career"

        return _box(
            f"📊 {r['player']} — {title_season}",
            data_rows,
            footer="  •  ".join(footer_bits) or None,
        )

    # ============================================================
    # INFOCARD: team_information (franchise overview)
    # ============================================================
    if kind == "team_information":
        name = result.get("team", "Franchise")
        win_pct = result.get("win_pct")
        best = result.get("best_record", {})

        lines = [
            ("Seasons completed", result.get("seasons")),
            (
                "All-time record",
                f"{_num(result.get('wins'))}-{_num(result.get('losses'))}",
            ),
            ("Win rate", f"{round(win_pct * 100, 1)}%" if win_pct else "N/A"),
            ("Playoff appearances", result.get("playoff_appearances")),
            (
                "Best season",
                (
                    f"{_fmt(best.get('season'))} "
                    f"({_num(best.get('w'))}-{_num(best.get('l'))})"
                    if best.get("season")
                    else "N/A"
                ),
            ),
        ]

        arena = _clean(result.get("arena"))
        if arena:
            lines.append(("Arena", arena))

        last = result.get("last_season_row") or {}
        if last.get("w") not in (None, "", "nan"):
            lines.append(
                (
                    f"Last season ({_fmt(last.get('season'))})",
                    f"{_num(last.get('w'))}-{_num(last.get('l'))}",
                )
            )

        return _box(f"🏀 {name}", lines)

    # ============================================================
    # SUMMARYCARD: team_summary
    # ============================================================
    if kind == "team_summary":
        rows = result["rows"]

        # --------------------------------------------------------
        # COMPARISON TABLE (two teams)
        # --------------------------------------------------------
        if len(rows) > 1:
            headers = ["Statistic"]
            valid = [
                r
                for r in rows
                if r.get("record", {}).get("w") not in (None, "", "nan")
            ]

            names = []

            for r in rows:
                rec = r.get("record", {})
                nm = _subject(r) or rec.get("team") or "?"

                short = str(nm)
                names.append(short)
                headers.append(short)

            metric_map = [
                ("Wins", "w"),
                ("Losses", "l"),
                ("Win %", "win_pct_calc"),
                ("Point Diff.", "mov"),
                ("Off Rating", "o_rtg"),
                ("Def Rating", "d_rtg"),
                ("Pace", "pace"),
                ("Playoffs", "playoffs"),
            ]

            data_rows = []

            for label, key in metric_map:
                vals = []
                for r in rows:
                    rec = r.get("record", {}) or {}
                    raw = rec.get(key)

                    if key == "win_pct_calc":
                        try:
                            w, l = float(rec.get("w")), float(rec.get("l"))
                            vals.append(f"{round(w / (w + l) * 100, 1)}%")
                        except (TypeError, ValueError):
                            vals.append("—")

                    elif key == "mov":
                        try:
                            f = float(raw)
                            vals.append(
                                f"+{round(f, 1)}"
                                if f > 0
                                else str(round(f, 1))
                            )
                        except (TypeError, ValueError):
                            vals.append("—")

                    elif key == "playoffs":
                        vals.append(_playoffs_txt(raw) or "—")
                    else:
                        vals.append(
                            _num(raw) if raw not in (None, "", "nan") else "—"
                        )

                data_rows.append([label] + vals)

            # Result line: better record wins.
            result_line = ""
            pcts = []

            for r in rows:
                rec = r.get("record", {})
                try:
                    w, l = float(rec.get("w")), float(rec.get("l"))
                    pcts.append((w / (w + l), _subject(r)))
                except (TypeError, ValueError):
                    pass

            if len(pcts) == len(rows) and len(rows) > 1:
                distinct = {p for p, _ in pcts}
                best_pct, best_team = max(pcts)

                if len(distinct) > 1:
                    result_line = (
                        f"Result: The {best_team} had the better record "
                        f"({round(best_pct * 100, 1)}% wins)."
                    )
                else:
                    result_line = (
                        "Result: They finished with identical records."
                    )
            return _table_box(
                (
                    f"⚔️ {names[0]} vs {names[1]}"
                    if len(names) > 1
                    else "⚔️ Team Comparison"
                ),
                headers,
                data_rows,
                footer=[result_line] if result_line else None,
            )

        # --------------------------------------------------------
        # SUMMARY CARD (single team-season)
        # --------------------------------------------------------
        r = rows[0]
        rec = r.get("record", {})
        name = _subject(r) or rec.get("team")

        if rec.get("w") in (None, "", "nan"):
            return (
                f"I found the {name} franchise but couldn't retrieve a "
                "record for that season."
            )

        w, l = _num(rec.get("w")), _num(rec.get("l"))

        try:
            win_pct_txt = f"{round(float(rec.get('w')) / (float(rec.get('w')) + float(rec.get('l'))) * 100, 1)}%"
        except (TypeError, ValueError, ZeroDivisionError):
            win_pct_txt = "N/A"

        mov_raw = rec.get("mov")

        try:
            mov_f = float(mov_raw)
            mov_txt = (
                f"+{round(mov_f, 1)}" if mov_f > 0 else str(round(mov_f, 1))
            )
        except (TypeError, ValueError):
            mov_txt = "N/A"

        playoffs = _clean(rec.get("playoffs"))

        lines = [
            ("Record", f"{w}–{l}"),
            ("Win %", win_pct_txt),
            ("Point Diff.", mov_txt),
        ]

        if _clean(rec.get("o_rtg")):
            lines.append(("Off Rating", _num(rec.get("o_rtg"))))

        if _clean(rec.get("d_rtg")):
            lines.append(("Def Rating", _num(rec.get("d_rtg"))))

        if _clean(rec.get("pace")):
            lines.append(("Pace", _num(rec.get("pace"))))

        season = _clean(rec.get("season"))

        footer = None

        if playoffs:

            footer = (
                f"📈 Season Result: reached the {playoffs}"
                if len(playoffs) > 4 and not playoffs.isdigit()
                else "📈 Made the playoffs."
            )

        return _box(
            f"🏀 {name} — {season}" if season else f"🏀 {name}",
            lines,
            footer=footer,
        )

    # ============================================================
    # STATTABLE / COMPARISON: team_stat (team_season_stats /
    # compare_teams numeric path)
    # ============================================================
    if kind == "team_stat":
        rows_out = result["rows"]
        stat = result.get("stat")

        pretty = _pretty_stat(stat)

        # --------------------------------------------------------
        # COMPARISON TABLE (two teams)
        # --------------------------------------------------------
        if len(rows_out) > 1:

            a, b = rows_out[0], rows_out[1]
            headers = ["Statistic", a["team"], b["team"]]
            data_rows = [
                [
                    pretty,
                    _stat_value(stat, a["value"]),
                    _stat_value(stat, b["value"]),
                ]
            ]

            ctx_a = {c["label"]: c["value"] for c in (a.get("context") or [])}
            ctx_b = {c["label"]: c["value"] for c in (b.get("context") or [])}

            for label in ctx_a:
                if (
                    label in ctx_b
                    and label != pretty
                    and not (
                        _same_val(ctx_a[label], a["value"])
                        and _same_val(ctx_b[label], b["value"])
                    )
                ):
                    data_rows.append(
                        [label, _fmt(ctx_a[label]), _fmt(ctx_b[label])]
                    )

            # Record rows when available.
            rec_rows = {}

            for idx, r in enumerate((a, b)):
                rec = r.get("record") or {}
                if rec.get("w") not in (None, "", "nan"):
                    rec_rows[idx] = rec

            if len(rec_rows) == 2:
                data_rows.append(
                    [
                        "Wins",
                        _num(rec_rows[0].get("w")),
                        _num(rec_rows[1].get("w")),
                    ]
                )
                data_rows.append(
                    [
                        "Losses",
                        _num(rec_rows[0].get("l")),
                        _num(rec_rows[1].get("l")),
                    ]
                )

            season_txt = _clean(a.get("season")) or ""
            title = f"⚔️ {a['team']} vs {b['team']}" + (
                f" — {season_txt}" if season_txt else ""
            )

            verdict = _verdict(a, b, stat)
            record_note = _record_result_line(a, b)

            if record_note.startswith("Result: "):
                record_note = "📊 " + record_note[len("Result: ") :]

            return _table_box(title, headers, data_rows, footer=[verdict]) + (
                "\n" + record_note if record_note else ""
            )

        # --------------------------------------------------------
        # TEAM STATISTICS TABLE (single team)
        # --------------------------------------------------------
        r = rows_out[0]
        primary_val = r["value"]
        data_rows = [(pretty, _stat_value(stat, primary_val))]

        for c in r.get("context") or []:
            if c["label"] == pretty:
                continue

            if any(
                _same_val(c["value"], existing_val)
                for _, existing_val in [(pretty, primary_val)]
                + [(lab, val) for lab, val in data_rows[1:]]
            ):
                continue

            data_rows.append((c["label"], _fmt(c["value"])))

        rec = r.get("record") or {}

        if rec.get("w") not in (None, "", "nan"):

            data_rows.append(("Wins", _num(rec.get("w"))))
            data_rows.append(("Losses", _num(rec.get("l"))))

            if _clean(rec.get("playoffs")):
                data_rows.append(
                    ("Playoffs", _playoffs_txt(rec.get("playoffs")))
                )

            if _clean(rec.get("pace")):
                data_rows.append(("Pace", _num(rec.get("pace"))))

        return _box(f"🏀 {r['team']} — {_fmt(r.get('season'))}", data_rows)

    # ============================================================
    # DEFENSIVE TABLE: team_opponent_stats
    # ============================================================
    if kind == "team_opponent_stat":
        pretty = _pretty_stat(result.get("stat"))
        pretty = f"Opponent {pretty}"
        context = result.get("context") or []
        data_rows = [
            (c["label"].replace("Opp ", ""), _fmt(c["value"])) for c in context
        ]

        # Ensure the requested stat leads.
        primary_val = _stat_value(result.get("stat"), result.get("value"))
        ordered = [(pretty.replace("Opponent ", ""), primary_val)]

        for lab, val in data_rows:
            if any(_same_val(val, existing) for _, existing in ordered):
                continue

            ordered.append((lab, val))

        return _box(
            f"🛡️ {result['team']} — Opponent Stats ({_fmt(result.get('season'))})",
            ordered,
            subtitle="Per-game averages allowed to opponents",
        )

    # ============================================================
    # AWARDTABLE: player_awards
    # ============================================================
    if kind == "award_winner":
        rows_won = result.get("rows", [])

        if not rows_won:
            return "I could not find an award winner for that query."

        first = rows_won[0]
        award = _pretty_award(first.get("award"))
        season = _clean(first.get("season"))

        winners = [
            f"{_clean(w.get('player'))} (share {_share(w.get('share'))})"
            for w in rows_won
        ]

        body = "\n".join(winners)

        return f"🏆 {season} {award}\n{body}"

    if kind == "player_awards":
        rows_awarded = result.get("rows", [])

        if not rows_awarded:
            return (
                "I couldn't find an award record matching that player and "
                "season combination."
            )

        player = rows_awarded[0].get("player")
        winners = [
            r
            for r in rows_awarded
            if str(r.get("winner")).lower() in {"true", "1", "yes"}
        ]

        # --------------------------------------------------------
        # AwardTable grouped by award with win counts + years.
        # --------------------------------------------------------
        if winners:
            groups: dict[str, list[str]] = {}
            order: list[str] = []

            for w in winners:
                label = _pretty_award(w.get("award"))

                if label not in groups:
                    groups[label] = []
                    order.append(label)

                groups[label].append(_clean(w.get("season")))

            lines = []

            for label in sorted(order, key=lambda x: -len(groups[x])):
                years = sorted(groups[label])
                year_txt = ", ".join(years[:6]) + (
                    f" …+{len(years) - 6} more" if len(years) > 6 else ""
                )
                lines.append((f"{label} ×{len(years)}", year_txt))

            return _box(f"🏆 {player} — Awards", lines)

        # No wins: show voting appearances instead.

        share_lines = [
            (
                f"{_pretty_award(r.get('award'))} {_clean(r.get('season'))}",
                f"share {_num(r.get('share'))}",
            )
            for r in rows_awarded[:6]
        ]

        return _box(
            f"🗳️ {player} — Award Voting",
            share_lines,
            footer="No outright wins found in these records.",
        )

    # ============================================================
    # ALL-STAR SELECTIONS (3 shapes)
    # ============================================================
    if kind == "all_star_selection":
        rows_as = result.get("rows", [])
        total = result.get("total", len(rows_as))

        if not rows_as:
            return (
                "I could not find an All-Star selection for that player "
                "and season combination."
            )

        distinct = result.get("distinct_players") or len(
            {r.get("player") for r in rows_as}
        )

        # --------------------------------------------------------
        # C. Roster list (a whole season was asked about)
        # --------------------------------------------------------
        if distinct > 1:
            season = _clean(rows_as[0].get("season"))
            mode = result.get("roster_mode") or "played"
            appeared = result.get("appeared") or []
            injured = result.get("injured") or []
            pairs = result.get("replacement_pairs") or []
            selected = result.get("players") or sorted(
                {str(r.get("player")) for r in rows_as}
            )

            if mode == "replacements":
                parts: list[str] = []
                if pairs:
                    parts.append("Injury replacements:")
                    parts += [f"{a_} replaced {b_}" for a_, b_ in pairs]

                if injured:
                    parts.append(
                        "Missed the game through injury: " + ", ".join(injured)
                    )

                if not pairs:
                    parts.append(
                        "The dataset marks which selections "
                        "missed the game but does not record "
                        "who replaced them."
                    )

                return (
                    f"⭐ {season} All-Star — injury replacements\n"
                    + "\n".join(parts)
                )

            shown = selected if mode == "selected" else appeared
            shown = shown or selected
            header = (
                f"⭐ {season} All-Star Roster "
                f"({len(shown)} players appeared in the game)"
            )

            if mode == "selected":
                header = (
                    f"⭐ {season} All-Star Roster "
                    f"({len(shown)} players were originally "
                    f"selected)"
                )

            grid = _two_col_grid(shown, "")
            text = header + "\n" + grid

            if mode == "selected" and injured:
                text += "\n\n🚑 Injured, did not play: " + ", ".join(injured)

            return text

        player = rows_as[0].get("player")
        seasons_list = result.get("years") or sorted(
            {
                str(int(s)) if str(s).isdigit() else str(s)
                for s in (r.get("season") for r in rows_as)
            }
        )

        # --------------------------------------------------------
        # B. Career selection summary
        # --------------------------------------------------------
        if len(seasons_list) > 1:

            years_txt = ", ".join(seasons_list[:14]) + (
                f" …+{len(seasons_list) - 14} more"
                if len(seasons_list) > 14
                else ""
            )

            return _box(
                f"⭐ {player} — All-Star Selections",
                [
                    ("Total selections", total),
                    ("First", seasons_list[0]),
                    ("Latest", seasons_list[-1]),
                    ("Years", years_txt),
                ],
            )

        # --------------------------------------------------------
        # A. Yes/no single season
        # --------------------------------------------------------
        first = rows_as[0]

        team_raw = _clean(first.get("team"))
        team_display = ""

        if team_raw:
            team_display = (
                team_raw
                if team_raw.lower().startswith("team ")
                else _clean(first.get("team_name")) or team_raw
            )

        status, replaced_name = _asg_status(first)

        asked_played = any(
            w in (query_text or "").casefold()
            for w in ("play", "appear", "participat")
        )

        detail_lines = []

        if team_display:
            detail_lines.append(("Team", team_display))

        if status == "out":
            if asked_played:
                detail_lines.append(("Played", "❌ No"))
                detail_lines.append(
                    ("Reason", "Injured — selected but did not appear")
                )
            else:
                detail_lines.append(("Selected", "✅ Yes"))
                detail_lines.append(("Played", "❌ No (injured)"))

        elif status == "in_for":
            detail_lines.append(("Selected", "✅ Yes"))
            detail_lines.append(("Played", "✅ Yes"))
            detail_lines.append(("Entered as replacement for", replaced_name))
        else:
            key = "Played" if asked_played else "Selected"
            detail_lines.append((key, "✅ Yes"))

        return _box(
            f"⭐ {_fmt(first.get('season'))} All-Star",
            detail_lines,
            subtitle=player,
        )

    # ============================================================
    # INFOCARD: draft_information
    # ============================================================
    if kind == "draft_information":
        draft_rows = result.get("rows", [])
        total = result.get("total", len(draft_rows))

        if not draft_rows:
            return (
                "I couldn't find a draft record for that player and season "
                "combination."
            )

        # ---- Full draft overview (text) ----

        if result.get("overview"):
            season = _fmt(draft_rows[0].get("season"))
            parts = [f"🎓 {season} NBA Draft"]
            by_round: dict[int, list] = {}

            for rec in draft_rows:
                rnd = int(float(rec.get("round") or 1))
                by_round.setdefault(rnd, []).append(rec)

            for rnd in sorted(by_round):
                label = (
                    "First Round"
                    if rnd == 1
                    else ("Second Round" if rnd == 2 else f"Round {rnd}")
                )

                parts.append("")
                parts.append(label + ":")
                parts += [
                    f"#{int(float(rec['overall_pick']))} "
                    f"{rec.get('player')} "
                    f"({_clean(rec.get('franchise')) or _clean(rec.get('tm'))})"
                    for rec in by_round[rnd]
                ]

            return "\n".join(parts)

        # ---- Single pick (text) ----
        if result.get("single_pick"):
            rec = draft_rows[0]
            team_txt = _clean(rec.get("franchise")) or _clean(rec.get("tm"))

            return (
                f"🎓 {_fmt(rec.get('season'))} NBA Draft\n\n"
                f"#{int(result['single_pick'])} Overall Pick: "
                f"{rec.get('player')}\n"
                f"{team_txt}"
            )

        d = draft_rows[0]

        round_raw = _clean(d.get("round"))
        round_n = None

        if round_raw is not None:
            try:
                round_n = _ordinal(round_raw)
            except (TypeError, ValueError):

                round_n = round_raw

        lines = [
            ("Draft year", _fmt(d.get("season"))),
            ("Round", f"{round_n}" if round_n else "N/A"),
            ("Pick", f"{_ordinal(d.get('overall_pick'))} overall"),
            (
                "Drafted by",
                _clean(d.get("franchise")) or _clean(d.get("tm")) or "N/A",
            ),
            ("College", _clean(d.get("college")) or "N/A"),
        ]

        footer = None

        if total > 1:
            footer = f"Highest selection among {total} draft entries found."
        return _box(
            f"🎓 {_fmt(d.get('player'))} — Draft", lines, footer=footer
        )

    # ============================================================
    # AWARDCARD: end_of_season_team
    # ============================================================
    if kind == "end_of_season_team":
        honor_rows = result.get("rows", [])

        if not honor_rows:
            return (
                "I could not find an end-of-season team selection for that "
                "player and season combination."
            )

        tier_words = {"1st": "First", "2nd": "Second", "3rd": "Third"}

        lines = []
        for r in honor_rows[:5]:

            team_type = _clean(r.get("type")) or "end-of-season"
            tier = _clean(r.get("number_tm"))
            position = _clean(r.get("position"))

            piece = (
                f"{team_type} {tier_words.get(tier, tier)} Team"
                if tier
                else team_type
            )

            if position:
                piece += f" ({position})"

            lines.append(("🏅", piece.strip()))

        season = _clean(honor_rows[0].get("season"))

        return _box(
            f"🏅 {_fmt(honor_rows[0].get('player'))} — Honors",
            lines,
            subtitle=f"{season} season" if season else None,
        )

    # ============================================================
    # FALLBACK
    # ============================================================
    return (
        "I found some information but do not have a polished way to present "
        "it yet - could you rephrase your question?"
    )


def _record_result_line(a: dict[str, Any], b: dict[str, Any]) -> str:
    """Append a records-based result note for team comparisons."""
    rec_a = a.get("record") or {}
    rec_b = b.get("record") or {}

    try:
        pa = float(rec_a.get("w")) / (
            float(rec_a.get("w")) + float(rec_a.get("l"))
        )
        pb = float(rec_b.get("w")) / (
            float(rec_b.get("w")) + float(rec_b.get("l"))
        )
    except (TypeError, ValueError, ZeroDivisionError):
        return ""

    if abs(pa - pb) < 1e-9:
        return "📊 Both teams finished with identical records."

    leader = a if pa > pb else b

    return (
        f"Result: The {leader['team']} had the better record "
        f"({round(max(pa, pb) * 100, 1)}% wins)."
    )


# ============================================================
# RICH CARD CONTENT (Streamlit chat UI)
# ============================================================
#
# Builds the card payload consumed by webhook.process_message,
# which turns it into {'rich': rows, 'text': bubble} for the
# /chat endpoint and the Streamlit front end:
#
#   [ {'text': {'text': [short_line]}},                 <- bubble
#     {'payload': {'richContent': [row1, row2]}} ]      <- card + chips
#
# Supported row types used here: info, description, chips.
# ============================================================
def _info(title: str, subtitle: str | None = None) -> dict[str, Any]:
    card: dict[str, Any] = {"type": "info", "title": title}
    if subtitle:
        card["subtitle"] = subtitle

    return card


def _desc(lines: list[Any], title: str | None = None) -> dict[str, Any]:
    text_lines = [str(line) if line is not None else "" for line in lines]
    card: dict[str, Any] = {"type": "description", "text": text_lines}

    if title:
        card["title"] = title

    return card


def _asg_status(row: dict) -> tuple[str, str]:
    """
    All-Star 'replaced' column semantics:
      ('out', '')     picked but injured -> did NOT play
      ('in_for', X)   injury replacement who played
                      (entered for X)
      ('normal', '')  picked and played
    """
    v = row.get("replaced")
    t = str(v).strip()

    if t.lower() in ("true", "1"):
        return ("out", "")
    if t.lower() in ("", "false", "none", "nan"):
        return ("normal", "")
    return ("in_for", t)


def _chips(labels: list[str]) -> dict[str, Any] | None:
    options = [{"text": label} for label in labels[:6] if label]

    if not options:
        return None
    return {"type": "chips", "options": options}


def _stat_row(label: str, value: Any) -> str:
    return f"{label}: {_fmt(value)}"


def _build_rich(
    result: dict[str, Any], intent: str, query_text: str
) -> list[list[dict[str, Any]]]:
    """
    Return richContent rows (list of rows; each row is a list of
    widgets rendered side by side / stacked in the chat card).
    """
    kind = result.get("kind")

    # --------------------------------------------------------
    # GREETING / GOODBYE
    # --------------------------------------------------------
    if intent == "greeting":
        row = [
            _desc(
                [
                    "Your NBA knowledge assistant.",
                    "",
                    "I can help you with:",
                    "👤 Players      📊 Statistics",
                    "🏀 Teams        🏆 Awards",
                    "🎓 Drafts       ⭐ All-Stars",
                ],
                title="👋 Welcome to HoopMind!",
            )
        ]
        chips = _chips(
            [
                "Tell me about LeBron James",
                "Stephen Curry stats in 2016",
                "Celtics record in 2024",
                "Compare Kobe and Jordan",
            ]
        )
        return [row + ([chips] if chips else [])]

    if intent == "goodbye":
        return [
            [
                _desc(
                    ["Come back anytime for more NBA information. 🏀"],
                    title="👋 Thanks for using HoopMind!",
                )
            ]
        ]

    # --------------------------------------------------------
    # DATASET SCOPE
    # --------------------------------------------------------
    if kind == "dataset_scope":
        datasets = result.get("datasets", [])
        row = [
            _desc(
                [
                    "I can provide information about:",
                    "",
                    "👤 NBA Players (profiles & careers)",
                    "📊 Player statistics (season, advanced,",
                    "   shooting, per-36, per-100, play-by-play)",
                    "🏀 Teams (records, season stats, defense)",
                    "🏆 Awards & All-Star selections",
                    "🎓 Draft history",
                    f"📅 Seasons covered across " f"{len(datasets)} datasets",
                ],
                title="📚 HoopMind Data",
            )
        ]
        chips = _chips(
            [
                "What statistics can you provide?",
                "Player stats",
                "Team stats",
                "Awards",
            ]
        )

        return [row + ([chips] if chips else [])]

    # --------------------------------------------------------
    # LEAGUE INFO
    # --------------------------------------------------------
    if kind == "league_information":
        if result.get("player_leagues"):
            leagues = result["player_leagues"]
            name = result.get("player")
            span = result.get("span")
            lines = [
                f"{' and '.join(leagues)}" + (f" ({span})" if span else "")
            ]

            if "ABA" in leagues and "NBA" in leagues:
                lines.append("")
                lines.append(
                    "Played in both the NBA and ABA" " before the 1976 merger."
                )

            return [[_info(f"🌎 {name}", "League History"), _desc(lines)]]

        if result.get("topic") == "league_compare":
            return [
                [
                    _desc(
                        [
                            "NBA",
                            "- Founded: 1946 (as BAA)",
                            "- Today's major professional league",
                            "",
                            "ABA",
                            "- Founded: 1967",
                            "- Merged into the NBA in 1976",
                            "",
                            "HoopMind data covers both leagues"
                            " where noted.",
                        ],
                        title="🏀 NBA vs ABA",
                    )
                ]
            ]

        league = result.get("league", "NBA")

        return [
            [
                _desc(
                    [
                        f"HoopMind currently covers {league} history "
                        "from the first season through recent seasons,",
                        "spanning player, team and awards data.",
                    ],
                    title=f"🌎 {league} coverage",
                )
            ]
        ]

    # --------------------------------------------------------
    # PLAYER PROFILE (info + description + chips)
    # --------------------------------------------------------
    if kind == "player_information":
        r = result["row"]
        name = r.get("player") or "Player"
        pos = str(_clean(r.get("pos")) or "").replace("-", "/")
        lines = []
        height = _feet_inches(r.get("ht_in_in"))

        if pos:
            lines.append(_stat_row("Position", pos))
        if height:
            try:
                cm = round(float(r.get("ht_in_in")) * 2.54)
                height = f"{height} ({cm} cm)"
            except (TypeError, ValueError):
                pass

            lines.append(_stat_row("Height", height))

        if _clean(r.get("wt")):
            try:
                kg = round(float(_num(r.get("wt"))) * 0.45359237)
                weight = f"{_num(r.get('wt'))} lb ({kg} kg)"
            except (TypeError, ValueError):
                weight = f"{_num(r.get('wt'))} lb"

            lines.append(_stat_row("Weight", weight))

        if _clean(r.get("birth_date")):
            lines.append(_stat_row("Born", r.get("birth_date")))

        colleges = _clean(r.get("colleges"))

        if colleges:
            lines.append(_stat_row("College", colleges))

        if r.get("from") and r.get("to"):
            lines.append(
                _stat_row(
                    "Career", f"{_num(r.get('from'))} - {_num(r.get('to'))}"
                )
            )

        lines.append(
            (
                "Hall of Fame"
                if str(r.get("hof")).lower() != "true"
                else "Hall of Fame 🏆"
            )
            + ": "
            + ("Yes" if str(r.get("hof")).lower() == "true" else "No")
        )

        cards = [
            _info(f"👤 {name}", pos or None),
            _desc(lines, title="Player Profile"),
        ]

        chips = _chips(
            [
                f"Career totals of {name}",
                f"Awards of {name}",
                f"Draft info of {name}",
            ]
        )

        if chips:
            cards.append(chips)

        return [cards]

    # --------------------------------------------------------
    # PLAYER STATS FAMILY
    # --------------------------------------------------------
    if kind == "player_stat":
        stat_rows = result["rows"]
        stat = result.get("stat")
        measure = result.get("measure")
        dataset = result.get("dataset", "")

        pretty = _pretty_stat(stat, dataset)

        dataset_label = DATASET_LABELS.get(dataset)

        # -------- comparison --------

        if len(stat_rows) > 1:
            a, b = stat_rows[0], stat_rows[1]

            name_a = a.get("player") or "Player A"
            name_b = b.get("player") or "Player B"

            # ------------------------------------------------
            # One labelled section per statistic, values as
            # bullets. Survives the narrow chat card,
            # unlike 'X: 1 vs 2 | Y: 3 vs 4' pipe rows.
            # ------------------------------------------------

            # ------------------------------------------------
            # A NAMED statistic ('scoring', 'rebounds') shows
            # ONLY that stat; a generic 'Compare X and Y'
            # gets the full head-to-head table.
            # ------------------------------------------------

            focused = bool(result.get("stat_requested"))

            blocks = [
                [
                    pretty,
                    f"• {name_a}: {_stat_value(stat, a['value'])}",
                    f"• {name_b}: {_stat_value(stat, b['value'])}",
                ]
            ]

            ctx_a = {c["label"]: c["value"] for c in (a.get("context") or [])}
            ctx_b = {c["label"]: c["value"] for c in (b.get("context") or [])}

            for label in ([] if focused else ctx_a):
                if (
                    label in ctx_b
                    and label != pretty
                    and not (
                        _same_val(ctx_a[label], a["value"])
                        and _same_val(ctx_b[label], b["value"])
                    )
                ):
                    blocks.append(
                        [
                            label,
                            f"• {name_a}: "
                            f"{_stat_value(label, ctx_a[label])}",
                            f"• {name_b}: "
                            f"{_stat_value(label, ctx_b[label])}",
                        ]
                    )

            lines: list = []

            for block in blocks:
                lines.extend(block)
                lines.append("")

            while lines and lines[-1] == "":
                lines.pop()

            verdict = _verdict(a, b, stat)
            footer_bits = []

            if measure == "career totals":
                footer_bits.append("Based on career totals.")
            elif result.get("mode") == "best_season":
                footer_bits.append("Each team's best season used.")
            elif not result.get("season_requested", True):
                footer_bits.append("Latest recorded season used.")
            cards = [
                _info(f"⚔️ {name_a} vs {name_b}", "Player Comparison"),
                _desc(lines, title="Head-to-head"),
            ]

            if footer_bits:
                cards.append(_desc(footer_bits))
            cards.append(_desc([f"🏆 {verdict}"]))

            return [cards]

        # -------- single player --------
        r = stat_rows[0]

        team = _clean(r.get("team_name") or _clean(r.get("team")))
        games = r.get("g")
        age = _num(_clean(r.get("age")))
        season_txt = _clean(r.get("season")) or "Career"

        subtitle_parts = []

        if team:
            subtitle_parts.append(team)
        if dataset_label and dataset_label != "Career Totals":
            subtitle_parts.append(dataset_label)

        # Mini card: one requested statistic.

        if result.get("stat_requested") and result.get("season_requested"):

            value = _stat_value(stat, r["value"])

            lines = [pretty]
            lines.append("")
            lines.append(f"⭐ {value}")

            if measure == "career totals":
                lines.insert(0, "(career totals)")

            footer = []

            if games is not None:
                footer.append(f"Games: {games}")
            if age:
                footer.append(f"Age: {age}")

            cards = [
                _info(
                    f"📊 {r.get('player')} - {season_txt}",
                    ", ".join(subtitle_parts) or None,
                ),
                _desc(lines),
            ]
            if footer:
                cards.append(_desc(["  •  ".join(footer)]))

            chips = _chips(
                [
                    f"All stats of {r.get('player')} in {season_txt}",
                    f"Career totals of {r.get('player')}",
                ]
            )

            if chips:
                cards.append(chips)

            return [cards]

        # Full statistics table.
        context = r.get("context") or []
        lines = []
        primary_label = pretty if result.get("stat_requested") else None

        for c in context:
            prefix = (
                "★ "
                if (
                    primary_label
                    and c["label"] == primary_label.replace("★ ", "")
                )
                else ""
            )
            lines.append(
                f"{prefix}{c['label']}: "
                f"{_stat_value(c['label'], c['value'])}"
            )

        if not lines:
            lines = [f'{pretty}: {_stat_value(stat, r["value"])}']

        footer_bits = []

        if team:
            footer_bits.append(f"Team: {team}")
        if games is not None:
            footer_bits.append(f"Games: {games}")
        if measure == "career totals":
            footer_bits.append("Career totals")

        cards = [
            _info(
                f"📊 {r.get('player')} - {season_txt}",
                ", ".join(subtitle_parts) or None,
            ),
            _desc(lines, title="Statistics"),
        ]

        if footer_bits:
            cards.append(_desc(["  •  ".join(footer_bits)]))

        return [cards]

    # --------------------------------------------------------
    # CAREER TOTALS
    # --------------------------------------------------------
    if kind == "player_career_total":
        name = result.get("player")
        stat = result.get("stat")

        if result.get("stat_requested"):
            footer_bits = []
            if result.get("span"):
                footer_bits.append(f"Career span: {result.get('span')}")

            teams_count = result.get("teams_count")

            if teams_count is not None and teams_count > 0:
                footer_bits.append(f"Teams: {teams_count}")

            cards = [
                _info(f"👑 {name}", f"Career {_pretty_stat(stat)}"),
                _desc(
                    [
                        _pretty_stat(stat),
                        "",
                        f'⭐ {_thousand(result.get("value"))}',
                    ]
                ),
            ]

            if footer_bits:
                cards.append(_desc(["  •  ".join(footer_bits)]))

            chips = _chips([f"All career totals of {name}"])

            if chips:
                cards.append(chips)

            return [cards]

        context = result.get("context") or []
        lines = [f"{c['label']}: {_thousand(c['value'])}" for c in context]
        footer = f"Seasons played: {result.get('seasons')}"

        if result.get("span"):
            footer += f" ({result.get('span')})"

        return [
            [
                _info(f"👑 {name}", "Career Totals"),
                _desc(lines, title="All-time totals"),
                _desc([footer]),
            ]
        ]

    # --------------------------------------------------------
    # AWARDS
    # --------------------------------------------------------
    if kind == "award_winner":
        winners = result.get("rows", [])
        first = winners[0]
        award = _pretty_award(first.get("award"))
        season = _clean(first.get("season"))
        lines = [
            f"{_clean(w.get('player'))} " f"(share {_share(w.get('share'))})"
            for w in winners
        ]

        return [[_info(f"🏆 {season} {award}"), _desc(lines)]]

    if kind == "player_awards":
        rows_awarded = result.get("rows", [])

        if not rows_awarded:
            return [
                [
                    _desc(
                        [
                            "Couldn't find an award record for that "
                            "player/season."
                        ]
                    )
                ]
            ]

        player_name = rows_awarded[0].get("player")

        winners = [
            r
            for r in rows_awarded
            if str(r.get("winner")).lower() in {"true", "1", "yes"}
        ]

        if winners:
            groups: dict[str, list[str]] = {}
            order: list[str] = []

            for w in winners:

                label = _pretty_award(w.get("award"))

                if label not in groups:
                    groups[label] = []
                    order.append(label)

                groups[label].append(str(_clean(w.get("season"))))

            lines = []

            for label in sorted(order, key=lambda x: -len(groups[x])):
                years = sorted(groups[label])
                year_txt = ", ".join(years[:6])

                if len(years) > 6:
                    year_txt += f" +{len(years) - 6} more"

                lines.append(f"{label} x{len(years)}: {year_txt}")

            return [[_info(f"🏆 {player_name}", "Awards"), _desc(lines)]]

        share_lines = [
            (
                f"{_pretty_award(r.get('award'))} "
                f"{_clean(r.get('season'))}: "
                f'share {_share(r.get("share"))}'
            )
            for r in rows_awarded[:6]
        ]
        return [
            [
                _info(f"🗳️ {player_name}", "Award voting"),
                _desc(share_lines),
                _desc(["No outright wins found in these records."]),
            ]
        ]

    # --------------------------------------------------------
    # ALL-STAR (three shapes)
    # --------------------------------------------------------
    if kind == "all_star_selection":

        rows_as = result.get("rows", [])
        total = result.get("total", len(rows_as))

        if not rows_as:
            return [
                [
                    _desc(
                        [
                            "No All-Star selection found for that "
                            "player/season."
                        ]
                    )
                ]
            ]

        distinct = result.get("distinct_players") or len(
            {r.get("player") for r in rows_as}
        )

        # Roster grid -> description lines.

        if distinct > 1:

            season = _clean(rows_as[0].get("season"))
            mode = result.get("roster_mode") or "played"
            appeared = result.get("appeared") or []
            injured = result.get("injured") or []
            pairs = result.get("replacement_pairs") or []
            selected = result.get("players") or sorted(
                {str(r.get("player")) for r in rows_as}
            )

            # --------------------------------------------
            # Three roster readings:
            #   played       -> actual participants
            #   selected     -> original picks + injury notes
            #   replacements -> who missed / who stepped in
            # --------------------------------------------
            if mode == "replacements":

                lines: list[str] = []

                if pairs:
                    lines.append("Injury replacements:")
                    lines += [f"• {a_} replaced {b_}" for a_, b_ in pairs]
                    lines.append("")

                if injured:
                    lines.append("Missed the game through injury:")
                    lines += [f"• {p}" for p in injured]

                if not pairs:
                    lines.append(
                        "The dataset marks which selections "
                        "missed the game but does not record "
                        "who replaced them."
                    )
                return [
                    [
                        _info(f"⭐ {season} All-Star", "Injury replacements"),
                        _desc(lines),
                    ]
                ]

            shown = (selected if mode == "selected" else appeared) or selected

            subtitle = (
                f"{len(shown)} players were originally selected"
                if mode == "selected"
                else (f"{len(shown)} players appeared in the game")
            )

            lines = [", ".join(shown)]

            if mode == "selected" and injured:
                lines.append("")
                lines.append("🚑 Injured, did not play: " + ", ".join(injured))

            return [
                [_info(f"⭐ {season} All-Star Roster", subtitle), _desc(lines)]
            ]

        player = rows_as[0].get("player")

        seasons_list = result.get("years") or sorted(
            {
                str(int(s)) if str(s).isdigit() else str(s)
                for s in (r.get("season") for r in rows_as)
            }
        )

        # Career selections.
        if len(seasons_list) > 1:
            years_txt = ", ".join(seasons_list[:14])

            if len(seasons_list) > 14:
                years_txt += f" +{len(seasons_list) - 14} more"

            return [
                [
                    _info(f"⭐ {player}", "All-Star Selections"),
                    _desc(
                        [
                            f"⭐ {total}",
                            "selections",
                            "",
                            f"First: {seasons_list[0]}   "
                            f"Latest: {seasons_list[-1]}",
                            years_txt,
                        ]
                    ),
                ]
            ]

        # Yes/no single season.
        first = rows_as[0]

        team_raw = _clean(first.get("team"))
        team_display = ""

        if team_raw:
            team_display = (
                team_raw
                if team_raw.lower().startswith("team ")
                else _clean(first.get("team_name")) or team_raw
            )

        status, replaced_name = _asg_status(first)

        asked_played = any(
            w in (query_text or "").casefold()
            for w in ("play", "appear", "participat")
        )

        lines: list[str] = []

        if status == "out":

            if asked_played:
                lines.append("❌ NO")
                lines.append("Injured — selected but did not play")
            else:
                lines.append("✅ YES (selected)")
                lines.append("❌ Did not play (injured)")

        elif status == "in_for":
            lines.append("✅ YES")
            lines.append(
                f"Entered as injury replacement for " f"{replaced_name}"
            )
        else:
            key = "Played" if asked_played else "Selected"
            lines.append(f"{key}: ✅ YES")

        if team_display:
            lines.append(f"Team: {team_display}")

        return [
            [
                _info(f"⭐ {_fmt(first.get('season'))} All-Star", player),
                _desc(lines),
            ]
        ]

    # --------------------------------------------------------
    # END OF SEASON TEAMS (All-NBA etc.)
    # --------------------------------------------------------
    if kind == "end_of_season_team":

        honor_rows = result.get("rows", [])

        if not honor_rows:
            return [
                [
                    _desc(
                        [
                            "No end-of-season team selection found for that "
                            "player/season."
                        ]
                    )
                ]
            ]

        tier_words = {
            "1st": "First Team",
            "2nd": "Second Team",
            "3rd": "Third Team",
        }

        lines = []

        for r in honor_rows[:5]:
            team_type = _clean(r.get("type")) or "end-of-season"
            tier = _clean(r.get("number_tm"))
            position = _clean(r.get("position"))
            piece = (
                f"{team_type} {tier_words.get(tier, tier)}"
                if tier
                else team_type
            )

            if position:
                piece += f" ({position})"

            lines.append(f"⭐ {piece.strip()}")

        season = _clean(honor_rows[0].get("season"))

        return [
            [
                _info(
                    f"🏆 {_fmt(honor_rows[0].get('player'))}"
                    + (f" - {season}" if season else ""),
                    "End-of-Season Honors",
                ),
                _desc(lines),
            ]
        ]

    # --------------------------------------------------------
    # DRAFT
    # --------------------------------------------------------
    if kind == "draft_information":

        draft_rows = result.get("rows", [])

        if not draft_rows:

            return [
                [
                    _desc(
                        [
                            "Couldn't find a draft record for that "
                            "player/season."
                        ]
                    )
                ]
            ]

        d = draft_rows[0]
        round_raw = _clean(d.get("round"))
        round_n = None

        if round_raw is not None:
            try:
                round_n = _ordinal(round_raw)
            except (TypeError, ValueError):
                round_n = round_raw

        pick = _ordinal(d.get("overall_pick"))

        # ---- Single pick card ----
        if result.get("single_pick"):
            rec = draft_rows[0]
            team_txt = _clean(rec.get("franchise")) or _clean(rec.get("tm"))

            return [
                [
                    _info(f"🎓 {_fmt(rec.get('season'))} NBA Draft"),
                    _desc(
                        [
                            f"#{int(result['single_pick'])} "
                            f"Overall Pick: {rec.get('player')}",
                            team_txt,
                        ]
                    ),
                ]
            ]

        # ---- Full draft overview ----
        if result.get("overview"):
            season = _fmt(draft_rows[0].get("season"))
            by_round: dict[int, list] = {}

            for rec in draft_rows:
                rnd = int(float(rec.get("round") or 1))
                by_round.setdefault(rnd, []).append(rec)

            cards = [
                _info(f"🎓 {season} NBA Draft", f"{len(draft_rows)} picks")
            ]

            for rnd in sorted(by_round):

                label = (
                    "🥇 First Round"
                    if rnd == 1
                    else ("🥈 Second Round" if rnd == 2 else f"Round {rnd}")
                )

                bullets = [
                    f"#{int(float(rec['overall_pick']))} "
                    f"{rec.get('player')} — "
                    f"{_clean(rec.get('franchise')) or _clean(rec.get('tm'))}"
                    for rec in by_round[rnd]
                ]

                cards.append(_desc(bullets, title=label))

            return [cards]

        # By-pick query (e.g. first overall pick of a year).
        if result.get("by_pick"):
            lines = []

            for rec in draft_rows:
                lines.append(
                    f"{_ordinal(rec.get('overall_pick'))}: "
                    f"{rec.get('player')} "
                    f"({rec.get('franchise') or rec.get('tm')})"
                )

            return [
                [
                    _info(
                        f"🎓 {_fmt(d.get('season'))} NBA Draft",
                        f'#1 Overall Pick: {d.get("player")}',
                    ),
                    _desc(lines[:5]),
                ]
            ]

        lines = [
            _stat_row("Draft year", d.get("season")),
            _stat_row("Round", round_n),
            _stat_row("Pick", f"{pick} overall"),
            _stat_row(
                "Drafted by", _clean(d.get("franchise")) or _clean(d.get("tm"))
            ),
            _stat_row("College", _clean(d.get("college"))),
        ]

        total = result.get("total", len(draft_rows))

        footer = None

        if total > 1:
            footer = f"Highest selection among {total} draft entries."

        cards = [
            _info(f"🎓 {_fmt(d.get('player'))}", "Draft Profile"),
            _desc(lines),
        ]

        if footer:
            cards.append(_desc([footer]))

        return [cards]

    # --------------------------------------------------------
    # TEAM INFORMATION (franchise profile)
    # --------------------------------------------------------
    if kind == "team_information":
        name = result.get("team", "Franchise")
        win_pct = result.get("win_pct")
        best = result.get("best_record", {})
        lines = [
            _stat_row("Abbreviation", result.get("abbreviation")),
            _stat_row("League", result.get("league")),
            _stat_row("First season", result.get("first_season")),
            _stat_row("Arena", _clean(result.get("arena"))),
            _stat_row("Seasons completed", result.get("seasons")),
            _stat_row(
                "All-time record",
                f"{_num(result.get('wins'))}-" f"{_num(result.get('losses'))}",
            ),
            _stat_row(
                "Win rate",
                (f"{round(win_pct * 100, 1)}%" if win_pct else "N/A"),
            ),
            _stat_row(
                "Playoff appearances", result.get("playoff_appearances")
            ),
            _stat_row(
                "Best season",
                (
                    f"{best.get('season')} "
                    f"({_num(best.get('w'))}-"
                    f"{_num(best.get('l'))})"
                    if best.get("season")
                    else "N/A"
                ),
            ),
        ]

        last = result.get("last_season_row") or {}

        if last.get("w") not in (None, "", "nan"):
            lines.append(
                f"Last season ({_fmt(last.get('season'))}): "
                f"{_num(last.get('w'))}-{_num(last.get('l'))}"
            )

        chips = _chips(
            [
                f"{name} latest season record",
                f"Compare {name} and " f"{_random_team(name)}",
            ]
        )

        cards = [_info(f"🏀 {name}"), _desc(lines)]

        if chips:
            cards.append(chips)

        return [cards]

    # --------------------------------------------------------
    # TEAM SUMMARY (single + compare)
    # --------------------------------------------------------
    if kind == "team_summary":
        rows_ts = result["rows"]

        if len(rows_ts) > 1:

            valid_rows = [
                r
                for r in rows_ts
                if r.get("record", {}).get("w") not in (None, "", "nan")
            ]

            headers_names = [_subject(r) or "?" for r in rows_ts[:2]]

            metric_map = [
                ("Record", "w", "l"),
                ("Point differential", "mov"),
                ("Offensive rating", "o_rtg"),
                ("Defensive rating", "d_rtg"),
                ("Pace", "pace"),
                ("Playoffs", "playoffs"),
            ]

            # --------------------------------------------
            # One description card per team with bullet
            # lines: space-aligned tables collapse in
            # the narrow chat card viewport.
            # --------------------------------------------
            cards = [
                _info(
                    "⚔️ Team Comparison",
                    headers_names[0] + " vs " + headers_names[1],
                )
            ]

            for i, r in enumerate(rows_ts[:2]):
                rec = r.get("record") or {}
                season_txt = _fmt(rec.get("season"))
                bullets: list[str] = []

                if season_txt:
                    bullets.append(f"• Season: {season_txt}")
                for metric in metric_map:
                    label = metric[0]

                    if len(metric) == 3:
                        value = (
                            f"{_num(rec.get(metric[1]))}-"
                            f"{_num(rec.get(metric[2]))}"
                        )

                        if value == "-":
                            continue
                    else:
                        raw = rec.get(metric[1])

                        if raw in (None, "", "nan"):
                            continue
                        if label == "Playoffs":
                            value = (
                                "Yes"
                                if str(raw).strip().lower()
                                in ("true", "1", "yes")
                                else "No"
                            )
                        elif (
                            label == "Point differential"
                            and str(raw)
                            .replace(".", "", 1)
                            .replace("-", "", 1)
                            .isdigit()
                        ):
                            value = f"{float(raw):+.1f}"
                        else:
                            value = _fmt(raw)

                    bullets.append(f"• {label}: {value}")

                if not bullets:
                    continue

                cards.append(_desc(bullets, title=headers_names[i]))

            result_note = _record_result_line(*rows_ts)

            if result.get("mode") == "best_season":

                cards.append(_desc(["Each team's best season used."]))

            if result_note:
                cards.append(_desc([f"🏆 {result_note}"]))

            return [cards]

        r = rows_ts[0]

        rec = r.get("record", {})
        name = _subject(r) or rec.get("team")

        if rec.get("w") in (None, "", "nan"):

            return [
                [_desc([f"Found the {name} but no record for that season."])]
            ]

        w, l = _num(rec.get("w")), _num(rec.get("l"))

        try:
            wp = float(rec.get("w")) / (
                float(rec.get("w")) + float(rec.get("l"))
            )
            win_pct_txt = f"{round(wp * 100, 1)}%"

        except (TypeError, ValueError, ZeroDivisionError):
            win_pct_txt = "N/A"
        try:
            mov_f = float(rec.get("mov"))

            mov_txt = (
                f"+{round(mov_f, 1)}" if mov_f > 0 else str(round(mov_f, 1))
            )

        except (TypeError, ValueError):

            mov_txt = "N/A"

        playoffs = _clean(rec.get("playoffs"))

        lines = [
            _stat_row("Record", f"{w} - {l}"),
            _stat_row("Win %", win_pct_txt),
            _stat_row("Point Diff.", mov_txt),
        ]

        if _clean(rec.get("o_rtg")):
            lines.append(_stat_row("Off Rating", rec.get("o_rtg")))

        if _clean(rec.get("d_rtg")):
            lines.append(_stat_row("Def Rating", rec.get("d_rtg")))

        if _clean(rec.get("pace")):
            lines.append(_stat_row("Pace", rec.get("pace")))

        season = _clean(rec.get("season"))

        footer = None

        if playoffs:

            footer = (
                f"📈 Reached the {playoffs}"
                if len(playoffs) > 4 and not playoffs.isdigit()
                else "📈 Made the playoffs."
            )

        cards = [
            _info(
                f"🏀 {name} — {season}" if season else f"🏀 {name}",
                "Season Summary",
            ),
            _desc(lines),
        ]

        if footer:
            cards.append(_desc([footer]))

        chips = _chips(
            [
                (
                    f"{name} stats in {season}"
                    if season
                    else f"{name} stats that season"
                ),
                (
                    f"Opponent stats of {name} in {season}"
                    if season
                    else f"Opponent stats of {name}"
                ),
            ]
        )

        if chips:
            cards.append(chips)

        return [cards]

    # --------------------------------------------------------
    # TEAM STATS / COMPARE TEAMS (numeric path)
    # --------------------------------------------------------
    if kind == "team_stat":
        stat_rows = result["rows"]
        stat = result.get("stat")
        pretty = _pretty_stat(stat)

        if len(stat_rows) > 1:

            a, b = stat_rows[0], stat_rows[1]

            names_pair = [a["team"], b["team"]]

            ctx_a = {c["label"]: c["value"] for c in (a.get("context") or [])}

            ctx_b = {c["label"]: c["value"] for c in (b.get("context") or [])}

            # Per-team bullet cards instead of 'A vs B'
            # pipe rows that break on narrow screens.

            def _team_block(side: dict, ctx: dict) -> list[str]:

                bullets = [
                    f"• {pretty}: " f"{_stat_value(stat, side['value'])}"
                ]

                for label, value in ctx.items():
                    if label == pretty:
                        continue
                    if _same_val(value, side["value"]) and label not in (
                        "Record",
                        "Playoffs",
                    ):
                        continue

                    bullets.append(f"• {label}: {_fmt(value)}")

                return bullets

            season_a = _fmt(
                a.get("season") or (a.get("record") or {}).get("season")
            )
            season_b = _fmt(
                b.get("season") or (b.get("record") or {}).get("season")
            )

            title_a = f"{a['team']} — {season_a}" if season_a else a["team"]
            title_b = f"{b['team']} — {season_b}" if season_b else b["team"]

            cards = [
                _info(f"⚔️ {a['team']} vs {b['team']}", "Team Comparison"),
                _desc(_team_block(a, ctx_a), title=title_a),
                _desc(_team_block(b, ctx_b), title=title_b),
            ]

            rec_a = a.get("record") or {}
            rec_b = b.get("record") or {}

            if rec_a.get("w") not in (None, "", "nan") and rec_b.get(
                "w"
            ) not in (None, "", "nan"):
                cards.append(
                    _desc(
                        [
                            f"• Records: "
                            f"{_num(rec_a.get('w'))}-"
                            f"{_num(rec_a.get('l'))} "
                            f"({a['team']}, "
                            f"{_fmt(a.get('season') or rec_a.get('season'))})",
                            f"• Records: "
                            f"{_num(rec_b.get('w'))}-"
                            f"{_num(rec_b.get('l'))} "
                            f"({b['team']}, "
                            f"{_fmt(b.get('season') or rec_b.get('season'))})",
                        ],
                        title="Season records",
                    )
                )

            verdict = _verdict(a, b, stat)
            record_note = _record_result_line(a, b)

            tail = [f"🏆 {verdict}"]

            if result.get("mode") == "best_season":
                tail.append("Each team's best season used.")

            if record_note:
                tail.append(record_note)

            cards.append(_desc(tail))

            return [cards]

        r = stat_rows[0]

        primary_val = r["value"]

        lines = [f"{pretty}: {_stat_value(stat, primary_val)}"]

        for c in r.get("context") or []:

            if _same_val(c["value"], primary_val):
                continue

            lines.append(f"{c['label']}: {_fmt(c['value'])}")

        rec = r.get("record") or {}

        if rec.get("w") not in (None, "", "nan"):

            lines.append(
                f"Record: {_num(rec.get('w'))}-" f"{_num(rec.get('l'))}"
            )

            po = _playoffs_txt(rec.get("playoffs"))

            if po:
                lines.append(f"Playoffs: {po}")

            if _clean(rec.get("pace")):
                lines.append(f"Pace: {_num(rec.get('pace'))}")

        return [
            [
                _info(
                    f"📈 {r['team']} — {_fmt(r.get('season'))}",
                    "Season Statistics",
                ),
                _desc(lines),
            ]
        ]

    # --------------------------------------------------------
    # OPPONENT STATS
    # --------------------------------------------------------
    if kind == "team_opponent_stat":
        pretty = _pretty_stat(result.get("stat"))
        context = result.get("context") or []
        ordered = [
            (pretty, _stat_value(result.get("stat"), result.get("value")))
        ]

        for c in context:
            lab = c["label"].replace("Opp ", "")

            if any(
                _same_val(c["value"], existing_val)
                for _, existing_val in ordered
            ):
                continue

            ordered.append((lab, _fmt(c["value"])))

        lines = [f"{lab}: {val}" for lab, val in ordered]

        return [
            [
                _info(
                    f"🛡️ {result.get('team')} "
                    f"— {_fmt(result.get('season'))}",
                    "Opponent Statistics (per game allowed)",
                ),
                _desc(lines),
            ]
        ]

    # --------------------------------------------------------
    # FALLBACK: plain text only
    # --------------------------------------------------------
    plain = _generate_template(result, intent, query_text)

    return [[_desc([plain])]]


def generate_cards(
    result: dict[str, Any], intent: str, query_text: str = ""
) -> list[dict[str, Any]]:
    """
    Build the full card response for the Streamlit chat UI.

    Sends ONLY the rich payload when cards were built; falls
    back to a single text bubble otherwise. Never both — the
    old bubble+card pair showed duplicate content.
    webhook.process_message parses this into {'rich', 'text'}.
    """
    messages: list[dict[str, Any]] = []

    try:
        rows = _build_rich(result, intent, query_text)
    except Exception:  # pragma: no cover - safety net
        logging.exception("Rich card build failed")
        rows = None

    if rows:
        rows = _expand_rich(rows)
        messages.append({"payload": {"richContent": rows}})

        return messages

    text = _fw(generate(result, intent, query_text))

    messages.append({"text": {"text": [text]}})

    return messages
