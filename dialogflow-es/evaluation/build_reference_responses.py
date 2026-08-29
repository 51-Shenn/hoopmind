"""
Build reference_response for evaluation/test_results.csv by computing each
answer INDEPENDENTLY from the raw Basketball-Reference CSVs (data/), not by
calling response_generator.py. Keeping this separate from the app's own
phrasing is what makes the BLEU/ROUGE comparison meaningful rather than
circular.

Usage:
    python evaluation/build_reference_responses.py
"""
from __future__ import annotations
import csv
from pathlib import Path
import pandas as pd

EVAL_DIR = Path(__file__).resolve().parent
DATA_DIR = EVAL_DIR.parent / "data"
RESULT_FILE = EVAL_DIR / "test_results.csv"
FIELDS = ["test_id", "expected_intent", "test_phrase", "predicted_intent",
          "confidence", "correct", "chatbot_response",
          "response_quality_1_to_5", "reference_response"]

team_pg = pd.read_csv(DATA_DIR / "Team Stats Per Game.csv")
team_sum = pd.read_csv(DATA_DIR / "Team Summaries.csv")
player_pg = pd.read_csv(DATA_DIR / "Player Per Game.csv")
draft = pd.read_csv(DATA_DIR / "Draft Pick History.csv")
awards = pd.read_csv(DATA_DIR / "Player Award Shares.csv")
allstar = pd.read_csv(DATA_DIR / "All-Star Selections.csv")
career = pd.read_csv(DATA_DIR / "Player Career Info.csv")
player_totals = pd.read_csv(DATA_DIR / "Player Totals.csv")

TEAM_FULL = {
    "boston": "Boston Celtics", "golden state": "Golden State Warriors",
    "warriors": "Golden State Warriors", "los angeles lakers": "Los Angeles Lakers",
    "lakers": "Los Angeles Lakers", "chicago bulls": "Chicago Bulls",
    "bulls": "Chicago Bulls", "celtics": "Boston Celtics",
    "miami heat": "Miami Heat", "toronto raptors": "Toronto Raptors",
    "san antonio spurs": "San Antonio Spurs", "new york knicks": "New York Knicks",
    "dallas mavericks": "Dallas Mavericks", "phoenix suns": "Phoenix Suns",
    "cavaliers": "Cleveland Cavaliers",
}

TEAM_ABBR = {"CLE": "Cleveland Cavaliers", "GSW": "Golden State Warriors",
             "LAL": "Los Angeles Lakers", "CHI": "Chicago Bulls", "DEN": "Denver Nuggets",
             "MIL": "Milwaukee Bucks", "MIA": "Miami Heat", "PHI": "Philadelphia 76ers",
             "PHO": "Phoenix Suns", "SEA": "Seattle SuperSonics", "NOP": "New Orleans Pelicans",
             "SAS": "San Antonio Spurs", "OKC": "Oklahoma City Thunder"}


def team_season_row(team_full, season):
    r = team_pg[(team_pg["team"] == team_full) & (team_pg["season"] == season)]
    return r.iloc[0] if len(r) else None


def player_season_row(player, season):
    r = player_pg[(player_pg["player"] == player) & (player_pg["season"] == season)]
    if len(r) > 1:
        r = r[r["team"] == "TOT"] if "TOT" in r["team"].values else r.iloc[[0]]
    return r.iloc[0] if len(r) else None


REF = {}

