import logging
import os
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
from difflib import get_close_matches

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "nba"

_data_loaded = False
player_season_df = None
player_per_game_df = None
player_career_df = None
team_abbrev_df = None
team_stats_df = None
team_summaries_df = None
all_star_df = None
draft_df = None
award_df = None
per_36_df = None
per_100_df = None
advanced_df = None
player_totals_df = None
player_shooting_df = None
play_by_play_df = None


def load_all_data():
    global _data_loaded, player_season_df, player_per_game_df, player_career_df
    global team_abbrev_df, team_stats_df, team_summaries_df, all_star_df, draft_df, award_df
    global per_36_df, per_100_df, advanced_df, player_totals_df, player_shooting_df, play_by_play_df

    if _data_loaded:
        return

    try:
        player_season_df = pd.read_csv(DATA_DIR / "Player Season Info.csv")
        player_per_game_df = pd.read_csv(DATA_DIR / "Player Per Game.csv")
        player_career_df = pd.read_csv(DATA_DIR / "Player Career Info.csv")
        team_abbrev_df = pd.read_csv(DATA_DIR / "Team Abbrev.csv")
        team_stats_df = pd.read_csv(DATA_DIR / "Team Stats Per Game.csv")
        team_summaries_df = pd.read_csv(DATA_DIR / "Team Summaries.csv")
        all_star_df = pd.read_csv(DATA_DIR / "All-Star Selections.csv")
        draft_df = pd.read_csv(DATA_DIR / "Draft Pick History.csv")
        per_36_df = pd.read_csv(DATA_DIR / "Per 36 Minutes.csv")
        per_100_df = pd.read_csv(DATA_DIR / "Per 100 Poss.csv")
        advanced_df = pd.read_csv(DATA_DIR / "Advanced.csv")
        player_totals_df = pd.read_csv(DATA_DIR / "Player Totals.csv")
        player_shooting_df = pd.read_csv(DATA_DIR / "Player Shooting.csv")
        play_by_play_df = pd.read_csv(DATA_DIR / "Player Play By Play.csv")
        
        award_path = DATA_DIR / "Player Award Shares.csv"
        if award_path.exists():
            award_df = pd.read_csv(award_path)
        else:
            award_df = pd.DataFrame()
            logger.warning(f"Award data file not found: {award_path}")

        _data_loaded = True
        logger.info(f"Loaded {len(player_season_df)} player-season records")
        logger.info(f"Loaded {len(player_per_game_df)} player per-game records")
        logger.info(f"Loaded {len(player_career_df)} player career records")
        logger.info(f"Loaded {len(team_abbrev_df)} team records")
        logger.info(f"Loaded {len(all_star_df)} All-Star records")
        logger.info(f"Loaded {len(draft_df)} draft records")
        logger.info(f"Loaded {len(award_df)} award records")
        logger.info(f"Loaded {len(per_36_df)} per-36 records")
        logger.info(f"Loaded {len(per_100_df)} per-100 records")
        logger.info(f"Loaded {len(advanced_df)} advanced records")
        logger.info(f"Loaded {len(player_totals_df)} player totals records")
        logger.info(f"Loaded {len(player_shooting_df)} player shooting records")
        logger.info(f"Loaded {len(play_by_play_df)} play-by-play records")
    except FileNotFoundError as e:
        logger.error(f"Data file not found: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        raise


def _ensure_loaded():
    if not _data_loaded:
        load_all_data()


def _as_int(value: Any, default: int = 0) -> int:
    """int() that survives missing data.

    Columns like games-started are blank for pre-1982 seasons; a bare
    int(NaN) raises ValueError, and because every getter wraps its body in
    try/except that surfaced as "I couldn't retrieve their stats" for every
    player who retired before 1982.
    """
    try:
        if value is None or not pd.notna(value):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, digits: int = 1) -> Optional[float]:
    """round() that reports missing data as None rather than NaN.

    Rebounds were not tracked before 1951 and steals/blocks/turnovers not
    before 1974, so round(NaN) used to print literally "Rebounds: nan" in
    George Mikan's 1950 line. Callers treat None as "omit this stat".
    """
    try:
        if value is None or not pd.notna(value):
            return None
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _normalize_name(name: str) -> str:
    return name.strip().lower()


