from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from config import DATA_DIR

PLAYER_FUZZY_CUTOFF = 0.85


@dataclass
class QueryResult:
    ok: bool
    answer_data: dict[str, Any]
    error: str | None = None


class NBAQueryEngine:
    """
    Query engine for HoopMind.

    Dialogflow is responsible for:
    - Intent detection
    - Entity recognition
    - Entity normalization
    - Parameter extraction

    This class is responsible for:
    - Loading NBA CSV datasets
    - Filtering data
    - Mapping statistics to CSV columns
    - Returning structured query results
    """

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        self._cache: dict[str, pd.DataFrame] = {}
        self._fuzzy_note: str | None = None

    # ============================================================
    # BASIC DATASET FUNCTIONS
    # ============================================================
    def _load(self, filename: str) -> pd.DataFrame:
        """Load a CSV dataset and cache it."""

        if filename not in self._cache:
            path = self.data_dir / filename

            if not path.exists():
                raise FileNotFoundError(f"Dataset not found: {path}")

            self._cache[filename] = pd.read_csv(path, low_memory=False)

        return self._cache[filename]

    @staticmethod
    def _norm(value: Any) -> str:
        """
        Normalize text for comparison.

        Accent-insensitive and punctuation-insensitive so that:

        Nikola Jokic      == Nikola Jokić
        J.J. Redick       == JJ Redick
        Stephen  Curry    == stephen curry
        """

        import unicodedata

        text = str(value).strip().lower()

        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))

        text = re.sub(r"[.'\-’]", "", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @staticmethod
    def _validate_season_year(value: Any) -> bool:
        """
        Return True if value looks like a plausible NBA starting-season
        year (4 digits, 1946..current+1).
        """
        if value is None:
            return False
        s = str(value).strip()
        if not s:
            return False
        # A pure year like '2016', a range like '2016-17' or '2016-2017'
        m_range = re.fullmatch(r"(\d{4})-(\d{2}|\d{4})", s)
        if m_range:
            year_str = m_range.group(1)
        else:
            year_str = s if s.isdigit() and len(s) == 4 else None
        if not year_str:
            return False
        try:
            year = int(year_str)
        except ValueError:
            return False
        import datetime as _dt
        max_year = _dt.date.today().year + 2
        return 1946 <= year <= max_year

    @staticmethod
    def _season_candidates(season: Any) -> list[str]:
        """
        Convert Dialogflow season values into possible dataset values.
        Returns [] when the value is clearly invalid (not a 4-digit
        year or a recognised season range).
        Example:

        2024-25
        ->
        ['2024', '2024-25']
        """
        if season is None:
            return []

        s = str(season).strip()

        if not s:
            return []

        if not NBAQueryEngine._validate_season_year(s):
            return []

        match = re.fullmatch(r"(\d{4})-(\d{2}|\d{4})", s)

        if match:
            return [match.group(1), s]

        return [s]

    def _abbrev_to_team(self) -> dict[str, str]:
        """
        Map a team abbreviation (e.g. 'LAL') to the most recent
        franchise name that used it, via Team Abbrev.csv.
        """
        if not hasattr(self, "_abbr_cache"):
            try:
                ab = self._load("Team Abbrev.csv").astype(str)
                self._abbr_cache = (
                    ab.sort_values("season")
                    .groupby("abbreviation")["team"]
                    .last()
                    .to_dict()
                )
            except Exception:
                self._abbr_cache = {}
        return self._abbr_cache

    def _pick_row(self, df: pd.DataFrame) -> pd.Series:
        """
        Choose the most representative row for a player/season slice.

        Players traded mid-season appear multiple times (TOT + team rows),
        so sort by season and push TOT (full-season) rows to the end,
        then take the last row.
        """

        if "season" not in df.columns:
            return df.iloc[-1]

        df = df.copy()
        df["_season_num"] = pd.to_numeric(df["season"], errors="coerce")

        sort_cols = ["_season_num"]
        if "team" in df.columns:
            df["_tot_rank"] = (
                df["team"].astype(str).str.upper().eq("TOT").astype(int)
            )
            sort_cols.append("_tot_rank")
        df = df.sort_values(sort_cols, kind="stable")

        return df.iloc[-1]

    def _team_display_name(self, value: Any) -> str:
        """Resolve a team abbreviation to a franchise display name."""
        text = str(value or "").strip()
        if not text or text.lower() == "nan":
            return ""

        if not text.isupper() or len(text) > 4:
            return text

        return self._abbrev_to_team().get(text.upper(), text)

    # ============================================================
    # FILTER FUNCTIONS
    # ============================================================
    def _filter_player(
        self, df: pd.DataFrame, player: str | None
    ) -> pd.DataFrame:

        self._fuzzy_note = None

        if not player or "player" not in df.columns:
            return df

        target = self._norm(player)
        mask = df["player"].astype(str).map(self._norm) == target
        result = df.loc[mask]

        if not result.empty:
            return result

        # --------------------------------------------------------
        # Fuzzy correction for typos such as 'Joel Embid' ->
        # 'Joel Embiid'. Only accept a very close match, otherwise
        # return empty so the bot asks for clarification instead
        # of silently answering about the wrong player.
        # --------------------------------------------------------

        candidates = df["player"].dropna().astype(str).unique()

        close = difflib.get_close_matches(
            str(player), candidates, n=1, cutoff=PLAYER_FUZZY_CUTOFF
        )

        if close:
            best = close[0]
            self._fuzzy_note = best
            return df.loc[df["player"] == best]

        return result

    def _filter_team(self, df: pd.DataFrame, team: str | None) -> pd.DataFrame:
        if not team or "team" not in df.columns:
            return df
        
        target = self._norm(team)

        # Resolve common abbreviations (e.g. 'BOS') to full names.
        try:
            abbrev_map = self._abbrev_to_team()
            resolved = abbrev_map.get(str(team).strip().upper())

            if resolved and resolved != str(team):
                target = self._norm(resolved)

        except FileNotFoundError:
            pass

        mask = df["team"].astype(str).map(self._norm) == target
        result = df.loc[mask]

        if not result.empty or len(target) < 4:
            return result

        # Graceful partial match: 'Lakers' -> 'Los Angeles Lakers'.
        normed = df["team"].astype(str).map(self._norm)
        fuzzy_mask = normed.map(lambda name: target in name)

        return df.loc[fuzzy_mask]

    def _filter_season(
        self, df: pd.DataFrame, season: str | None
    ) -> pd.DataFrame:

        if not season or "season" not in df.columns:
            return df

        candidates = {s.casefold() for s in self._season_candidates(season)}

        return df[df["season"].astype(str).str.casefold().isin(candidates)]

    # ============================================================
    # STATISTIC MAPPING
    # ============================================================
    STAT_SYNONYMS: dict[str, str] = {
        # points
        "ppg": "points",
        "points per game": "points",
        "pts": "points",
        "scoring": "points",
        # rebounds
        "rpg": "rebounds",
        "rebounds per game": "rebounds",
        "boards": "rebounds",
        "board": "rebounds",
        "reb": "rebounds",
        # assists
        "apg": "assists",
        "assists per game": "assists",
        "dimes": "assists",
        "dishes": "assists",
        "ast": "assists",
        # steals / blocks / turnovers
        "spg": "steals",
        "swipes": "steals",
        "stl": "steals",
        "bpg": "blocks",
        "rejections": "blocks",
        "blk": "blocks",
        "tpg": "turnovers",
        "miscues": "turnovers",
        # shooting
        "fgm": "field goals",
        "field goals made": "field goals",
        "fga": "field goal attempts",
        "fg%": "field goal percentage",
        "shooting percentage": "field goal percentage",
        "threes": "three-pointers",
        "triples": "three-pointers",
        "3 pointers": "three-pointers",
        "three pointers": "three-pointers",
        "three pointers made": "three-pointers",
        "3pm": "three-pointers",
        "3pa": "three-point attempts",
        "three point attempts": "three-point attempts",
        "3p%": "three-point percentage",
        "3pt%": "three-point percentage",
        "three point percentage": "three-point percentage",
        "ftm": "free throws",
        "free throws made": "free throws",
        "fta": "free throw attempts",
        "ft%": "free throw percentage",
        # misc
        "mpg": "minutes",
        "minutes per game": "minutes",
        "minutes played": "minutes",

        # fouls
        "shooting foul": "shooting fouls",
        "shooting fouls": "shooting fouls",
        "shooting foul committed": "shooting fouls committed",
        "shooting fouls committed": "shooting fouls committed",
        "shooting foul drawn": "shooting fouls drawn",
        "shooting fouls drawn": "shooting fouls drawn",

        "offensive foul": "offensive fouls",
        "offensive fouls": "offensive fouls",
        "offensive foul committed": "offensive fouls committed",
        "offensive fouls committed": "offensive fouls committed",
        "offensive foul drawn": "offensive fouls drawn",
        "offensive fouls drawn": "offensive fouls drawn",

        # Generic foul wording
        "fouls": "personal fouls",
        # advanced
        "efficiency": "player efficiency rating",
        "ts%": "true shooting percentage",
        "true shooting": "true shooting percentage",
        "efg%": "effective field goal percentage",
        "effective fg%": "effective field goal percentage",
        "usage rate": "usage percentage",
        "ws": "win shares",
        "ws/48": "win shares per 48",
        "bpm": "box plus/minus",
        "vorp": "value over replacement player",
        "ortg": "offensive rating",
        "drtg": "defensive rating",
        # play-by-play / shooting specials
        "+/-": "plus-minus",
        "net plus minus": "plus-minus",
        "dunk": "dunks",
        "corner 3%": "corner three percentage",
        "corner 3 percentage": "corner three percentage",
    }

    def _canonical_stat(self, stat: Any) -> str:
        """
        Normalize user/stat wording into a canonical key before
        looking it up in the dataset-specific column mappings,
        e.g. 'ppg' -> 'points', 'boards' -> 'rebounds'.
        """

        s = str(stat or "").casefold().strip()

        # These must be handled BEFORE generic "fouls" /
        # "personal fouls" mappings.
        if "shooting foul" in s:
            if "draw" in s:
                return "shooting fouls drawn"
            return "shooting fouls committed"

        if "offensive foul" in s:
            if "draw" in s:
                return "offensive fouls drawn"
            return "offensive fouls committed"

        # Existing synonym mappings
        if s in self.STAT_SYNONYMS:
            resolved = self.STAT_SYNONYMS[s]
            if resolved is not None:
                return resolved

        return s

    # ============================================================
    # AWARD MATCHING (entity value -> dataset award names)
    # ============================================================

    AWARD_SYNONYMS = {
        "mvp": "nba mvp",
        "most valuable player": "nba mvp",
        "dpoy": "nba dpoy",
        "defensive player of the year": "nba dpoy",
        "roy": "nba roy",
        "rookie of the year": "nba roy",
        "mip": "nba mip",
        "most improved player": "nba mip",
        "smoy": "nba smoy",
        "sixth man of the year": "nba smoy",
        "clutch player of the year": "nba clutch_poy",
    }

    def _filter_award(self, frame: pd.DataFrame, award: Any) -> pd.DataFrame:
        """
        Match an award entity value ('MVP', 'NBA DPOY', ...) against the
        dataset's award names ('nba mvp', 'nba dpoy', ...).
        Falls back to substring containment in either direction.
        """

        if not award or "award" not in frame.columns:
            return frame

        key = self._norm(award)
        key = self.AWARD_SYNONYMS.get(key, key)
        normed = frame["award"].astype(str).map(self._norm)
        exact = frame[normed == key]

        if not exact.empty:
            return exact

        contains = frame[
            normed.map(lambda s: bool(key) and (key in s or s in key))
        ]

        return contains

    def _column_for_stat(
        self, stat: Any, dataset_type: str, columns: pd.Index
    ) -> str | None:

        s = self._canonical_stat(stat)

        mapping: dict[str, dict[str, str]] = {
            # ----------------------------------------------------
            # PLAYER PER GAME
            # ----------------------------------------------------
            "per_game": {
                "points": "pts_per_game",
                "rebounds": "trb_per_game",
                "assists": "ast_per_game",
                "steals": "stl_per_game",
                "blocks": "blk_per_game",
                "turnovers": "tov_per_game",
                "personal fouls": "pf_per_game",
                "field goals": "fg_per_game",
                "field goal attempts": "fga_per_game",
                "field goal percentage": "fg_percent",
                "three-pointers": "x3p_per_game",
                "three-point attempts": "x3pa_per_game",
                "three-point percentage": "x3p_percent",
                "free throws": "ft_per_game",
                "free throw attempts": "fta_per_game",
                "free throw percentage": "ft_percent",
                "minutes": "mp_per_game",
                "games": "g",
                "games started": "gs",
            },
            # ----------------------------------------------------
            # PLAYER CAREER / SEASON TOTALS
            # ----------------------------------------------------
            "totals": {
                "points": "pts",
                "rebounds": "trb",
                "assists": "ast",
                "steals": "stl",
                "blocks": "blk",
                "turnovers": "tov",
                "personal fouls": "pf",
                "field goals": "fg",
                "field goal attempts": "fga",
                "field goal percentage": "fg_percent",
                "three-pointers": "x3p",
                "three-point attempts": "x3pa",
                "three-point percentage": "x3p_percent",
                "free throws": "ft",
                "free throw attempts": "fta",
                "free throw percentage": "ft_percent",
                "minutes": "mp",
                "games": "g",
                "games started": "gs",
            },
            # ----------------------------------------------------
            # PER 100 POSSESSIONS
            # ----------------------------------------------------
            "per_100": {
                "points": "pts_per_100_poss",
                "rebounds": "trb_per_100_poss",
                "assists": "ast_per_100_poss",
                "steals": "stl_per_100_poss",
                "blocks": "blk_per_100_poss",
                "turnovers": "tov_per_100_poss",
                "personal fouls": "pf_per_100_poss",
                "field goals": "fg_per_100_poss",
                "field goal attempts": "fga_per_100_poss",
                "three-pointers": "x3p_per_100_poss",
                "three-point attempts": "x3pa_per_100_poss",
                "free throws": "ft_per_100_poss",
                "free throw attempts": "fta_per_100_poss",
            },
            # ----------------------------------------------------
            # PER 36 MINUTES
            # ----------------------------------------------------
            "per_36": {
                "points": "pts_per_36_min",
                "rebounds": "trb_per_36_min",
                "assists": "ast_per_36_min",
                "steals": "stl_per_36_min",
                "blocks": "blk_per_36_min",
                "turnovers": "tov_per_36_min",
                "personal fouls": "pf_per_36_min",
                "field goals": "fg_per_36_min",
                "field goal attempts": "fga_per_36_min",
                "three-pointers": "x3p_per_36_min",
                "three-point attempts": "x3pa_per_36_min",
                "free throws": "ft_per_36_min",
                "free throw attempts": "fta_per_36_min",
            },
            # ----------------------------------------------------
            # ADVANCED
            # ----------------------------------------------------
            "advanced": {
                "per": "per",
                "player efficiency rating": "per",
                "efficiency": "per",
                "true shooting percentage": "ts_percent",
                "true shooting": "ts_percent",
                "ts": "ts_percent",
                "ts%": "ts_percent",
                # IMPORTANT:
                # eFG% is NOT TS%.
                "effective field goal percentage": "efg_percent",
                "efg": "efg_percent",
                "efg%": "efg_percent",
                "usage percentage": "usg_percent",
                "usage": "usg_percent",
                "usg": "usg_percent",
                "usg%": "usg_percent",
                "win shares": "ws",
                "ws": "ws",
                "win shares per 48": "ws_48",
                "box plus/minus": "bpm",
                "box plus minus": "bpm",
                "bpm": "bpm",
                "value over replacement player": "vorp",
                "vorp": "vorp",
                "offensive box plus/minus": "obpm",
                "obpm": "obpm",
                "defensive box plus/minus": "dbpm",
                "dbpm": "dbpm",
                "offensive win shares": "ows",
                "defensive win shares": "dws",
                "offensive rating": "ows",
                "defensive rating": "dws",
            },
            # ----------------------------------------------------
            # PLAY BY PLAY
            # ----------------------------------------------------
            "play_by_play": {
                "plus-minus": "net_plus_minus_per_100_poss",
                "net plus minus": "net_plus_minus_per_100_poss",
                "net +/-": "net_plus_minus_per_100_poss",

                "on-court plus-minus": "on_court_plus_minus_per_100_poss",
                "on court plus minus": "on_court_plus_minus_per_100_poss",
                "on-court +/-": "on_court_plus_minus_per_100_poss",

                "and-one": "and1",
                "and1": "and1",

                "dunks": "num_of_dunks",

                "assists points": "points_generated_by_assists",
                "points from assists": "points_generated_by_assists",
                "points generated by assists": "points_generated_by_assists",
                "passes": "passes_made",

                "shooting fouls": "shooting_foul_committed",
                "shooting fouls committed": "shooting_foul_committed",
                "shooting fouls drawn": "shooting_foul_drawn",
                "offensive fouls": "offensive_foul_committed",
                "offensive fouls committed": "offensive_foul_committed",
                "offensive fouls drawn": "offensive_foul_drawn",
            },
            # ----------------------------------------------------
            # SHOOTING
            # ----------------------------------------------------
            "shooting": {
                "field goal percentage": "fg_percent",
                "fg%": "fg_percent",
                "corner three percentage": "corner_3_point_percent",
                "three-point percentage": "fg_percent_from_x3p_range",
                "3p%": "fg_percent_from_x3p_range",
                "shot distance": "avg_dist_fga",
                "average shot distance": "avg_dist_fga",
                "dunks": "num_of_dunks",
            },
        }

        col = mapping.get(dataset_type, {}).get(s)
        if col in columns:
            return col

        return None

    # ============================================================
    # VALUE FORMATTER
    # ============================================================

    @staticmethod
    def _value(row: pd.Series, col: str) -> Any:

        value = row[col]
        if pd.isna(value):
            return None

        try:
            num = float(value)
            if num.is_integer():
                return int(num)

            return round(num, 3)

        except (TypeError, ValueError):

            return value

    # ============================================================
    # MAIN QUERY ROUTER
    # ============================================================

    @staticmethod
    def _scalar(value: Any) -> Any:
        """
        Dialogflow sends list-valued parameters (e.g. ["LeBron James"]).

        The engine treats every parameter as a single value,
        so unwrap one-element lists.
        """

        if isinstance(value, (list, tuple)):
            return value[0] if value else None

        return value

    def query(
        self, intent: str, params: dict[str, Any], query_text: str = ""
    ) -> QueryResult:

        try:
            params = {
                key: self._scalar(value) for key, value in params.items()
            }

            # ------------------------------------------------
            # ENTITY GUARDS: without these, a missing or
            # garbled name falls through to the first CSV row
            # (alphabetically Hank Biasatti). Fail politely
            # instead whenever the handler needs an entity the
            # question never supplied.
            # ------------------------------------------------
            if intent == "award_winner":
                intent = "player_awards"

            PLAYER_NEEDED = {
                "player_information",
                "player_career_totals",
                "player_season_stats",
                "player_advanced_stats",
                "player_per_36_stats",
                "player_per_100_stats",
                "player_shooting_stats",
                "player_play_by_play_stats",
            }
            TEAM_NEEDED = {
                "team_information",
                "team_summary",
                "team_opponent_stats",
                "team_season_stats",
            }
            PLAYER_OR_SEASON_NEEDED = {
                "all_star_selection",
                "end_of_season_team",
                "draft_information",
            }

            if intent in PLAYER_NEEDED and not params.get("player"):
                return QueryResult(
                    False,
                    {"missing": "player"},
                    "I couldn't find that player in my NBA "
                    "dataset. Please check the spelling — "
                    "for example 'Tell me about Stephen "
                    "Curry'.",
                )

            if intent == "player_awards":
                has_p = bool(params.get("player"))
                has_s = bool(params.get("season"))
                has_a = bool(params.get("award"))
                has_year_in_text = bool(
                    query_text
                    and re.search(r"\b(?:19|20)\d{2}\b", query_text)
                )
                has_award_word_in_text = bool(
                    query_text
                    and re.search(
                        r"\b(mvp|roy|dpoy|mip|smoy|award|player of the year|sixth man|most improved|rookie of the year|most valuable|defensive player|clutch player)\b",
                        query_text,
                        re.IGNORECASE,
                    )
                )
                if (
                    not has_p
                    and not has_s
                    and not has_a
                    and not has_year_in_text
                    and not has_award_word_in_text
                ):
                    return QueryResult(
                        False,
                        {"missing": "player"},
                        "Please name a player, or an award plus season — "
                        "for example 'Awards won by Stephen Curry' or "
                        "'Who won MVP in 2016?'.",
                    )

            if intent in TEAM_NEEDED and not params.get("team"):
                return QueryResult(
                    False,
                    {"missing": "team"},
                    "I couldn't find that team in my NBA "
                    "dataset. Please check the spelling — "
                    "for example 'Tell me about the Boston "
                    "Celtics'.",
                )

            if intent in PLAYER_OR_SEASON_NEEDED:
                has_p = bool(params.get("player"))
                has_s = bool(params.get("season"))
                if intent == "draft_information" and not has_p:
                    if not has_s and query_text:
                        if not re.search(r"\b(?:19|20)\d{2}\b", query_text):
                            return QueryResult(
                                False,
                                {"missing": "season", "have": []},
                                "Which year's draft? For example: "
                                "'Show me the full 2003 NBA draft'.",
                            )
                elif not has_p and not has_s:
                    if intent == "all_star_selection":
                        return QueryResult(
                            False,
                            {"missing": "season", "have": []},
                            "Which All-Star game? For example: "
                            "'2022 NBA All-Star roster'.",
                        )
                    if intent == "end_of_season_team":
                        return QueryResult(
                            False,
                            {"missing": "season", "have": []},
                            "Which season? For example: "
                            "'2021 All-NBA First Team'.",
                        )
                
            if intent == "compare_players":
                have = [p for p in (params.get("player1"), params.get("player2")) if p]
                if len(have) < 2:
                    return QueryResult(
                        False,
                        {"missing": "player_pair", "have": have},
                        "Please name two players to "
                        "compare — for example 'Compare "
                        "Kobe and Jordan'.",
                    )

            if intent == "compare_teams":
                have_t = [
                    t for t in (params.get("team1"), params.get("team2")) if t]

                if len(have_t) < 2:
                    return QueryResult(
                        False,
                        {"missing": "team_pair", "have": have_t},
                        "Please name two teams to "
                        "compare — for example 'Compare "
                        "the Bulls and the Lakers'.",
                    )

            # ----------------------------------------------------
            # BASIC INTENTS
            # ----------------------------------------------------
            if intent in {"greeting", "goodbye"}:
                return QueryResult(True, {"kind": intent})

            # ----------------------------------------------------
            # DATASET SCOPE
            # ----------------------------------------------------
            if intent == "dataset_scope":
                datasets = [p.name for p in self.data_dir.glob("*.csv")]

                return QueryResult(
                    True, {"kind": "dataset_scope", "datasets": datasets}
                )

            # ----------------------------------------------------
            # LEAGUE INFORMATION
            # ----------------------------------------------------
            if intent == "league_information":
                # ------------------------------------------------
                # 'What league did Michael Jordan play in?' /
                # 'Was Kareem Abdul-Jabbar in the ABA?'
                # ------------------------------------------------
                if params.get("player"):
                    pg = self._load("Player Per Game.csv")
                    pg = self._filter_player(pg, params.get("player"))

                    if not pg.empty:

                        seasons_pg = pd.to_numeric(
                            pg["season"], errors="coerce"
                        ).dropna()

                        return QueryResult(
                            True,
                            {
                                "kind": "league_information",
                                "player_leagues": sorted(
                                    pg["lg"].dropna().astype(str).unique()
                                ),
                                "player": str(pg.iloc[0]["player"]),
                                "span": (
                                    f"{int(seasons_pg.min())}"
                                    f" - "
                                    f"{int(seasons_pg.max())}"
                                    if len(seasons_pg)
                                    else None
                                ),
                            },
                        )

                league = params.get("league") or "NBA"
                topic = None
                lowered = (query_text or "").casefold()

                if (
                    "nba" in lowered and ("aba" in lowered or "baa" in lowered)
                ) or "difference" in lowered:
                    topic = "league_compare"

                return QueryResult(
                    True,
                    {
                        "kind": "league_information",
                        "league": league,
                        "topic": topic,
                    },
                )

            # ----------------------------------------------------
            # PLAYER INFORMATION
            # ----------------------------------------------------
            if intent == "player_information":
                df = self._load("Player Career Info.csv")
                df = self._filter_player(df, params.get("player"))

                if df.empty:

                    return QueryResult(
                        False,
                        {},
                        "I could not find that player in the career information dataset.",
                    )

                return QueryResult(
                    True,
                    {
                        "kind": "player_information",
                        "row": df.iloc[0].to_dict(),
                    },
                )

            # ----------------------------------------------------
            # PLAYER SEASON STATS (or compare_players)
            # ----------------------------------------------------
            if intent in {"player_season_stats", "compare_players"}:
                if intent == "compare_players":
                    # Detect award-count comparison first: if the user
                    # mentions any award word (MVP, ROY, award, ring,
                    # championship, trophy, etc.), compare award counts
                    # rather than per-game statistics.
                    award = params.get("award")
                    lowered = self._norm(query_text or "")
                    award_lexicon = set(self.AWARD_SYNONYMS) | {
                        "award",
                        "awards",
                        "trophy",
                        "trophies",
                        "ring",
                        "rings",
                        "championship",
                        "championships",
                        "title",
                        "titles",
                        "mvp",
                        "mvps",
                    }
                    has_award_hint = bool(award)
                    if not has_award_hint and query_text:
                        has_award_hint = any(
                            re.search(
                                r"(?<![a-z0-9])"
                                + re.escape(w)
                                + r"s?(?![a-z0-9])",
                                lowered,
                            )
                            for w in sorted(award_lexicon, key=len, reverse=True)
                        )
                    if not award and query_text:
                        for key in sorted(
                            self.AWARD_SYNONYMS, key=len, reverse=True
                        ):
                            if re.search(
                                r"(?<![a-z0-9])"
                                + re.escape(key)
                                + r"s?(?![a-z0-9])",
                                lowered,
                            ):
                                award = self.AWARD_SYNONYMS[key]
                                break
                    if has_award_hint:
                        return self._player_award_compare_query(
                            params, query_text, award
                        )

                return self._player_stat_query(
                    params,
                    "Player Per Game.csv",
                    "per_game",
                    compare=intent == "compare_players",
                    query_text=query_text,
                )

            # ----------------------------------------------------
            # PLAYER CAREER TOTALS
            # ----------------------------------------------------
            if intent == "player_career_totals":
                if params.get("player1") and params.get("player2"):
                    return self._player_stat_query(
                        params,
                        "Player Totals.csv",
                        "totals",
                        compare=True,
                        query_text=query_text,
                    )
                return self._player_career_total_query(params)

            # ----------------------------------------------------
            # PLAYER PER 100
            # ----------------------------------------------------
            if intent == "player_per_100_stats":
                return self._player_stat_query(
                    params, "Per 100 Poss.csv", "per_100"
                )

            # ----------------------------------------------------
            # PLAYER PER 36
            # ----------------------------------------------------
            if intent == "player_per_36_stats":
                return self._player_stat_query(
                    params, "Per 36 Minutes.csv", "per_36"
                )

            # ----------------------------------------------------
            # PLAYER ADVANCED
            # ----------------------------------------------------
            if intent == "player_advanced_stats":

                return self._player_stat_query(
                    params, "Advanced.csv", "advanced"
                )

            # ----------------------------------------------------
            # PLAYER PLAY BY PLAY
            # ----------------------------------------------------
            if intent == "player_play_by_play_stats":
                return self._player_stat_query(
                    params, "Player Play By Play.csv", "play_by_play"
                )

            # ----------------------------------------------------
            # PLAYER SHOOTING
            # ----------------------------------------------------
            if intent == "player_shooting_stats":
                return self._player_stat_query(
                    params, "Player Shooting.csv", "shooting"
                )

            # ----------------------------------------------------
            # PLAYER AWARDS
            # ----------------------------------------------------
            if intent == "player_awards":
                df = self._load("Player Award Shares.csv")

                # ----------------------------------------------------
                # Winner query without a player, e.g.
                # 'Who won MVP in 2016?' -> show the winner(s).
                # ----------------------------------------------------
                if not params.get("player"):

                    # ------------------------------------------------
                    # Infer the award from the wording when the
                    # agent sent no @award value, e.g. 'Who won
                    # MVP in 2016?'.
                    # ------------------------------------------------
                    award = params.get("award")
                    if not award and query_text:
                        lowered = self._norm(query_text)

                        for key in sorted(
                            self.AWARD_SYNONYMS, key=len, reverse=True
                        ):
                            if re.search(
                                r"(?<![a-z0-9])"
                                + re.escape(key)
                                + r"(?![a-z0-9])",
                                lowered,
                            ):
                                award = self.AWARD_SYNONYMS[key]
                                break

                    season_value = params.get("season")
                    if not season_value and query_text:
                        # Safety net: when Dialogflow did not fill the
                        # season param (e.g. because the user typed a
                        # typo like "20166"), look for a 4-digit year
                        # directly in the question.
                        year_match = re.search(
                            r"\b(?:19|20)\d{2}\b", query_text
                        )
                        if year_match:
                            season_value = year_match.group(0)

                    winners_df = df
                    season_filter_applied = False
                    if season_value:
                        before_len = len(winners_df)
                        winners_df = self._filter_season(
                            winners_df, season_value
                        )
                        if self._validate_season_year(season_value):
                            season_filter_applied = True
                        elif not before_len or len(winners_df) == before_len:
                            # User gave a non-year number (e.g. 20166)
                            # which was not a valid season. Treat as
                            # invalid attempted season.
                            season_filter_applied = True
                            winners_df = winners_df.iloc[0:0]

                    winners_df = self._filter_award(winners_df, award)

                    if "winner" in winners_df.columns:
                        winners_df = winners_df[
                            winners_df["winner"]
                            .astype(str)
                            .str.lower()
                            .isin({"true", "1", "yes"})
                        ]

                    if winners_df.empty:
                        query_seems_time_bound = bool(
                            query_text
                            and (
                                re.search(r"\d{2,}", query_text)
                                or season_value is not None
                            )
                        )
                        if query_seems_time_bound or season_filter_applied:
                            return QueryResult(
                                False,
                                {},
                                "I could not find an award winner for that "
                                "season and award combination.",
                            )
                        return QueryResult(
                            False,
                            {},
                            "Which season? For example: "
                            "'Who won MVP in 2016?' or '2024 NBA ROY'.",
                        )

                    # Guard: when NO specific season was applied (either
                    # param- nor text-derived), do NOT return a mash-up of
                    # winners across different seasons with a misleading
                    # header from the first row. Ask for a season, or if
                    # the question clearly contains digits/attempted year
                    # treat it as a season-not-found error.
                    unique_seasons = (
                        sorted({str(s) for s in winners_df["season"].astype(str).unique()})
                        if "season" in winners_df.columns
                        else []
                    )
                    if len(unique_seasons) > 1:
                        query_seems_time_bound = bool(
                            query_text
                            and (
                                re.search(r"\d{2,}", query_text)
                                or season_value is not None
                            )
                        )
                        if query_seems_time_bound or season_filter_applied:
                            return QueryResult(
                                False,
                                {},
                                "I could not find an award winner for that "
                                "season and award combination.",
                            )
                        return QueryResult(
                            False,
                            {},
                            "Which season? For example: "
                            "'Who won MVP in 2016?' or '2024 NBA ROY'.",
                        )

                    return QueryResult(
                        True,
                        {
                            "kind": "award_winner",
                            "rows": winners_df.to_dict("records")[:5],
                        },
                    )

                df = self._filter_player(df, params.get("player"))
                df = self._filter_season(df, params.get("season"))
                df = self._filter_award(df, params.get("award"))

                # ----------------------------------------------------
                # Prioritise outright wins so the row cap never
                # hides a player's trophies behind minor voting
                # appearances. Shares then order the rest.
                # ----------------------------------------------------
                if "winner" in df.columns:
                    win_flag = (
                        df["winner"]
                        .astype(str)
                        .str.lower()
                        .isin({"true", "1", "yes"})
                        .astype(int)
                        .to_numpy()
                    )

                    if "share" in df.columns:
                        share_vals = (
                            pd.to_numeric(df["share"], errors="coerce")
                            .fillna(0)
                            .to_numpy()
                        )
                        df = (
                            df.assign(__w=win_flag, __s=share_vals)
                            .sort_values(
                                ["__w", "__s"],
                                ascending=[False, False],
                                kind="stable",
                            )
                            .drop(columns=["__w", "__s"])
                        )

                    else:
                        df = (
                            df.assign(__w=win_flag)
                            .sort_values("__w", ascending=False, kind="stable")
                            .drop(columns=["__w"])
                        )

                return QueryResult(
                    True,
                    {
                        "kind": "player_awards",
                        "rows": df.to_dict("records")[:40],
                    },
                )

            # ----------------------------------------------------
            # ALL STAR
            # ----------------------------------------------------
            if intent == "all_star_selection":
                df = self._load("All-Star Selections.csv")
                season_value = params.get("season")

                if not season_value and query_text:

                    # Safety net: if Dialogflow did not fill the season
                    # parameter, fall back to a 4-digit year mentioned
                    # directly in the question.
                    year_match = re.search(r"\b(?:19|20)\d{2}\b", query_text)

                    if year_match:
                        season_value = year_match.group(0)

                df = self._filter_player(df, params.get("player"))
                df = self._filter_season(df, season_value)
                all_star_years = sorted(
                    {
                        str(int(str(s)))
                        for s in df["season"].tolist()
                        if str(s).strip().isdigit()
                    }
                )

                def _classify_replaced(value: Any) -> str:
                    """
                    'replaced' column meanings:
                      False        -> picked and played
                      True         -> picked but INJURED,
                                      did not play
                      '<name>'     -> injury replacement
                                      who PLAYED (for <name>)
                    """
                    text = str(value).strip()
                    if text in (
                        "",
                        "False",
                        "false",
                        "None",
                        "none",
                        "nan",
                        "NaN",
                    ):
                        return "normal"

                    if text in ("True", "true", "1"):
                        return "out"
                    return "in_for"

                if "replaced" in df.columns:
                    kinds = df["replaced"].map(_classify_replaced)
                else:
                    kinds = pd.Series(
                        "normal", index=df.index
                    )

                # Roster question modes. Only when NO single
                # player was asked about.
                roster_mode = "played"

                if not params.get("player"):
                    low_txt = (query_text or "").casefold()

                    if any(
                        w in low_txt
                        for w in (
                            "replacement",
                            "who replaced",
                            "instead of",
                        )
                    ):
                        roster_mode = "replacements"
                    elif any(
                        w in low_txt
                        for w in (
                            "select",
                            "chosen",
                            "named to",
                            "drafted",
                            "originally",
                        )
                    ):
                        roster_mode = "selected"
                appeared_players = sorted(
                    df.loc[
                        kinds.isin(["normal", "in_for"]),
                        "player",
                    ]
                    .dropna()
                    .astype(str)
                    .unique()
                )
                injured_players = sorted(
                    df.loc[kinds == "out", "player"]
                    .dropna()
                    .astype(str)
                    .unique()
                )
                replacement_pairs = [
                    (str(r["player"]), str(r["replaced"]).strip())
                    for _, r in df.loc[
                        kinds == "in_for",
                        ["player", "replaced"],
                    ]
                    .iterrows()
                ]

                # Original selections = EVERY name in the
                # season's rows (injured included).
                main_players = sorted(
                    df["player"].dropna().astype(str).unique()
                )
                replacement_players = sorted(
                    df.loc[kinds != "normal", "player"]
                    .dropna()
                    .astype(str)
                    .unique()
                )

                return QueryResult(
                    True,
                    {
                        "kind": "all_star_selection",
                        "rows": df.to_dict("records")[:20],
                        "total": int(len(df)),
                        "years": all_star_years,
                        "distinct_players": (
                            int(df["player"].nunique())
                            if "player" in df.columns
                            else 1
                        ),
                        "players": main_players,
                        "replacements": replacement_players,
                        "appeared": appeared_players,
                        "injured": injured_players,
                        "replacement_pairs": replacement_pairs,
                        "roster_mode": roster_mode,
                    },
                )

            # ----------------------------------------------------
            # DRAFT
            # ----------------------------------------------------
            if intent == "draft_information":
                df = self._load("Draft Pick History.csv")

                # ------------------------------------------------
                # Pick query without a player, e.g.
                # 'Who was the first overall pick in 2003?'
                # ------------------------------------------------
                if not params.get("player"):
                    pick_df = self._filter_season(
                        df, params.get("season")
                    )

                    low_txt = (query_text or "").casefold()

                    # ---- mode detection -----------------
                    full_words = (
                        "full",
                        "complete",
                        "entire",
                        "whole",
                    )
                    overview = (
                        "all picks" in low_txt
                        or "draft overview" in low_txt
                        or "both rounds" in low_txt
                        or (
                            "draft" in low_txt
                            and any(
                                w in low_txt
                                for w in full_words
                            )
                        )
                    )
                    ordinal_words = {
                        w: i + 1
                        for i, w in enumerate(
                            (
                                "first",
                                "second",
                                "third",
                                "fourth",
                                "fifth",
                                "sixth",
                                "seventh",
                                "eighth",
                                "ninth",
                                "tenth",
                                "eleventh",
                                "twelfth",
                            )
                        )
                    }
                    pick_num = None
                    m_hash = re.search(
                        r"#\s*(\d{1,3})\b", low_txt
                    )
                    m_suf = re.search(
                        r"\b(\d{1,3})(?:st|nd|rd|th)\b",
                        low_txt,
                    )

                    if m_hash:
                        pick_num = int(m_hash.group(1))
                    elif m_suf:
                        pick_num = int(m_suf.group(1))
                    else:
                        for word, n in ordinal_words.items():
                            if re.search(
                                rf"\b{word}\b", low_txt
                            ):
                                pick_num = n
                                break

                    name_map2 = self._abbrev_to_team()

                    def _with_franchise(records):
                        for rec in records:
                            rec["franchise"] = (
                                name_map2.get(
                                    str(
                                        rec.get("tm", "")
                                    ).upper(),
                                    "",
                                )
                            )
                        return records

                    # Bare draft question ('2003 NBA Draft')
                    # -> show the complete board. A specific
                    # ordinal picks out one selection.
                    if (
                        not overview
                        and not pick_num
                        and params.get("season")
                    ):
                        overview = True
                    if overview and not params.get("season"):
                        return QueryResult(
                            False,
                            {},
                            "Which year's draft? For example: "
                            "'Show me the full 2003 NBA draft'.",
                        )

                    # ---- SINGLE PICK --------------------
                    if not overview:
                        target = pick_num or 1

                        if "overall_pick" in pick_df.columns:

                            one = pick_df[
                                pick_df["overall_pick"]
                                == float(target)
                            ]
                        else:
                            one = pick_df.iloc[0:0]
                        if one.empty:
                            return QueryResult(
                                False,
                                {},
                                f"I could not find pick "
                                f"#{target} in that draft.",
                            )
                        return QueryResult(
                            True,
                            {
                                "kind":
                                    "draft_information",
                                "rows": _with_franchise(
                                    one.to_dict("records")
                                )[:1],
                                "total": 1,
                                "single_pick": target,
                            },
                        )

                    # ---- FULL DRAFT OVERVIEW ------------
                    if "overall_pick" in pick_df.columns:
                        pick_df = pick_df.sort_values(
                            "overall_pick", kind="stable"
                        )
                    rows_all = _with_franchise(
                        pick_df.to_dict("records")
                    )
                    return QueryResult(
                        True,
                        {
                            "kind": "draft_information",
                            "rows": rows_all,
                            "total": len(rows_all),
                            "by_pick": True,
                            "overview": True,
                        },
                    )

                df = self._filter_player(df, params.get("player"))
                df = self._filter_season(df, params.get("season"))
                name_map = self._abbrev_to_team()
                records = df.to_dict("records")[:20]

                for rec in records:
                    rec["franchise"] = name_map.get(
                        str(rec.get("tm", "")).upper(), ""
                    )
                return QueryResult(
                    True,
                    {
                        "kind": "draft_information",
                        "rows": records,
                        "total": int(len(df)),
                    },
                )

            # ----------------------------------------------------
            # END OF SEASON TEAM
            # ----------------------------------------------------
            if intent == "end_of_season_team":
                df = self._load("End of Season Teams.csv")
                df = self._filter_player(df, params.get("player"))
                df = self._filter_season(df, params.get("season"))

                return QueryResult(
                    True,
                    {
                        "kind": "end_of_season_team",
                        "rows": df.to_dict("records")[:20],
                    },
                )

            # ----------------------------------------------------
            # TEAM INFORMATION
            # ----------------------------------------------------
            if intent == "team_information":
                df = self._load("Team Summaries.csv")
                df = self._filter_team(df, params.get("team"))

                if df.empty:
                    return QueryResult(
                        False, {}, "I could not find that team."
                    )

                df = df.sort_values("season")
                w = pd.to_numeric(df["w"], errors="coerce").sum()
                l = pd.to_numeric(df["l"], errors="coerce").sum()
                best_idx = pd.to_numeric(df["w"], errors="coerce").idxmax()
                best = df.loc[best_idx]

                playoff_mask = (
                    df["playoffs"].astype(str).str.strip().ne("")
                ) & (df["playoffs"].astype(str).str.lower().ne("nan"))

                return QueryResult(
                    True,
                    {
                        "kind": "team_information",
                        "team": str(df.iloc[0]["team"]),
                        "abbreviation": str(
                            df.iloc[-1].get("abbreviation", "")
                        ),
                        "league": str(df.iloc[-1].get("lg", "")),
                        "arena": (
                            str(df.iloc[-1]["arena"])
                            if pd.notna(df.iloc[-1].get("arena"))
                            else None
                        ),
                        "first_season": str(df.iloc[0]["season"]),
                        "last_season": str(df.iloc[-1]["season"]),
                        "seasons": int(len(df)),
                        "wins": int(w),
                        "losses": int(l),
                        "win_pct": round(w / (w + l), 3) if (w + l) else None,
                        "playoff_appearances": int(playoff_mask.sum()),
                        "best_record": {
                            "season": str(best["season"]),
                            "w": str(best["w"]),
                            "l": str(best["l"]),
                        },
                        "last_season_row": df.iloc[-1].to_dict(),
                    },
                )

            # ----------------------------------------------------
            # TEAM STATS
            # ----------------------------------------------------
            if intent in {
                "team_summary",
                "team_season_stats",
                "compare_teams",
            }:
                return self._team_stat_query(
                    params,
                    compare=intent == "compare_teams",
                    summary=intent == "team_summary",
                    query_text=query_text,
                )

            # ----------------------------------------------------
            # TEAM OPPONENT STATS
            # ----------------------------------------------------
            if intent == "team_opponent_stats":
                return self._team_opponent_query(params)

            # ----------------------------------------------------
            # UNKNOWN INTENT
            # ----------------------------------------------------
            return QueryResult(
                False, {}, f"Intent {intent} is not implemented yet."
            )
        except Exception as exc:
            return QueryResult(False, {}, f"Query failed: {exc}")

    # ============================================================
    # PLAYER CAREER TOTALS
    # ============================================================
    def _player_career_total_query(
        self, params: dict[str, Any]
    ) -> QueryResult:
        df = self._load("Player Totals.csv")
        stat = params.get("stat")
        col = self._column_for_stat(stat, "totals", df.columns)
        sub = self._filter_player(df, params.get("player"))

        if sub.empty:
            return QueryResult(
                False,
                {},
                "I could not find that player in the career totals dataset.",
            )

        # --------------------------------------------------------
        # Broad career question ('What are X's career totals?'):
        # sum the standard totals bundle so the generator can
        # render a full career table.
        # --------------------------------------------------------
        bundle_context = []

        if not col and not params.get("stat"):
            for label, candidate in self.CONTEXT_STATS.get("totals", []):
                if candidate not in df.columns:
                    continue
                ctx_sum = pd.to_numeric(sub[candidate], errors="coerce").sum(
                    min_count=1
                )
                if pd.isna(ctx_sum):
                    continue

                bundle_context.append(
                    {
                        "label": label,
                        "value": self._value(
                            pd.Series({candidate: ctx_sum}), candidate
                        ),
                    }
                )
            col = next(
                (
                    c
                    for _, c in self.CONTEXT_STATS["totals"]
                    if c == "pts" and c in df.columns
                ),
                None,
            )
        if not col:
            return QueryResult(
                False,
                {},
                f"I don't have a mapped career-total column for the statistic '{stat}'.",
            )

        value = pd.to_numeric(sub[col], errors="coerce").sum(min_count=1)

        # Career span and team count for the career card.
        span = None
        teams_count = None
        if "season" in sub.columns:
            seasons_num = pd.to_numeric(
                sub["season"], errors="coerce"
            ).dropna()

            if not seasons_num.empty:
                span = f"{int(seasons_num.min())}-" f"{int(seasons_num.max())}"

        if "team_abbreviation" in sub.columns:
            teams_count = int(
                sub["team_abbreviation"]
                .dropna()
                .astype(str)
                .replace("TOT", pd.NA)
                .dropna()
                .nunique()
            )
        elif "team" in sub.columns:
            teams_count = int(
                sub["team"]
                .dropna()
                .astype(str)
                .str.upper()
                .str.replace("TOT", "", regex=False)
                .str.strip()
                .replace("", pd.NA)
                .dropna()
                .nunique()
            )
        return QueryResult(
            True,
            {
                "kind": "player_career_total",
                "player": str(sub.iloc[0]["player"]),
                "stat": stat,
                "stat_requested": bool(stat),
                "value": self._value(pd.Series({col: value}), col),
                "context": bundle_context,
                "seasons": (
                    int(sub["season"].nunique())
                    if "season" in sub.columns
                    else None
                ),
                "span": span,
                "teams_count": teams_count,
            },
        )

    # ============================================================
    # PLAYER STAT QUERY
    # ============================================================
    @staticmethod
    def _fmt_pct(value: Any) -> Any:
        """
        Format a ratio as a percentage string, tolerating datasets that
        store percentages either as fractions (0.701) or as whole
        numbers (27.2).
        """
        try:
            f = float(value)
        except (TypeError, ValueError):
            return value

        if abs(f) <= 1.5:
            f *= 100
        return f"{round(f, 1)}%"

    # ============================================================
    # CONTEXT STAT BUNDLES (for rich card responses)
    # ============================================================
    CONTEXT_STATS: dict[str, list[tuple[str, str]]] = {
        "per_game": [
            ("PPG", "pts_per_game"),
            ("RPG", "trb_per_game"),
            ("APG", "ast_per_game"),
            ("SPG", "stl_per_game"),
            ("BPG", "blk_per_game"),
            ("MPG", "mp_per_game"),
        ],
        "totals": [
            ("PTS", "pts"),
            ("REB", "trb"),
            ("AST", "ast"),
            ("STL", "stl"),
            ("BLK", "blk"),
            ("Games", "g"),
        ],
        "per_100": [
            ("PTS/100", "pts_per_100_poss"),
            ("REB/100", "trb_per_100_poss"),
            ("AST/100", "ast_per_100_poss"),
        ],
        "per_36": [
            ("PTS/36", "pts_per_36_min"),
            ("REB/36", "trb_per_36_min"),
            ("AST/36", "ast_per_36_min"),
        ],
        "advanced": [
            ("PER", "per"),
            ("TS%", "ts_percent"),
            ("WS", "ws"),
            ("USG%", "usg_percent"),
            ("BPM", "bpm"),
            ("VORP", "vorp"),
        ],
        "play_by_play": [
            ("On-court +/-", "on_court_plus_minus_per_100_poss"),
            ("Net +/-", "net_plus_minus_per_100_poss"),
            ("Ast points", "points_generated_by_assists"),
            ("And-1s", "and1"),
        ],
        "shooting": [
            ("FG%", "fg_percent"),
            ("3P%", "fg_percent_from_x3p_range"),
            ("Avg dist (ft)", "avg_dist_fga"),
            ("Dunks", "num_of_dunks"),
        ],
    }

    def _stat_context(
        self, row: pd.Series, dataset_type: str
    ) -> list[dict[str, Any]]:
        """
        Pull a bundle of well-known stats from the row so the
        response generator can render a readable stat card.
        """
        bundle = []

        for label, column in self.CONTEXT_STATS.get(dataset_type, []):
            if column not in row.index:
                continue
            raw = row.get(column)
            if pd.isna(raw):
                continue

            value = self._value(row, column)

            if "%" in label:
                value = self._fmt_pct(value)
            bundle.append({"label": label, "value": value})

        return bundle

    def _player_award_compare_query(
        self,
        params: dict[str, Any],
        query_text: str = "",
        award: Any = None,
    ) -> QueryResult:
        players = [params.get("player1"), params.get("player2")]
        df = self._load("Player Award Shares.csv")

        player_rows = []
        for p in players:
            if not p:
                player_rows.append(None)
                continue
            sub = self._filter_player(df, p)
            sub = self._filter_award(sub, award)
            if sub.empty:
                player_rows.append(None)
                continue
            name = str(sub.iloc[0]["player"])
            wins = sub
            if "winner" in wins.columns:
                wins = wins[
                    wins["winner"]
                    .astype(str)
                    .str.lower()
                    .isin({"true", "1", "yes"})
                ]
            win_years = sorted(
                {str(int(float(y))) for y in wins["season"].dropna()}
            ) if "season" in wins.columns else []

            win_count_by_award: dict[str, list[str]] = {}
            for _, r in wins.iterrows():
                pretty = {
                    "nba mvp": "NBA MVP",
                    "nba dpoy": "NBA DPOY",
                    "nba roy": "NBA ROY",
                    "nba mip": "NBA MIP",
                    "nba smoy": "NBA Sixth Man",
                    "nba clutch_poy": "NBA Clutch POY",
                }.get(self._norm(r.get("award")), str(r.get("award", "Award")))
                yr = str(r.get("season", ""))
                if yr:
                    win_count_by_award.setdefault(pretty, []).append(yr)

            player_rows.append(
                {
                    "player": name,
                    "win_count_by_award": win_count_by_award,
                    "win_years_all": win_years,
                }
            )

        if any(x is None for x in player_rows):
            missing_names = [
                pl for pl, row in zip(players, player_rows) if row is None
            ]
            return QueryResult(
                False,
                {},
                "I could not find both players for that comparison.",
            )

        return QueryResult(
            True,
            {
                "kind": "compare_player_awards",
                "award": award,
                "rows": player_rows,
            },
        )

    def _player_stat_query(
        self,
        params: dict[str, Any],
        filename: str,
        dataset_type: str,
        compare: bool = False,
        query_text: str = "",
    ) -> QueryResult:

        # --------------------------------------------------------
        # 'Career scoring' style comparisons should sum totals,
        # not compare latest-season averages. Also handle
        # "total points of X in 2016" style queries.
        # --------------------------------------------------------
        use_totals = bool(
            query_text
            and re.search(
                r"\btotal\b|\btotals?\b",
                query_text.casefold(),
            )
        )
        if use_totals:
            filename = "Player Totals.csv"
            dataset_type = "totals"
        if use_totals:
            filename = "Player Totals.csv"
            dataset_type = "totals"
        df = self._load(filename)

        if compare:
            players = [params.get("player1"), params.get("player2")]
        else:
            players = [params.get("player")]

        stat = params.get("stat")

        # --------------------------------------------------------
        # Stat fallback: when Dialogflow extracted no statistic,
        # try to infer it from wording such as 'career scoring'.
        # --------------------------------------------------------
        if not stat and query_text:
            lowered = query_text.casefold()
            for key in sorted(self.STAT_SYNONYMS, key=len, reverse=True):
                if re.search(
                    r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])",
                    lowered,
                ):
                    stat = self.STAT_SYNONYMS[key]
                    break

        # ----------------------------------------------------
        # 'Who scored more points' / 'Compare X and Y scoring':
        # a COUNTING stat with no season and no rate wording
        # means CAREER totals, not last-season averages.
        # ----------------------------------------------------
        if (
            compare
            and not use_totals
            and not params.get("season")
            and stat
            in (
                "points",
                "rebounds",
                "assists",
                "steals",
                "blocks",
                "three-pointers",
                "field goals",
                "free throws",
                "games played",
            )
            and query_text
        ):
            lowered = query_text.casefold()
            rate_wording = (
                "averag" in lowered
                or "per game" in lowered
                or bool(
                    re.search(r"\bin\s+(19|20)\d{2}\b", lowered)
                )
            )
            if not rate_wording:
                use_totals = True
                filename = "Player Totals.csv"
                dataset_type = "totals"
                df = self._load(filename)

        # A bare "X vs Y" comparison falls back to career totals,
        # which is the most meaningful head-to-head view when
        # neither a statistic nor a season was specified.
        if compare and not stat and not params.get("season"):
            use_totals = True

            filename = "Player Totals.csv"
            dataset_type = "totals"
            df = self._load(filename)

        # --------------------------------------------------------
        # Season comparison with a counting stat: use totals
        # (e.g. 'rebounds of curry and lebron in 2022' should
        # show total rebounds, not per-game averages).
        # --------------------------------------------------------
        COUNTING_STATS = frozenset({
            "points", "rebounds", "assists", "steals", "blocks",
            "three-pointers", "field goals", "free throws",
            "turnovers", "personal fouls", "minutes",
        })
        if (
            compare
            and not use_totals
            and params.get("season")
            and stat in COUNTING_STATS
        ):
            use_totals = True
            filename = "Player Totals.csv"
            dataset_type = "totals"
            df = self._load(filename)

        col = self._column_for_stat(stat, dataset_type, df.columns)

        # --------------------------------------------------------
        # Broad stats request (no specific statistic extracted):
        # fall back to the headline stat so the generator can
        # render the full context table instead of erroring.
        # --------------------------------------------------------
        COL_TO_STAT = {
            "pts": "points",
            "pts_per_game": "points",
            "pts_per_100_poss": "points",
            "pts_per_36_min": "points",
            "trb": "rebounds",
            "trb_per_game": "rebounds",
            "trb_per_100_poss": "rebounds",
            "trb_per_36_min": "rebounds",
            "ast": "assists",
            "ast_per_game": "assists",
            "stl": "steals",
            "blk": "blocks",
            "per": "player efficiency rating",
            "ts_percent": "true shooting percentage",
            "ws": "win shares",
        }

        if not col and not params.get("stat"):
            bundle_type = "totals" if use_totals else dataset_type
            for _, candidate in self.CONTEXT_STATS.get(bundle_type, []):
                if candidate in df.columns:
                    col = candidate
                    stat = COL_TO_STAT.get(candidate, stat)

                    break
        if not col:
            return QueryResult(
                False,
                {},
                f"I couldn't map '{stat}' to a statistic. Supported "
                "examples: points, rebounds, assists, steals, blocks, "
                "field goal percentage, three-pointers.",
            )

        output = []

        for player in players:
            if not player:
                output.append({"player": None, "value": None})

                continue

            sub = self._filter_player(df, player)
            sub = self._filter_season(sub, params.get("season"))

            if sub.empty:
                output.append({"player": player, "value": None})
                continue

            if use_totals:
                # Sum every season into one career number.
                total_value = pd.to_numeric(sub[col], errors="coerce").sum(
                    min_count=1
                )
                entry_player = str(sub.iloc[0]["player"])
                entry_season = (
                    f"{int(sub['season'].min())}-"
                    f"{int(sub['season'].max())}"
                    if "season" in sub.columns and len(sub) > 1
                    else str(sub.iloc[-1].get("season", ""))
                )
                context = []

                for label, ctx_col in self.CONTEXT_STATS.get("totals", []):

                    if ctx_col not in sub.columns:
                        continue

                    ctx_total = pd.to_numeric(
                        sub[ctx_col], errors="coerce"
                    ).sum(min_count=1)

                    if pd.isna(ctx_total):
                        continue

                    value = self._value(
                        pd.Series({ctx_col: ctx_total}), ctx_col
                    )

                    if "%" in label:
                        value = self._fmt_pct(value)

                    context.append({"label": label, "value": value})

                output.append(
                    {
                        "player": entry_player,
                        "value": self._value(
                            pd.Series({col: total_value}), col
                        ),
                        "season": entry_season,
                        "context": context,
                    }
                )

                continue

            # ------------------------------------------------------
            # Compare with a rate-stat and no explicit season: use
            # the career per-game average (weighted by games played,
            # and dropping tiny cup-of-coffee stints) instead of a
            # single picked season, because _pick_row defaults to
            # the LATEST season which is often a garbage partial
            # stint (e.g. Chris Paul 2026: 16 games, 0.7 SPG).
            # ------------------------------------------------------
            compute_career_rate = bool(
                compare
                and not params.get("season")
                and dataset_type == "per_game"
            )

            if compute_career_rate:
                g_col = "g"
                if g_col in sub.columns:
                    g = pd.to_numeric(sub[g_col], errors="coerce").fillna(0)
                    min_g = g.quantile(0.25) if len(g) else 0
                    mask = g >= max(8.0, min_g)
                    s2 = sub.loc[mask].copy()
                    if s2.empty:
                        s2 = sub.copy()
                    g = pd.to_numeric(s2[g_col], errors="coerce").fillna(0)
                    weights = g / g.sum() if g.sum() > 0 else None
                    entry_player = str(s2.iloc[-1]["player"])
                    s_min = s2["season"].min()
                    s_max = s2["season"].max()
                    try:
                        entry_season = (
                            f"{int(float(s_min))}-{int(float(s_max))}"
                        )
                    except (TypeError, ValueError):
                        entry_season = f"{s_min}-{s_max}"
                    context = []
                    val_num = None
                    stats_pack: dict[str, tuple[str, Any]] = {}
                    for label, ctx_col in self.CONTEXT_STATS.get(
                        "per_game", []
                    ):
                        if ctx_col not in s2.columns:
                            continue
                        series = pd.to_numeric(
                            s2[ctx_col], errors="coerce"
                        )
                        if weights is not None and not weights.isna().all():
                            weighted = (series * weights).sum()
                        else:
                            weighted = series.mean()
                        if pd.isna(weighted):
                            continue
                        if ctx_col == col:
                            val_num = weighted
                        stats_pack[ctx_col] = (label, weighted)
                    if val_num is None and col in s2.columns:
                        series = pd.to_numeric(s2[col], errors="coerce")
                        if weights is not None and not weights.isna().all():
                            val_num = (series * weights).sum()
                        else:
                            val_num = series.mean()
                    for ctx_col, (label, weighted) in stats_pack.items():
                        value = self._value(
                            pd.Series({ctx_col: weighted}), ctx_col
                        )
                        if "%" in label:
                            value = self._fmt_pct(value)
                        context.append({"label": label, "value": value})
                    g_total = int(float(g.sum()))
                    entry: dict[str, Any] = {
                        "player": entry_player,
                        "value": self._value(
                            pd.Series({col: val_num}), col
                        ),
                        "season": entry_season,
                        "context": context,
                        "g": g_total,
                    }
                    if "team" in s2.columns:
                        teams = [
                            t for t in s2["team"].dropna().astype(str).unique()
                        ]
                        if teams:
                            entry["team"] = teams[-1]
                            entry["team_name"] = self._team_display_name(
                                teams[-1]
                            )
                    output.append(entry)
                    continue

            row = self._pick_row(sub)

            entry: dict[str, Any] = {
                "player": str(row["player"]),
                "value": self._value(row, col),
                "season": str(row.get("season", "")),
                "context": self._stat_context(row, dataset_type),
            }

            for col_name, out_key in (
                ("pos", "pos"),
                ("age", "age"),
                ("g", "g"),
            ):

                raw = row.get(col_name)

                if col_name in sub.columns and pd.notna(raw):
                    if col_name == "g":
                        try:
                            entry[out_key] = int(float(raw))
                        except (TypeError, ValueError):
                            pass
                    else:
                        entry[out_key] = str(raw)
            team_raw = row.get("team")

            if "team" in sub.columns and pd.notna(team_raw):
                team_text = str(team_raw)
                entry["team"] = team_text
                entry["team_name"] = self._team_display_name(team_text)

            output.append(entry)

        if compare and any(x["value"] is None for x in output):
            return QueryResult(
                False, {}, "I could not find both players for that comparison."
            )

        if not compare and output[0]["value"] is None:
            return QueryResult(
                False,
                {},
                "I could not find the requested player/statistic combination.",
            )

        return QueryResult(
            True,
            {
                "kind": "player_stat",
                "stat": stat,
                "stat_requested": bool(params.get("stat")),
                "rows": output,
                "dataset": filename,
                "season_requested": bool(params.get("season")),
                "measure": (
                    "season totals"
                    if use_totals and params.get("season")
                    else "career totals" if use_totals
                    else "per game"
                ),
            },
        )

    # ============================================================
    # TEAM STAT QUERY
    # ============================================================
    # TEAM HELPERS (records + context bundles)
    # ============================================================
    def _best_season_year(self, team_name: str):
        """
        Season string of the team's best year by win %,
        from Team Summaries.csv.
        """

        try:
            df = self._load("Team Summaries.csv")
        except FileNotFoundError:
            return None

        sub = self._filter_team(df, team_name)

        if sub.empty or not {"w", "l"} <= set(sub.columns):
            return None

        w_ = pd.to_numeric(sub["w"], errors="coerce")
        l_ = pd.to_numeric(sub["l"], errors="coerce")
        pick = sub.loc[(w_ / (w_ + l_)).idxmax()]
        season = pick.get("season")

        return None if season is None else str(season)

    def _team_record(
        self, team_name: str, season: str | None
    ) -> dict[str, Any] | None:
        """
        Look up the season record row for a team from
        Team Summaries.csv (record, ratings, pace, playoffs...).
        """
        try:
            df = self._load("Team Summaries.csv")
        except FileNotFoundError:
            return None

        sub = self._filter_team(df, team_name)
        sub = self._filter_season(sub, season)

        if sub.empty:
            return None
        if not season and "season" in sub.columns:
            sub = (
                sub.assign(_s=pd.to_numeric(sub["season"], errors="coerce"))
                .sort_values("_s", ascending=False)
                .drop(columns="_s")
            )

            return sub.iloc[0].to_dict()

        return sub.iloc[-1].to_dict()

    TEAM_CONTEXT_STATS = [
        ("PPG", "pts_per_game", False),
        ("Opp PPG", "opp_pts_per_game", False),
        ("FG%", "fg_percent", True),
        ("3P%", "x3p_percent", True),
        ("SRS", "srs", False),
    ]

    def _team_context(self, row: pd.Series) -> list[dict[str, Any]]:
        """
        Bundle of headline team stats from a
        Team Stats Per Game / summaries row.
        """
        bundle = []

        for label, column, is_pct in self.TEAM_CONTEXT_STATS:
            if column not in row.index:
                continue
            raw = row.get(column)

            if pd.isna(raw):
                continue

            value = self._value(pd.Series({column: raw}), column)

            if is_pct:
                value = self._fmt_pct(value)
            bundle.append({"label": label, "value": value})

        return bundle

    def _team_stat_query(
        self,
        params: dict[str, Any],
        compare: bool = False,
        summary: bool = False,
        query_text: str = "",
    ) -> QueryResult:

        # ----------------------------------------------------
        # 'Compare the Bulls and Lakers best seasons': pick
        # each team's own peak season (highest win %) instead
        # of the latest one.
        # ----------------------------------------------------
        best_mode = bool(
            compare
            and query_text
            and re.search(
                r"\bbest\s+(season|record)"
                r"|\bgreatest\s+season\b|\bpeak\b",
                query_text.casefold(),
            )
        )

        # --------------------------------------------------------
        # When no statistic was extracted for a comparison,
        # infer it from wording; if nothing is inferable,
        # fall back to comparing the season records.
        # --------------------------------------------------------
        if compare and not summary and not params.get("stat"):
            inferred = None

            if query_text:
                lowered = query_text.casefold()
                keyword_map = (
                    ("scoring", "points"),
                    ("points", "points"),
                    ("rebound", "rebounds"),
                    ("assist", "assists"),
                    ("steal", "steals"),
                    ("blocks", "blocks"),
                    ("three", "three-pointers"),
                )
                for keyword, canonical in keyword_map:
                    if keyword in lowered:
                        inferred = canonical
                        break
            if inferred:
                params = {**params, "stat": inferred}
            elif params.get("season"):
                return self._team_stat_query(
                    params, compare=True, summary=True
                )

        if summary:
            df = self._load("Team Summaries.csv")
            if compare:
                teams = [params.get("team1"), params.get("team2")]
            else:
                teams = [params.get("team")]
            rows = []
            for team in teams:
                sub = self._filter_team(df, team)
                sub = self._filter_season(
                    sub, params.get("season")
                )

                # No explicit season -> report the
                # LATEST one (CSV is stored newest
                # first, but do not rely on that).
                latest_pick = not params.get("season")
                if (
                    latest_pick
                    and not sub.empty
                    and "season" in sub.columns
                ):
                    sub = sub.assign(
                        _s=pd.to_numeric(
                            sub["season"], errors="coerce"
                        )
                    ).sort_values(
                        "_s", ascending=False
                    ).drop(columns="_s")

                if sub.empty:
                    rows.append({"team": team, "value": None})
                else:
                    explicit = bool(params.get("season"))
                    if (
                        best_mode
                        and not explicit
                        and {"w", "l"} <= set(sub.columns)
                    ):
                        w_ = pd.to_numeric(
                            sub["w"], errors="coerce"
                        )
                        l_ = pd.to_numeric(
                            sub["l"], errors="coerce"
                        )
                        pick = sub.loc[
                            (w_ / (w_ + l_)).idxmax()
                        ]
                    else:
                        pick = (
                            sub.iloc[0]
                            if latest_pick
                            else sub.iloc[-1]
                        )
                    rows.append(
                        {
                            "team": str(pick["team"]),
                            "record": pick.to_dict(),
                        }
                    )

            mode = "best_season" if best_mode else None

            return QueryResult(
                True,
                {"kind": "team_summary", "rows": rows, "mode": mode},
            )

        df = self._load("Team Stats Per Game.csv")

        # Original extraction state (before any fallback).
        stat_requested = bool(params.get("stat"))

        # --------------------------------------------------------
        # Broad team-stats question: fall back to scoring so the
        # generator can render the full season table.
        # --------------------------------------------------------
        if not params.get("stat"):
            params = {**params, "stat": "points"}
        stat = params.get("stat")
        col = self._column_for_stat(stat, "per_game", df.columns)

        if not col:
            return QueryResult(
                False,
                {},
                "Please specify a supported team statistic such as points, rebounds, assists, or field goal percentage.",
            )

        if compare:
            teams = [params.get("team1"), params.get("team2")]
        else:
            teams = [params.get("team")]
        rows = []
        for team in teams:
            sub = self._filter_team(df, team)
            sub = self._filter_season(sub, params.get("season"))

            # No explicit season -> LATEST season.
            latest_pick = not params.get("season")

            if (
                latest_pick
                and not sub.empty
                and "season" in sub.columns
            ):
                sub = sub.assign(
                    _s=pd.to_numeric(
                        sub["season"], errors="coerce"
                    )
                ).sort_values(
                    "_s", ascending=False
                ).drop(columns="_s")

            if sub.empty:
                rows.append({"team": team, "value": None})
            else:
                explicit = bool(params.get("season"))

                # best-season wording -> look up the
                # team's peak year (win %) from Team
                # Summaries, then use that season's
                # per-game row.

                row = None

                if (
                    best_mode
                    and not explicit
                    and not sub.empty
                    and "season" in sub.columns
                ):
                    team_key = (
                        str(sub.iloc[0]["team"])
                        if "team" in sub.columns
                        else str(team)
                    )
                    year = self._best_season_year(
                        team_key
                    )
                    if year is not None:
                        cand = sub[
                            sub["season"].astype(str)
                            == year
                        ]
                        if not cand.empty:
                            row = cand.iloc[0]

                if row is None:
                    row = (
                        sub.iloc[0]
                        if latest_pick
                        else sub.iloc[-1]
                    )

                entry = {
                    "team": str(row["team"]),
                    "value": self._value(row, col),
                    "season": str(row["season"]),
                    "context": self._team_context(row),
                    # Record must describe the SAME season
                    # as the stat above.
                    "record": self._team_record(
                        str(row["team"]), str(row["season"])
                    ),
                }

                rows.append(entry)

        if any(r["value"] is None for r in rows):
            return QueryResult(
                False,
                {},
                "I could not find all teams for that comparison/query.",
            )

        return QueryResult(
            True,
            {
                "kind": "team_stat",
                "stat": stat,
                "stat_requested": stat_requested,
                "rows": rows,
                "mode": "best_season" if best_mode else None,
            },
        )

    # ============================================================
    # TEAM OPPONENT STAT QUERY
    # ============================================================
    def _team_opponent_query(self, params: dict[str, Any]) -> QueryResult:
        df = self._load("Opponent Stats Per Game.csv")
        stat_requested = bool(params.get("stat"))
        if not params.get("stat"):
            params = {**params, "stat": "points"}
        stat = params.get("stat")

        # Remove "opp_" temporarily so the normal stat mapping
        # can be reused.
        simplified_columns = pd.Index(
            [
                c.replace("opp_", "", 1) if c.startswith("opp_") else c
                for c in df.columns
            ]
        )
        base_col = self._column_for_stat(stat, "per_game", simplified_columns)
        if base_col:
            col = (
                base_col if base_col.startswith("opp_") else "opp_" + base_col
            )
        else:
            col = None
        if col not in df.columns:
            return QueryResult(
                False, {}, "I could not map that opponent statistic."
            )

        sub = self._filter_team(df, params.get("team"))
        sub = self._filter_season(sub, params.get("season"))

        if sub.empty:
            return QueryResult(False, {}, "I could not find that team/season.")

        # No explicit season -> use the LATEST one.
        if not params.get("season") and "season" in sub.columns:
            sub = (
                sub.assign(_s=pd.to_numeric(sub["season"], errors="coerce"))
                .sort_values("_s", ascending=False)
                .drop(columns="_s")
            )

        row = sub.iloc[0]

        # --------------------------------------------------------
        # Context bundle of headline opponent stats so the
        # response can render a defensive stat card.
        # --------------------------------------------------------
        opp_context = []
        opp_bundle = [
            ("Opp PPG", "opp_pts_per_game", False),
            (
                "Opp REB",
                (
                    "opp_trb_per_game"
                    if "opp_trb_per_game" in df.columns
                    else None
                ),
                False,
            ),
            (
                "Opp AST",
                (
                    "opp_ast_per_game"
                    if "opp_ast_per_game" in df.columns
                    else None
                ),
                False,
            ),
            ("Opp FG%", "opp_fg_percent", True),
            (
                "Opp 3P%",
                (
                    "opp_x3p_percent"
                    if "opp_x3p_percent" in df.columns
                    else (
                        "opp_fg3_percent"
                        if "opp_fg3_percent" in df.columns
                        else None
                    )
                ),
                True,
            ),
        ]

        for label, column, is_pct in opp_bundle:
            if column is None or column not in row.index:
                continue
            raw = row.get(column)

            if pd.isna(raw):
                continue

            value = self._value(pd.Series({column: raw}), column)

            if is_pct:
                value = self._fmt_pct(value)
            opp_context.append({"label": label, "value": value})

        return QueryResult(
            True,
            {
                "kind": "team_opponent_stat",
                "team": str(row["team"]),
                "season": str(row["season"]),
                "stat": stat,
                "stat_requested": stat_requested,
                "value": self._value(row, col),
                "context": opp_context,
            },
        )