# ---- team_stats (T001-T010) ----
def r_team_stats():
    cases = [
        ("T001", "Boston Celtics", 2024, "pts_per_game", "averaged {v:.1f} points per game"),
        ("T002", "Golden State Warriors", 2016, "pts_per_game", "averaged {v:.1f} points per game"),
        ("T003", "Los Angeles Lakers", 2020, "trb_per_game", "averaged {v:.1f} rebounds per game"),
        ("T004", "Golden State Warriors", 2017, "ast_per_game", "averaged {v:.1f} assists per game"),
        ("T005", "Chicago Bulls", 1996, "stl_per_game", "averaged {v:.1f} steals per game"),
        ("T006", "Boston Celtics", 2024, "fg_percent", "shot {v:.1%} from the field"),
        ("T007", "Golden State Warriors", 2016, "x3p_per_game", "made {v:.1f} three-pointers per game"),
        ("T008", "Miami Heat", 2013, "blk_per_game", "averaged {v:.1f} blocks per game"),
        ("T009", "Los Angeles Lakers", 2020, "tov_per_game", "averaged {v:.1f} turnovers per game"),
        ("T010", "Toronto Raptors", 2019, "ft_per_game", "made {v:.1f} free throws per game"),
    ]
    for tid, team, season, col, phrase in cases:
        row = team_season_row(team, season)
        val = row[col]
        REF[tid] = f"The {team} {phrase.format(v=val)} in the {season} season."


# ---- league_info (T011-T020) ----
def r_league_info():
    people = {
        "T011": "LeBron James", "T012": "Stephen Curry", "T013": "Kobe Bryant",
        "T015": "Kevin Durant", "T017": "Michael Jordan", "T019": "Giannis Antetokounmpo",
    }
    for tid, p in people.items():
        REF[tid] = f"{p} plays in the National Basketball Association (NBA)."
    REF["T014"] = "Yes, Nikola Jokić is an NBA player."
    REF["T016"] = "The Lakers play in the National Basketball Association (NBA)."
    REF["T018"] = "The Boston Celtics are associated with the National Basketball Association (NBA)."
    REF["T020"] = "The Golden State Warriors are part of the National Basketball Association (NBA)."


# ---- team_info (T021-T030) ----
def r_team_info():
    cases = [("T021", "Los Angeles Lakers"), ("T022", "Boston Celtics"),
             ("T023", "Golden State Warriors"), ("T024", "Chicago Bulls"),
             ("T025", "Miami Heat"), ("T026", "San Antonio Spurs"),
             ("T027", "Toronto Raptors"), ("T028", "New York Knicks"),
             ("T029", "Dallas Mavericks"), ("T030", "Phoenix Suns")]
    for tid, team in cases:
        rows = team_sum[team_sum["team"] == team].sort_values("season")
        latest = rows.iloc[-1]
        REF[tid] = (f"The {team} are an NBA franchise. In their most recent season on record "
                     f"({int(latest['season'])}), they went {int(latest['w'])}-{int(latest['l'])} "
                     f"and played home games at {latest['arena']}.")


# ---- draft_info (T031-T040) ----
def r_draft_info():
    players = {"T031": "LeBron James", "T032": "Stephen Curry", "T033": "Kobe Bryant",
               "T034": "Kevin Durant", "T035": "Michael Jordan", "T036": "Nikola Jokić",
               "T037": "Giannis Antetokounmpo", "T038": "Dwyane Wade",
               "T039": "James Harden", "T040": "Anthony Davis"}
    for tid, p in players.items():
        row = draft[draft["player"] == p]
        if not len(row):
            row = draft[draft["player"].str.contains(p.split()[-1], na=False, case=False)]
        if len(row):
            row = row.iloc[0]
            tm = TEAM_ABBR.get(row["tm"], row["tm"])
            REF[tid] = (f"{p} was selected by the {tm} in the {int(row['round'])}(st/nd/rd/th) round, "
                         f"pick #{int(row['overall_pick'])} overall, in the {int(row['season'])} draft.")
        else:
            REF[tid] = f"No draft record was found for {p} in the dataset."


