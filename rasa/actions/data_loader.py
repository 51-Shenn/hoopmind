import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List

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


def load_all_data():
    global _data_loaded, player_season_df, player_per_game_df, player_career_df
    global team_abbrev_df, team_stats_df, team_summaries_df, all_star_df, draft_df

    if _data_loaded:
        return

    player_season_df = pd.read_csv(DATA_DIR / "Player Season Info.csv")
    player_per_game_df = pd.read_csv(DATA_DIR / "Player Per Game.csv")
    player_career_df = pd.read_csv(DATA_DIR / "Player Career Info.csv")
    team_abbrev_df = pd.read_csv(DATA_DIR / "Team Abbrev.csv")
    team_stats_df = pd.read_csv(DATA_DIR / "Team Stats Per Game.csv")
    team_summaries_df = pd.read_csv(DATA_DIR / "Team Summaries.csv")
    all_star_df = pd.read_csv(DATA_DIR / "All-Star Selections.csv")
    draft_df = pd.read_csv(DATA_DIR / "Draft Pick History.csv")

    _data_loaded = True
    print(f"[DataLoader] Loaded {len(player_season_df)} player-season records")
    print(f"[DataLoader] Loaded {len(player_per_game_df)} player per-game records")
    print(f"[DataLoader] Loaded {len(player_career_df)} player career records")
    print(f"[DataLoader] Loaded {len(team_abbrev_df)} team records")
    print(f"[DataLoader] Loaded {len(all_star_df)} All-Star records")
    print(f"[DataLoader] Loaded {len(draft_df)} draft records")


def _ensure_loaded():
    if not _data_loaded:
        load_all_data()


def _normalize_name(name: str) -> str:
    return name.strip().lower()


def find_player(name: str) -> Optional[pd.DataFrame]:
    _ensure_loaded()
    n = _normalize_name(name)
    mask = player_season_df["player"].str.lower() == n
    matches = player_season_df[mask]
    if matches.empty:
        mask = player_season_df["player"].str.lower().str.contains(n, na=False)
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
        mask = team_abbrev_df["team"].str.lower().str.contains(n, na=False)
        matches = team_abbrev_df[mask]
    return matches if not matches.empty else None


def get_player_info(name: str) -> Optional[Dict[str, Any]]:
    _ensure_loaded()
    n = _normalize_name(name)

    career = player_career_df[player_career_df["player"].str.lower() == n]
    if career.empty:
        career = player_career_df[player_career_df["player"].str.lower().str.contains(n, na=False)]
    if career.empty:
        return None

    row = career.iloc[0]

    seasons = player_season_df[player_season_df["player"].str.lower() == n]
    if seasons.empty:
        seasons = player_season_df[player_season_df["player"].str.lower().str.contains(n, na=False)]

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
    _ensure_loaded()
    n = _normalize_name(name)

    mask = player_per_game_df["player"].str.lower() == n
    stats = player_per_game_df[mask]
    if stats.empty:
        mask = player_per_game_df["player"].str.lower().str.contains(n, na=False)
        stats = player_per_game_df[mask]
    if stats.empty:
        return None

    if season is not None:
        try:
            season_int = int(season)
            stats = stats[stats["season"] == season_int]
        except ValueError:
            stats = stats[stats["season"].astype(str).str.contains(season, na=False)]

    if stats.empty:
        return None

    row = stats.iloc[0]

    return {
        "player": row.get("player", name),
        "season": int(row.get("season", 0)),
        "team": row.get("team", "Unknown"),
        "position": row.get("pos", "Unknown"),
        "games": int(row.get("g", 0)),
        "games_started": int(row.get("gs", 0)),
        "minutes": round(row.get("mp_per_game", 0), 1),
        "points": round(row.get("pts_per_game", 0), 1),
        "rebounds": round(row.get("trb_per_game", 0), 1),
        "assists": round(row.get("ast_per_game", 0), 1),
        "steals": round(row.get("stl_per_game", 0), 1),
        "blocks": round(row.get("blk_per_game", 0), 1),
        "turnovers": round(row.get("tov_per_game", 0), 1),
        "fg_pct": round(row.get("fg_percent", 0) * 100, 1) if pd.notna(row.get("fg_percent")) else None,
        "three_pct": round(row.get("x3p_percent", 0) * 100, 1) if pd.notna(row.get("x3p_percent")) else None,
        "ft_pct": round(row.get("ft_percent", 0) * 100, 1) if pd.notna(row.get("ft_percent")) else None,
    }