_PLAYER_SYNONYMS = {
    "cury": "stephen curry",
    "curry": "stephen curry",
    "steph": "stephen curry",
    "steph curry": "stephen curry",
    "lebron": "lebron james",
    "king james": "lebron james",
    "mj": "michael jordan",
    "jordan": "michael jordan",
    "kobe": "kobe bryant",
    "shaq": "shaquille o'neal",
    "kd": "kevin durant",
    "giannis": "giannis antetokounmpo",
    "jokic": "nikola jokić",
    "luka": "luka doncic",
    "tatum": "jayson tatum",
    "booker": "devin booker",
    "harden": "james harden",
    "dame": "damian lillard",
    "cp3": "chris paul",
    "ad": "anthony davis",
    "embiid": "joel embiid",
    "zion": "zion williamson",
    "trae": "trae young",
    "lamelo": "lamelo ball",
    "ja": "ja morant",
    "ant": "anthony edwards",
    "scottie": "scottie pippen",
    "magic": "magic johnson",
    "bird": "larry bird",
    "dirk": "dirk nowitzki",
    "wade": "dwyane wade",
    "melo": "carmelo anthony",
    "russ": "russell westbrook",
    "pg": "paul george",
    "jimmy": "jimmy butler",
    "butler": "jimmy butler",
    "draymond": "draymond green",
    "klay": "klay thompson",
    "beal": "bradley beal",
    "dwight": "dwight howard",
    "vince": "vince carter",
    "ray": "ray allen",
    "reggie": "reggie miller",
    "charles": "charles barkley",
    "barkley": "charles barkley",
    "ai": "allen iverson",
    "hakeem": "hakeem olajuwon",
    "stockton": "john stockton",
    "malone": "karl malone",
    "penny": "anfernee hardaway",
    "webber": "chris webber",
}


def _fuzzy_find_player(name: str, df: pd.DataFrame = None, col: str = "player") -> Optional[str]:
    _ensure_loaded()
    n = _normalize_name(name)

    # Use provided df, or default to player_per_game_df
    if df is None:
        df = player_per_game_df
    if df is None:
        logger.error("player_per_game_df is still None after _ensure_loaded()")
        return None

    all_names = df[col].dropna().unique().tolist()
    all_names_lower = [a.lower() for a in all_names]
    name_to_original = {a.lower(): a for a in all_names}

    if n in _PLAYER_SYNONYMS:
        # The synonym table stores lowercase names; return the dataset's own
        # spelling so callers echo "Stephen Curry", not "stephen curry".
        return name_to_original.get(_PLAYER_SYNONYMS[n], _PLAYER_SYNONYMS[n])

    exact = name_to_original.get(n)
    if exact:
        return exact

    close = get_close_matches(n, all_names_lower, n=1, cutoff=0.75)
    if close:
        return name_to_original[close[0]]

    # Check if query matches a last name exactly
    last_name_matches = [a for a in all_names_lower if a.split()[-1] == n]
    if len(last_name_matches) == 1:
        return name_to_original[last_name_matches[0]]

    # Substring matching with popularity weighting
    matches = [a for a in all_names_lower if n in a]
    if len(matches) == 1:
        return name_to_original[matches[0]]
    if len(matches) > 1:
        def _match_quality(candidate: str, query: str) -> float:
            # Prefer last name matches
            last_name_match = 1.0 if candidate.split()[-1] == query else 0.0
            # Prefer candidates whose name starts with the query
            starts = 0.5 if candidate.startswith(query) else 0.0
            # Prefer longer careers (proxy for fame) using career data
            popularity = 0.0
            if player_career_df is not None:
                career = player_career_df[player_career_df["player"].str.lower() == candidate]
                if not career.empty:
                    row = career.iloc[0]
                    career_from = row.get("from", 0)
                    career_to = row.get("to", 0)
                    if pd.notna(career_from) and pd.notna(career_to):
                        career_len = int(career_to) - int(career_from)
                        popularity = min(career_len / 20.0, 1.0)
            # Coverage: how much of the candidate name is matched
            coverage = len(query) / len(candidate) if len(candidate) > 0 else 0.0
            return last_name_match * 2.0 + starts * 0.5 + popularity * 1.0 + coverage * 0.3

        best = max(matches, key=lambda x: _match_quality(x, n))
        return name_to_original[best]

    return None


def find_player(name: str) -> Optional[pd.DataFrame]:
    _ensure_loaded()
    resolved = _fuzzy_find_player(name, player_season_df)
    if not resolved:
        return None
    mask = player_season_df["player"].str.lower() == resolved.lower()
    matches = player_season_df[mask]
    return matches if not matches.empty else None


def find_team(name_or_abbr: str) -> Optional[pd.DataFrame]:
    _ensure_loaded()
    n = _normalize_name(name_or_abbr)
    mask = team_abbrev_df["team"].str.lower() == n
    matches = team_abbrev_df[mask]
    if matches.empty:
        mask = team_abbrev_df["abbreviation"].str.upper() == name_or_abbr.upper()
        matches = team_abbrev_df[mask]
    if matches.empty:
        resolved = _fuzzy_find_player(name_or_abbr, team_abbrev_df, col="team")
        if resolved:
            mask = team_abbrev_df["team"].str.lower() == resolved.lower()
            matches = team_abbrev_df[mask]
    if matches.empty:
        mask = team_abbrev_df["team"].str.lower().str.contains(n, na=False, regex=False)
        matches = team_abbrev_df[mask]
    return matches if not matches.empty else None