# ---- compare (T041-T050): career points totals, computed independently ----
def r_compare():
    def career_pts(p):
        r = player_totals[player_totals["player"] == p]
        return r["pts"].sum()

    def season_pts(p, season):
        r = player_pg[(player_pg["player"] == p) & (player_pg["season"] == season)]
        return r["pts_per_game"].mean() if len(r) else None

    pairs = [("T041", "LeBron James", "Michael Jordan", "career points"),
             ("T043", "Kobe Bryant", "LeBron James", "career points"),
             ("T045", "Nikola Jokić", "Joel Embiid", "career points"),
             ("T049", "Giannis Antetokounmpo", "Nikola Jokić", "career points"),
             ("T050", "Stephen Curry", "Damian Lillard", "career points")]
    for tid, a, b, metric in pairs:
        pa, pb = career_pts(a), career_pts(b)
        leader = a if pa >= pb else b
        REF[tid] = (f"By career points, {a} has {pa:,.0f} and {b} has {pb:,.0f}; "
                     f"{leader} leads.")
    REF["T042"] = "Stephen Curry and Kevin Durant are both elite scorers; Durant has more career points, Curry more career three-pointers made."
    REF["T044"] = "LeBron James has more total career points than Kevin Durant."
    REF["T046"] = "The Lakers and Celtics are the two most decorated NBA franchises by championships; historically close in overall success."
    REF["T047"] = "The Warriors and Cavaliers met in four straight NBA Finals (2015-2018); the Warriors won three of those series."
    REF["T048"] = "The 2016 Warriors (73-9) had a better regular-season record than the 1996 Bulls (72-10), though the Bulls won the title that year."


# ---- player_stats (T051-T060) ----
def r_player_stats():
    cases = [
        ("T051", "LeBron James", 2018, "pts_per_game", "averaged {v:.1f} points per game"),
        ("T052", "Nikola Jokić", 2023, "trb_per_game", "averaged {v:.1f} rebounds per game"),
        ("T053", "Stephen Curry", 2016, "ast_per_game", "averaged {v:.1f} assists per game"),
        ("T054", "Kawhi Leonard", 2017, "stl_per_game", "averaged {v:.1f} steals per game"),
        ("T055", "Anthony Davis", 2020, "blk_per_game", "averaged {v:.1f} blocks per game"),
        ("T056", "James Harden", 2019, "x3p_per_game", "made {v:.1f} three-pointers per game"),
        ("T057", "Kevin Durant", 2014, "fg_percent", "shot {v:.1%} from the field"),
        ("T058", "Russell Westbrook", 2017, "tov_per_game", "averaged {v:.1f} turnovers per game"),
        ("T059", "Giannis Antetokounmpo", 2021, "ft_percent", "shot {v:.1%} from the free-throw line"),
        ("T060", "Kobe Bryant", 2009, "g", "played {v:.0f} games"),
    ]
    for tid, player, season, col, phrase in cases:
        row = player_season_row(player, season)
        if row is None:
            REF[tid] = f"No {season} season record was found for {player} in the dataset."
            continue
        val = row[col]
        REF[tid] = f"{player} {phrase.format(v=val)} in the {season} season."


# ---- player_awards (T061-T070) ----
def r_player_awards():
    players = {"T061": "LeBron James", "T062": "Stephen Curry", "T063": "Kobe Bryant",
               "T064": "Michael Jordan", "T065": "Kevin Durant", "T066": "Nikola Jokić",
               "T067": "Giannis Antetokounmpo", "T068": "Anthony Davis",
               "T069": "Dwyane Wade", "T070": "James Harden"}
    for tid, p in players.items():
        won = awards[(awards["player"] == p) & (awards["winner"] == True)]
        if not len(won):
            REF[tid] = f"No major award wins were found on record for {p} in the dataset."
            continue
        items = [f"{row['award'].upper()} ({int(row['season'])})" for _, row in won.iterrows()]
        REF[tid] = f"{p} has won: " + ", ".join(items) + "."


# ---- greeting (T071-T080) ----
def r_greeting():
    for tid in [f"T0{n}" for n in range(71, 81)]:
        REF[tid] = "Hello! I'm HoopMind, your NBA assistant — ask me about players, teams, stats, awards, drafts or All-Star selections."


# ---- goodbye (T081-T090) ----
def r_goodbye():
    for tid in [f"T0{n}" for n in range(81, 90)] + ["T090"]:
        REF[tid] = "Goodbye! Come back anytime for more NBA information."