def get_team_info(name_or_abbr: str) -> Optional[Dict[str, Any]]:
    _ensure_loaded()
    n = _normalize_name(name_or_abbr)

    mask = team_summaries_df["team"].str.lower() == n
    matches = team_summaries_df[mask]
    if matches.empty:
        mask = team_summaries_df["abbreviation"].str.upper() == name_or_abbr.upper()
        matches = team_summaries_df[mask]
    if matches.empty:
        mask = team_summaries_df["team"].str.lower().str.contains(n, na=False)
        matches = team_summaries_df[mask]

    if matches.empty:
        return None

    latest = matches.sort_values("season", ascending=False).iloc[0]

    return {
        "name": latest.get("team", name_or_abbr),
        "abbreviation": latest.get("abbreviation", "Unknown"),
        "season": int(latest.get("season", 0)),
        "wins": int(latest.get("w", 0)),
        "losses": int(latest.get("l", 0)),
        "arena": latest.get("arena", "Unknown"),
        "age": round(latest.get("age", 0), 1),
        "off_rating": round(latest.get("o_rtg", 0), 1) if pd.notna(latest.get("o_rtg")) else None,
        "def_rating": round(latest.get("d_rtg", 0), 1) if pd.notna(latest.get("d_rtg")) else None,
        "net_rating": round(latest.get("n_rtg", 0), 1) if pd.notna(latest.get("n_rtg")) else None,
        "pace": round(latest.get("pace", 0), 1) if pd.notna(latest.get("pace")) else None,
        "attendance": int(latest.get("attend", 0)),
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
        mask = team_stats_df["team"].str.lower().str.contains(n, na=False)
        stats = team_stats_df[mask]

    if stats.empty:
        return None

    try:
        season_int = int(season)
        stats = stats[stats["season"] == season_int]
    except ValueError:
        stats = stats[stats["season"].astype(str).str.contains(season, na=False)]

    if stats.empty:
        return None

    row = stats.iloc[0]

    return {
        "team": row.get("team", name_or_abbr),
        "season": int(row.get("season", 0)),
        "games": int(row.get("g", 0)),
        "points": round(row.get("pts_per_game", 0), 1),
        "rebounds": round(row.get("trb_per_game", 0), 1),
        "assists": round(row.get("ast_per_game", 0), 1),
        "steals": round(row.get("stl_per_game", 0), 1),
        "blocks": round(row.get("blk_per_game", 0), 1),
        "fg_pct": round(row.get("fg_percent", 0) * 100, 1) if pd.notna(row.get("fg_percent")) else None,
        "three_pct": round(row.get("x3p_percent", 0) * 100, 1) if pd.notna(row.get("x3p_percent")) else None,
        "ft_pct": round(row.get("ft_percent", 0) * 100, 1) if pd.notna(row.get("ft_percent")) else None,
    }


def compare_players(name1: str, name2: str) -> Optional[Dict[str, Any]]:
    stats1 = get_player_stats(name1)
    stats2 = get_player_stats(name2)
    if stats1 is None or stats2 is None:
        return None
    return {"player1": stats1, "player2": stats2}


def get_all_star(name: str) -> Optional[Dict[str, Any]]:
    _ensure_loaded()
    n = _normalize_name(name)
    mask = all_star_df["player"].str.lower() == n
    selections = all_star_df[mask]
    if selections.empty:
        mask = all_star_df["player"].str.lower().str.contains(n, na=False)
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
    n = _normalize_name(name)
    mask = draft_df["player"].str.lower() == n
    picks = draft_df[mask]
    if picks.empty:
        mask = draft_df["player"].str.lower().str.contains(n, na=False)
        picks = draft_df[mask]
    if picks.empty:
        return None
    row = picks.iloc[0]
    return {
        "player": row.get("player", name),
        "season": int(row.get("season", 0)),
        "overall_pick": int(row.get("overall_pick", 0)),
        "round": int(row.get("round", 0)),
        "team": row.get("tm", "Unknown"),
        "college": row.get("college", "Unknown"),
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