def get_player_info(name: str) -> Optional[Dict[str, Any]]:
    _ensure_loaded()
    resolved = _fuzzy_find_player(name, player_career_df)
    if not resolved:
        return None
    n = resolved.lower()

    career = player_career_df[player_career_df["player"].str.lower() == n]
    if career.empty:
        return None

    row = career.iloc[0]

    seasons = player_season_df[player_season_df["player"].str.lower() == n]

    teams_played = []
    if not seasons.empty:
        teams_played = seasons["team"].unique().tolist()

    return {
        "name": row.get("player", name),
        "position": row.get("pos", "Unknown"),
        "height_inches": row.get("ht_in_in", "Unknown"),
        "weight_lbs": row.get("wt", "Unknown"),
        "birth_date": str(row.get("birth_date", "Unknown")),
        "college": row.get("colleges", "Unknown"),
        "career_from": row.get("from", "Unknown"),
        "career_to": row.get("to", "Unknown"),
        "debut": str(row.get("debut", "Unknown")),
        "hall_of_fame": row.get("hof", False),
        "teams_played": teams_played,
    }


def get_player_stats(name: str, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
    try:
        _ensure_loaded()
        resolved = _fuzzy_find_player(name, player_per_game_df)
        if not resolved:
            return None
        n = resolved.lower()

        mask = player_per_game_df["player"].str.lower() == n
        stats = player_per_game_df[mask]
        if stats.empty:
            return None

        if season is not None:
            try:
                season_int = int(season)
                stats = stats[stats["season"] == season_int]
            except ValueError:
                stats = stats[stats["season"].astype(str).str.contains(season, na=False, regex=False)]

        if stats.empty:
            return None

        row = stats.iloc[0]

        return {
            "player": row.get("player", name),
            "season": _as_int(row.get("season")),
            "team": row.get("team", "Unknown"),
            "position": row.get("pos", "Unknown"),
            "games": _as_int(row.get("g")),
            "games_started": _as_int(row.get("gs")),
            "minutes": _as_float(row.get("mp_per_game"), 1),
            "points": _as_float(row.get("pts_per_game"), 1),
            "rebounds": _as_float(row.get("trb_per_game"), 1),
            "assists": _as_float(row.get("ast_per_game"), 1),
            "steals": _as_float(row.get("stl_per_game"), 1),
            "blocks": _as_float(row.get("blk_per_game"), 1),
            "turnovers": _as_float(row.get("tov_per_game"), 1),
            "fg_pct": round(row.get("fg_percent", 0) * 100, 1) if pd.notna(row.get("fg_percent")) else None,
            "three_pct": round(row.get("x3p_percent", 0) * 100, 1) if pd.notna(row.get("x3p_percent")) else None,
            "ft_pct": round(row.get("ft_percent", 0) * 100, 1) if pd.notna(row.get("ft_percent")) else None,
        }
    except Exception as e:
        logger.error(f"Error in get_player_stats for {name}, season {season}: {e}", exc_info=True)
        return None


def _filter_by_player_season(df, name, season):
    """Filter a dataframe by player name and season, returning the matching row(s)."""
    _ensure_loaded()
    resolved = _fuzzy_find_player(name, df)
    if not resolved:
        return None
    n = resolved.lower()
    mask = df["player"].str.lower() == n
    filtered = df[mask]
    if filtered.empty:
        return None
    if season is not None:
        try:
            season_int = int(season)
            filtered = filtered[filtered["season"] == season_int]
        except ValueError:
            filtered = filtered[filtered["season"].astype(str).str.contains(season, na=False, regex=False)]
    if filtered.empty:
        return None
    return filtered, resolved


def get_per_36_stats(name: str, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get per-36-minute stats for a player."""
    try:
        result = _filter_by_player_season(per_36_df, name, season)
        if result is None:
            return None
        stats_df, resolved = result
        row = stats_df.iloc[0]
        return {
            "player": row.get("player", name),
            "season": _as_int(row.get("season")),
            "team": row.get("team", "Unknown"),
            "position": row.get("pos", "Unknown"),
            "games": _as_int(row.get("g")),
            "minutes": _as_float(row.get("mp"), 1),
            "points": _as_float(row.get("pts_per_36_min"), 1),
            "rebounds": _as_float(row.get("trb_per_36_min"), 1),
            "assists": _as_float(row.get("ast_per_36_min"), 1),
            "steals": _as_float(row.get("stl_per_36_min"), 1),
            "blocks": _as_float(row.get("blk_per_36_min"), 1),
            "turnovers": _as_float(row.get("tov_per_36_min"), 1),
            "fg_pct": round(row.get("fg_percent", 0) * 100, 1) if pd.notna(row.get("fg_percent")) else None,
            "three_pct": round(row.get("x3p_percent", 0) * 100, 1) if pd.notna(row.get("x3p_percent")) else None,
            "ft_pct": round(row.get("ft_percent", 0) * 100, 1) if pd.notna(row.get("ft_percent")) else None,
        }
    except Exception as e:
        logger.error(f"Error in get_per_36_stats for {name}, season {season}: {e}", exc_info=True)
        return None


def get_per_100_stats(name: str, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get per-100-possession stats for a player."""
    try:
        result = _filter_by_player_season(per_100_df, name, season)
        if result is None:
            return None
        stats_df, resolved = result
        row = stats_df.iloc[0]
        return {
            "player": row.get("player", name),
            "season": _as_int(row.get("season")),
            "team": row.get("team", "Unknown"),
            "position": row.get("pos", "Unknown"),
            "games": _as_int(row.get("g")),
            "minutes": _as_float(row.get("mp"), 1),
            "points": _as_float(row.get("pts_per_100_poss"), 1),
            "rebounds": _as_float(row.get("trb_per_100_poss"), 1),
            "assists": _as_float(row.get("ast_per_100_poss"), 1),
            "steals": _as_float(row.get("stl_per_100_poss"), 1),
            "blocks": _as_float(row.get("blk_per_100_poss"), 1),
            "turnovers": _as_float(row.get("tov_per_100_poss"), 1),
            "fg_pct": round(row.get("fg_percent", 0) * 100, 1) if pd.notna(row.get("fg_percent")) else None,
            "three_pct": round(row.get("x3p_percent", 0) * 100, 1) if pd.notna(row.get("x3p_percent")) else None,
            "ft_pct": round(row.get("ft_percent", 0) * 100, 1) if pd.notna(row.get("ft_percent")) else None,
            "off_rating": round(row.get("o_rtg", 0), 1) if pd.notna(row.get("o_rtg")) else None,
            "def_rating": round(row.get("d_rtg", 0), 1) if pd.notna(row.get("d_rtg")) else None,
        }
    except Exception as e:
        logger.error(f"Error in get_per_100_stats for {name}, season {season}: {e}", exc_info=True)
        return None


def get_advanced_stats(name: str, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get advanced stats (PER, TS%, VORP, etc.) for a player."""
    try:
        result = _filter_by_player_season(advanced_df, name, season)
        if result is None:
            return None
        stats_df, resolved = result
        row = stats_df.iloc[0]
        return {
            "player": row.get("player", name),
            "season": _as_int(row.get("season")),
            "team": row.get("team", "Unknown"),
            "position": row.get("pos", "Unknown"),
            "games": _as_int(row.get("g")),
            "minutes": _as_float(row.get("mp"), 1),
            "per": round(row.get("per", 0), 1) if pd.notna(row.get("per")) else None,
            "ts_pct": round(row.get("ts_percent", 0) * 100, 1) if pd.notna(row.get("ts_percent")) else None,
            "three_pct_ar": round(row.get("x3p_ar", 0) * 100, 1) if pd.notna(row.get("x3p_ar")) else None,
            "ft_rate": round(row.get("f_tr", 0), 3) if pd.notna(row.get("f_tr")) else None,
            "orb_pct": round(row.get("orb_percent", 0), 1) if pd.notna(row.get("orb_percent")) else None,
            "drb_pct": round(row.get("drb_percent", 0), 1) if pd.notna(row.get("drb_percent")) else None,
            "trb_pct": round(row.get("trb_percent", 0), 1) if pd.notna(row.get("trb_percent")) else None,
            "ast_pct": round(row.get("ast_percent", 0), 1) if pd.notna(row.get("ast_percent")) else None,
            "stl_pct": round(row.get("stl_percent", 0), 1) if pd.notna(row.get("stl_percent")) else None,
            "blk_pct": round(row.get("blk_percent", 0), 1) if pd.notna(row.get("blk_percent")) else None,
            "tov_pct": round(row.get("tov_percent", 0), 1) if pd.notna(row.get("tov_percent")) else None,
            "usg_pct": round(row.get("usg_percent", 0), 1) if pd.notna(row.get("usg_percent")) else None,
            "ows": round(row.get("ows", 0), 1) if pd.notna(row.get("ows")) else None,
            "dws": round(row.get("dws", 0), 1) if pd.notna(row.get("dws")) else None,
            "ws": round(row.get("ws", 0), 1) if pd.notna(row.get("ws")) else None,
            "ws_48": round(row.get("ws_48", 0), 3) if pd.notna(row.get("ws_48")) else None,
            "bpm": round(row.get("bpm", 0), 1) if pd.notna(row.get("bpm")) else None,
            "vorp": round(row.get("vorp", 0), 1) if pd.notna(row.get("vorp")) else None,
        }
    except Exception as e:
        logger.error(f"Error in get_advanced_stats for {name}, season {season}: {e}", exc_info=True)
        return None


def _dedupe_traded_seasons(rows: pd.DataFrame) -> pd.DataFrame:
    """Drop per-team rows for seasons that also carry a combined row.

    Basketball Reference records a traded player's season twice: one combined
    row (team "2TM"/"3TM"/..., historically "TOT") plus one row per team. Summing
    the frame as-is counts those seasons twice - Vince Carter came out with
    28,636 career points instead of 25,728.
    """
    if rows.empty or "team" not in rows.columns or "season" not in rows.columns:
        return rows
    combined = rows["team"].astype(str).str.upper().str.match(r"^(\d+TM|TOT)$")
    seasons_with_combined = set(rows.loc[combined, "season"])
    if not seasons_with_combined:
        return rows
    keep = combined | ~rows["season"].isin(seasons_with_combined)
    return rows[keep]


def get_career_totals(name: str) -> Optional[Dict[str, Any]]:
    """Get career totals for a player (aggregated across all seasons)."""
    try:
        resolved = _fuzzy_find_player(name, player_totals_df)
        if not resolved:
            return None
        n = resolved.lower()
        mask = player_totals_df["player"].str.lower() == n
        totals = player_totals_df[mask]
        if totals.empty:
            return None
        totals = _dedupe_traded_seasons(totals)
        return {
            "player": totals.iloc[0].get("player", name),
            "seasons": f"{int(totals['season'].min())}-{int(totals['season'].max())}",
            "games": int(totals["g"].sum()),
            "points": int(totals["pts"].sum()),
            "rebounds": int(totals["trb"].sum()),
            "assists": int(totals["ast"].sum()),
            "steals": int(totals["stl"].sum()),
            "blocks": int(totals["blk"].sum()),
            "turnovers": int(totals["tov"].sum()),
            "fg_pct": round(totals["fg"].sum() / totals["fga"].sum() * 100, 1) if totals["fga"].sum() > 0 else None,
            "three_pct": round(totals["x3p"].sum() / totals["x3pa"].sum() * 100, 1) if totals["x3pa"].sum() > 0 else None,
            "ft_pct": round(totals["ft"].sum() / totals["fta"].sum() * 100, 1) if totals["fta"].sum() > 0 else None,
        }
    except Exception as e:
        logger.error(f"Error in get_career_totals for {name}: {e}", exc_info=True)
        return None


def get_shooting_stats(name: str, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get shooting stats for a player."""
    try:
        result = _filter_by_player_season(player_shooting_df, name, season)
        if result is None:
            return None
        stats_df, resolved = result
        row = stats_df.iloc[0]
        return {
            "player": row.get("player", name),
            "season": _as_int(row.get("season")),
            "team": row.get("team", "Unknown"),
            "position": row.get("pos", "Unknown"),
            "games": _as_int(row.get("g")),
            "fg_pct": round(row.get("fg_percent", 0) * 100, 1) if pd.notna(row.get("fg_percent")) else None,
            "avg_dist_fga": round(row.get("avg_dist_fga", 0), 1) if pd.notna(row.get("avg_dist_fga")) else None,
            "pct_fga_from_2p": round(row.get("percent_fga_from_x2p_range", 0) * 100, 1) if pd.notna(row.get("percent_fga_from_x2p_range")) else None,
            "pct_fga_from_3p": round(row.get("percent_fga_from_x3p_range", 0) * 100, 1) if pd.notna(row.get("percent_fga_from_x3p_range")) else None,
            "fg_pct_from_2p": round(row.get("fg_percent_from_x2p_range", 0) * 100, 1) if pd.notna(row.get("fg_percent_from_x2p_range")) else None,
            "fg_pct_from_3p": round(row.get("fg_percent_from_x3p_range", 0) * 100, 1) if pd.notna(row.get("fg_percent_from_x3p_range")) else None,
            "corner_3_pct": round(row.get("corner_3_point_percent", 0) * 100, 1) if pd.notna(row.get("corner_3_point_percent")) else None,
            "pct_dunks": round(row.get("percent_dunks_of_fga", 0) * 100, 1) if pd.notna(row.get("percent_dunks_of_fga")) else None,
            "num_dunks": int(row.get("num_of_dunks", 0)) if pd.notna(row.get("num_of_dunks")) else None,
            "pct_assisted_2p": round(row.get("percent_assisted_x2p_fg", 0) * 100, 1) if pd.notna(row.get("percent_assisted_x2p_fg")) else None,
            "pct_assisted_3p": round(row.get("percent_assisted_x3p_fg", 0) * 100, 1) if pd.notna(row.get("percent_assisted_x3p_fg")) else None,
        }
    except Exception as e:
        logger.error(f"Error in get_shooting_stats for {name}, season {season}: {e}", exc_info=True)
        return None


def get_team_info(name_or_abbr: str) -> Optional[Dict[str, Any]]:
    _ensure_loaded()
    n = _normalize_name(name_or_abbr)

    mask = team_summaries_df["team"].str.lower() == n
    matches = team_summaries_df[mask]
    if matches.empty:
        mask = team_summaries_df["abbreviation"].str.upper() == name_or_abbr.upper()
        matches = team_summaries_df[mask]
    if matches.empty:
        resolved = _fuzzy_find_player(name_or_abbr, team_summaries_df, col="team")
        if resolved:
            mask = team_summaries_df["team"].str.lower() == resolved.lower()
            matches = team_summaries_df[mask]
    if matches.empty:
        mask = team_summaries_df["team"].str.lower().str.contains(n, na=False, regex=False)
        matches = team_summaries_df[mask]

    if matches.empty:
        return None

    latest = matches.sort_values("season", ascending=False).iloc[0]

    return {
        "name": latest.get("team", name_or_abbr),
        "abbreviation": latest.get("abbreviation", "Unknown"),
        "season": _as_int(latest.get("season")),
        "wins": _as_int(latest.get("w")),
        "losses": _as_int(latest.get("l")),
        "arena": latest.get("arena", "Unknown"),
        "age": _as_float(latest.get("age"), 1),
        "off_rating": round(latest.get("o_rtg", 0), 1) if pd.notna(latest.get("o_rtg")) else None,
        "def_rating": round(latest.get("d_rtg", 0), 1) if pd.notna(latest.get("d_rtg")) else None,
        "net_rating": round(latest.get("n_rtg", 0), 1) if pd.notna(latest.get("n_rtg")) else None,
        "pace": round(latest.get("pace", 0), 1) if pd.notna(latest.get("pace")) else None,
        "attendance": _as_int(latest.get("attend")),
    }


def get_team_stats(name_or_abbr: str, season: str) -> Optional[Dict[str, Any]]:
    _ensure_loaded()
    n = _normalize_name(name_or_abbr)

    mask = team_stats_df["team"].str.lower() == n
    stats = team_stats_df[mask]
    if stats.empty:
        mask = team_stats_df["abbreviation"].str.upper() == name_or_abbr.upper()
        stats = team_stats_df[mask]
    if stats.empty:
        resolved = _fuzzy_find_player(name_or_abbr, team_stats_df, col="team")
        if resolved:
            mask = team_stats_df["team"].str.lower() == resolved.lower()
            stats = team_stats_df[mask]
    if stats.empty:
        mask = team_stats_df["team"].str.lower().str.contains(n, na=False, regex=False)
        stats = team_stats_df[mask]

    if stats.empty:
        return None

    try:
        season_int = int(season)
        stats = stats[stats["season"] == season_int]
    except ValueError:
        stats = stats[stats["season"].astype(str).str.contains(season, na=False, regex=False)]

    if stats.empty:
        return None

    row = stats.iloc[0]

    # Look up wins/losses from team summaries
    wins = None
    losses = None
    try:
        sum_mask = team_summaries_df["team"].str.lower() == row.get("team", "").lower()
        sum_stats = team_summaries_df[sum_mask]
        if not sum_stats.empty:
            s_int = _as_int(row.get("season"))
            sum_stats = sum_stats[sum_stats["season"] == s_int]
            if not sum_stats.empty:
                sum_row = sum_stats.iloc[0]
                wins = int(sum_row.get("w", 0)) if pd.notna(sum_row.get("w")) else None
                losses = int(sum_row.get("l", 0)) if pd.notna(sum_row.get("l")) else None
    except Exception:
        pass

    return {
        "team": row.get("team", name_or_abbr),
        "season": _as_int(row.get("season")),
        "games": _as_int(row.get("g")),
        "wins": wins,
        "losses": losses,
        "points": _as_float(row.get("pts_per_game"), 1),
        "rebounds": _as_float(row.get("trb_per_game"), 1),
        "assists": _as_float(row.get("ast_per_game"), 1),
        "steals": _as_float(row.get("stl_per_game"), 1),
        "blocks": _as_float(row.get("blk_per_game"), 1),
        "turnovers": _as_float(row.get("tov_per_game"), 1),
        "fouls": _as_float(row.get("pf_per_game"), 1),
        "fg_pct": round(row.get("fg_percent", 0) * 100, 1) if pd.notna(row.get("fg_percent")) else None,
        "three_pct": round(row.get("x3p_percent", 0) * 100, 1) if pd.notna(row.get("x3p_percent")) else None,
        "ft_pct": round(row.get("ft_percent", 0) * 100, 1) if pd.notna(row.get("ft_percent")) else None,
    }


def get_career_per_game(name: str) -> Optional[Dict[str, Any]]:
    """Career per-game averages, shaped like `get_player_stats`.

    Used when a comparison names no season: "who had the stronger career" must
    not be answered from one arbitrary row of the per-game table, which for a
    retired player is their farewell season (Kobe Bryant at 17.6 PPG).
    """
    try:
        _ensure_loaded()
        resolved = _fuzzy_find_player(name, player_totals_df)
        if not resolved:
            return None
        mask = player_totals_df["player"].str.lower() == resolved.lower()
        totals = _dedupe_traded_seasons(player_totals_df[mask])
        if totals.empty:
            return None

        games = totals["g"].sum()
        if not games:
            return None

        def per_game(column: str) -> Optional[float]:
            if column not in totals.columns:
                return None
            values = totals[column]
            # Steals and blocks were not recorded before 1974 - divide by the
            # games from the seasons that actually carry the stat.
            played = totals.loc[values.notna(), "g"].sum()
            if not played:
                return None
            return round(values.sum() / played, 1)

        def percentage(made: str, attempted: str) -> Optional[float]:
            if made not in totals.columns or attempted not in totals.columns:
                return None
            att = totals[attempted].sum()
            return round(totals[made].sum() / att * 100, 1) if att > 0 else None

        return {
            "player": totals.iloc[0].get("player", name),
            "season": f"{int(totals['season'].min())}-{int(totals['season'].max())}",
            "team": "career",
            "games": int(games),
            "points": per_game("pts"),
            "rebounds": per_game("trb"),
            "assists": per_game("ast"),
            "steals": per_game("stl"),
            "blocks": per_game("blk"),
            "turnovers": per_game("tov"),
            "fg_pct": percentage("fg", "fga"),
            "three_pct": percentage("x3p", "x3pa"),
            "ft_pct": percentage("ft", "fta"),
        }
    except Exception as e:
        logger.error(f"Error in get_career_per_game for {name}: {e}", exc_info=True)
        return None


def compare_players(
    name1: str, name2: str, season: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    if season:
        stats1 = get_player_stats(name1, season)
        stats2 = get_player_stats(name2, season)
    else:
        stats1 = get_career_per_game(name1)
        stats2 = get_career_per_game(name2)
    if stats1 is None or stats2 is None:
        return None
    return {"player1": stats1, "player2": stats2}


def get_all_star(name: str) -> Optional[Dict[str, Any]]:
    _ensure_loaded()
    resolved = _fuzzy_find_player(name, all_star_df)
    if not resolved:
        return None
    n = resolved.lower()
    mask = all_star_df["player"].str.lower() == n
    selections = all_star_df[mask]
    if selections.empty:
        return None
    return {
        "player": selections.iloc[0]["player"],
        "count": len(selections),
        "seasons": sorted(selections["season"].tolist()),
    }


def get_draft_info(name: str) -> Optional[Dict[str, Any]]:
    _ensure_loaded()
    resolved = _fuzzy_find_player(name, draft_df)
    if not resolved:
        return None
    n = resolved.lower()
    mask = draft_df["player"].str.lower() == n
    picks = draft_df[mask]
    if picks.empty:
        return None
    row = picks.iloc[0]
    college = row.get("college", "Unknown")
    if pd.isna(college):
        college = "Unknown"
    return {
        "player": row.get("player", name),
        "season": _as_int(row.get("season")),
        "overall_pick": _as_int(row.get("overall_pick")),
        "round": _as_int(row.get("round")),
        "team": row.get("tm", "Unknown"),
        "college": college,
    }


def get_league_info() -> Dict[str, Any]:
    _ensure_loaded()
    return {
        "leagues": ["NBA", "ABA", "BAA"],
        "season_range": "1947-2026",
        "total_players": int(player_career_df["player"].nunique()),
        "total_teams": int(team_abbrev_df["team"].nunique()),
    }


def get_dataset_scope() -> Dict[str, Any]:
    _ensure_loaded()
    return {
        "season_range": "1947-2026",
        "leagues": ["NBA", "ABA", "BAA"],
        "total_players": int(player_career_df["player"].nunique()),
        "total_teams": int(team_abbrev_df["team"].nunique()),
        "total_seasons": int(player_per_game_df["season"].nunique()),
    }


def get_draft_year(year: str) -> Optional[Dict[str, Any]]:
    _ensure_loaded()
    try:
        year_int = int(year)
    except ValueError:
        return None
    picks = draft_df[draft_df["season"] == year_int]
    if picks.empty:
        return None
    top_5 = picks.sort_values("overall_pick").head(5)
    picks_list = []
    for _, row in top_5.iterrows():
        picks_list.append({
            "pick": _as_int(row.get("overall_pick")),
            "player": row.get("player", "Unknown"),
            "team": row.get("tm", "Unknown"),
            "college": row.get("college", "Unknown"),
        })
    return {
        "year": year_int,
        "total_picks": len(picks),
        "top_5": picks_list,
    }


def get_award_winner(award: str, season: int) -> Optional[Dict[str, Any]]:
    """Get the winner of a specific award in a given season."""
    _ensure_loaded()
    if award_df is None or award_df.empty:
        return None
    
    award_lower = award.lower().strip()
    
    # Map user input to actual award names in the data
    award_map = {
        'mvp': 'nba mvp',
        'most valuable player': 'nba mvp',
        'dpoy': 'nba dpoy',
        'defensive player of the year': 'nba dpoy',
        'defensive player': 'nba dpoy',
        'roy': 'nba roy',
        'rookie of the year': 'nba roy',
        'smoy': 'nba smoy',
        'sixth man of the year': 'nba smoy',
        'sixth man': 'nba smoy',
        'mip': 'nba mip',
        'most improved player': 'nba mip',
        'most improved': 'nba mip',
        'cpoy': 'nba clutch_poy',
        'clutch player of the year': 'nba clutch_poy',
        'clutch player': 'nba clutch_poy',
    }
    
    award_full = award_map.get(award_lower, award_lower)
    
    mask = (
        (award_df['award'].str.lower() == award_full) &
        (award_df['season'] == season) &
        (award_df['winner'] == True)
    )
    
    winners = award_df[mask]
    if winners.empty:
        return None
    
    winner = winners.iloc[0]
    return {
        'player': winner.get('player', 'Unknown'),
        'award': winner.get('award', award),
        'season': int(season),
    }


def get_player_awards(player: str) -> Optional[Dict[str, Any]]:
    """Get all awards won by a specific player."""
    _ensure_loaded()
    if award_df is None or award_df.empty:
        return None
    
    matched_name = _fuzzy_find_player(player, award_df)
    if not matched_name:
        return None
    
    mask = (
        (award_df['player'].str.lower() == matched_name.lower()) &
        (award_df['winner'] == True)
    )
    
    awards_df = award_df[mask]
    if awards_df.empty:
        return {
            'player': matched_name,
            'awards': [],
            'count': 0,
            'award_counts': {},
        }
    
    # Format award names for display
    award_display_map = {
        'nba mvp': 'NBA MVP',
        'aba mvp': 'ABA MVP',
        'nba dpoy': 'NBA DPOY',
        'nba roy': 'NBA ROY',
        'aba roy': 'ABA ROY',
        'nba smoy': 'NBA SMOY',
        'nba mip': 'NBA MIP',
        'nba clutch_poy': 'NBA Clutch Player of the Year',
        'baa roy': 'BAA ROY',
    }
    
    awards = []
    award_counts = {}
    for _, row in awards_df.iterrows():
        award_name = row.get('award', 'Unknown')
        season = row.get('season', 'Unknown')
        display_name = award_display_map.get(award_name, award_name.upper())
        awards.append({'award': display_name, 'season': int(season) if pd.notna(season) else season})
        award_counts[display_name] = award_counts.get(display_name, 0) + 1
    
    return {
        "player": matched_name,
        "awards": awards,
        "count": len(awards),
        "award_counts": award_counts,
    }


# Map user input stat_type values to canonical forms
_STAT_TYPE_MAP = {
    "per 36": "per_36",
    "per 36 minutes": "per_36",
    "per 36 min": "per_36",
    "per36": "per_36",
    "per_36": "per_36",
    "per 100": "per_100",
    "per 100 possessions": "per_100",
    "per possession": "per_100",
    "per100": "per_100",
    "per_100": "per_100",
    "advanced": "advanced",
    "career totals": "career_totals",
    "career": "career_totals",
    "totals": "career_totals",
    "career_totals": "career_totals",
    "shooting": "shooting",
    "shooting splits": "shooting",
    "per game": "per_game",
    "per_game": "per_game",
}


def normalize_stat_type(stat_type: Optional[str]) -> str:
    """Normalize stat_type input to canonical form. Defaults to 'per_game'."""
    if not stat_type:
        return "per_game"
    normalized = stat_type.lower().strip()
    return _STAT_TYPE_MAP.get(normalized, "per_game")