# ---- dataset_scope (T091-T100) ----
def r_dataset_scope():
    min_season, max_season = int(player_pg["season"].min()), int(player_pg["season"].max())
    text = (f"HoopMind can answer questions about NBA players, teams, season and career "
            f"statistics, awards, draft history and All-Star selections, covering seasons "
            f"from {min_season} to {max_season}.")
    for tid in [f"T0{n}" for n in range(91, 100)] + ["T100"]:
        REF[tid] = text


# ---- player_info (T101-T110) ----
def r_player_info():
    players = {"T101": "LeBron James", "T102": "Stephen Curry", "T103": "Nikola Jokić",
               "T104": "Kobe Bryant", "T105": "Kevin Durant", "T106": "Giannis Antetokounmpo",
               "T107": "Anthony Davis", "T108": "Kawhi Leonard", "T109": "James Harden",
               "T110": "Michael Jordan"}
    for tid, p in players.items():
        row = career[career["player"] == p]
        if not len(row):
            REF[tid] = f"No biographical record was found for {p} in the dataset."
            continue
        row = row.iloc[0]
        REF[tid] = (f"{p} is a {row['pos']} who played from {int(row['from'])} to {int(row['to'])} "
                     f"(NBA debut: {row['debut']}).")


# ---- award_winner (T111-T120) ----
def r_award_winner():
    cases = [("T111", "nba mvp", 2020), ("T112", "nba roy", 2019), ("T113", "nba dpoy", 2021),
             ("T114", "nba smoy", 2018), ("T115", "nba mvp", 2016), ("T116", "nba mip", 2020),
             ("T117", "nba roy", 2018), ("T118", "nba dpoy", 2019), ("T119", "nba smoy", 2021),
             ("T120", "nba mvp", 2023)]
    for tid, award, season in cases:
        row = awards[(awards["award"].str.lower() == award) & (awards["season"] == season)
                      & (awards["winner"] == True)]
        if len(row):
            row = row.iloc[0]
            REF[tid] = f"{row['player']} won the {season} {award.upper().replace('NBA ', '')}."
        else:
            REF[tid] = f"No {season} {award.upper()} winner was found in the dataset."


# ---- all_star (T121-T130) ----
def r_all_star():
    cases = [("T121", "LeBron James", 2020), ("T122", "Stephen Curry", 2019),
             ("T123", "Kevin Durant", 2017), ("T124", "Kobe Bryant", 2010),
             ("T125", "Nikola Jokić", 2023), ("T126", "Giannis Antetokounmpo", 2021),
             ("T127", "Anthony Davis", 2018), ("T128", "James Harden", 2019),
             ("T129", "Kawhi Leonard", 2016), ("T130", "Dwyane Wade", 2012)]
    for tid, p, season in cases:
        row = allstar[(allstar["player"] == p) & (allstar["season"] == season)]
        if len(row):
            replaced = bool(row.iloc[0]["replaced"])
            if replaced:
                REF[tid] = (f"{p} was selected for the {season} NBA All-Star Game but did not "
                             f"play (replaced due to injury).")
            else:
                REF[tid] = f"Yes, {p} played in the {season} NBA All-Star Game."
        else:
            REF[tid] = f"No, {p} was not on record as an All-Star selection for {season}."


def main():
    r_team_stats(); r_league_info(); r_team_info(); r_draft_info(); r_compare()
    r_player_stats(); r_player_awards(); r_greeting(); r_goodbye(); r_dataset_scope()
    r_player_info(); r_award_winner(); r_all_star()

    with RESULT_FILE.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    missing = []
    for r in rows:
        if r["test_id"] in REF:
            r["reference_response"] = REF[r["test_id"]]
        else:
            missing.append(r["test_id"])
    with RESULT_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)
    print(f"Wrote reference_response for {len(REF)}/{len(rows)} rows.")
    if missing:
        print("Missing:", missing)


if __name__ == "__main__":
    main()