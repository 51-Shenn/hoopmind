"""
Generate evaluation/manual_test_checklist.md

Runs a curated set of ~50 test questions through the query engine +
response generator and embeds the CURRENT expected output for each,
so manual testers can verify both correctness and formatting.

Regenerate any time the engine/generator changes:
    python -X utf8 evaluation/gen_manual_checklist.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent

PROJECT_ROOT = EVAL_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from query_engine import NBAQueryEngine          # noqa: E402
from response_generator import generate          # noqa: E402


# ------------------------------------------------------------
# Test matrix: (section, intent, question, params)
# Params mimic what Dialogflow would send after entity
# extraction (canonical names).
# ------------------------------------------------------------

CASES = [
    # --- Conversational -------------------------------------
    ('greeting', 'greeting', 'Hello!', {}),
    ('goodbye', 'goodbye', 'Bye bye!', {}),
    ('dataset_scope', 'dataset_scope',
     'What NBA data do you have?', {}),
    ('league_information', 'league_information',
     'What league do you cover?', {'league': []}),

    # --- Player profile cards -------------------------------
    ('player_information | InfoCard',
     'player_information', 'Who is LeBron James?',
     {'player': ['LeBron James']}),
    ('player_information | single attribute',
     'player_information', 'How tall is Kevin Durant?',
     {'player': ['Kevin Durant']}),
    ('player_information | full profile',
     'player_information', 'Career overview of Tim Duncan',
     {'player': ['Tim Duncan']}),

    # --- Player statistics (both shapes) --------------------
    ('player_season_stats | mini card',
     'player_season_stats',
     'How many points did Stephen Curry average in 2016?',
     {'player': ['Stephen Curry'], 'season': ['2016'],
      'stat': ['points']}),
    ('player_season_stats | full table',
     'player_season_stats', 'What were Stephen Currys stats in 2016?',
     {'player': ['Stephen Curry'], 'season': ['2016'],
      'stat': []}),
    ('player_advanced_stats | mini card',
     'player_advanced_stats', 'What was Nikola Jokics PER in 2023?',
     {'player': ['Nikola Jokic'], 'season': ['2023'],
      'stat': ['per']}),
    ('player_advanced_stats | full table',
     'player_advanced_stats',
     'Show me Nikola Jokics advanced stats in 2023',
     {'player': ['Nikola Jokic'], 'season': ['2023'],
      'stat': []}),
    ('player_per_36_stats | mini card',
     'player_per_36_stats',
     'Michael Jordan points per 36 minutes in 1991',
     {'player': ['Michael Jordan'], 'season': ['1991'],
      'stat': ['points']}),
    ('player_per_100_stats | full table',
     'player_per_100_stats',
     'Shaquille ONeal per 100 possessions in 2000',
     {'player': ["Shaquille O'Neal"], 'season': ['2000'],
      'stat': []}),
    ('player_shooting_stats | mini card',
     'player_shooting_stats', 'Stephen Curry 3 point percentage 2016',
     {'player': ['Stephen Curry'], 'season': ['2016'],
      'stat': ['three-point percentage']}),
    ('player_play_by_play_stats | full table',
     'player_play_by_play_stats',
     'Nikola Jokic play by play stats in 2023',
     {'player': ['Nikola Jokic'], 'season': ['2023'],
      'stat': []}),

    # --- Career totals (both shapes) ------------------------
    ('player_career_totals | mini card',
     'player_career_totals',
     'How many career points does LeBron James have?',
     {'player': ['LeBron James'], 'stat': ['points']}),
    ('player_career_totals | full table',
     'player_career_totals',
     'What are LeBron James career totals?',
     {'player': ['LeBron James'], 'stat': []}),
    ('player_career_totals | another player',
     'player_career_totals',
     'Career assists of Magic Johnson',
     {'player': ['Magic Johnson'], 'stat': ['assists']}),

    # --- Awards ----------------------------------------------
    ('player_awards | career table',
     'player_awards', 'What awards has LeBron James won?',
     {'player': ['LeBron James'], 'award': [], 'season': []}),
    ('player_awards | winner query MVP',
     'player_awards', 'Who won MVP in 2016?',
     {'player': [], 'award': ['MVP'], 'season': ['2016']}),
    ('player_awards | winner query DPOY',
     'player_awards', 'Who won Defensive Player of the Year in 2023?',
     {'player': [], 'award': ['DPOY'], 'season': ['2023']}),
    ('player_awards | winner query ROY',
     'player_awards', 'Who won Rookie of the Year in 2020?',
     {'player': [], 'award': ['Rookie of the Year'],
      'season': ['2020']}),
    ('player_awards | voting only',
     'player_awards',
     'Did Ja Morant win any awards?',
     {'player': ['Ja Morant'], 'award': [], 'season': []}),

    # --- All-Star (three shapes) -----------------------------
    ('all_star_selection | yes/no',
     'all_star_selection',
     'Was LeBron James an All-Star in 2020?',
     {'player': ['LeBron James'], 'season': ['2020']}),
    ('all_star_selection | career',
     'all_star_selection',
     'How many times was LeBron James an All-Star?',
     {'player': ['LeBron James'], 'season': []}),
    ('all_star_selection | roster list',
     'all_star_selection',
     'Who was selected as an All-Star in 2015?',
     {'player': [], 'season': ['2015']}),
    ('all_star_selection | injured yes/no',
     'all_star_selection',
     'Did Kevin Durant play in the 2022 All-Star Game?',
     {'player': ['Kevin Durant'], 'season': ['2022']},
     'KD was selected but injured: expect NO + Injured line.'),
    ('all_star_selection | played wording',
     'all_star_selection',
     'Who played in the 1998 All-Star Game?',
     {'player': [], 'season': ['1998']},
     'Roster card should say how many players APPEARED.'),
    ('all_star_selection | replacements wording',
     'all_star_selection',
     'Who were the injury replacements in the 2015 All-Star Game?',
     {'player': [], 'season': ['2015']},
     'Replacement pairs, or an honest note if the dataset '
     'does not record who replaced whom.'),

    # --- End-of-season teams ---------------------------------
    ('end_of_season_team | honors',
     'end_of_season_team',
     'Did Tim Duncan make All-NBA in 2003?',
     {'player': ['Tim Duncan'], 'season': ['2003']}),

    # --- Draft ------------------------------------------------
    ('draft_information | DraftCard',
     'draft_information', 'Where was Stephen Curry drafted?',
     {'player': ['Stephen Curry'], 'season': []}),
    ('draft_information | specific pick',
     'draft_information', 'What pick was LeBron James?',
     {'player': ['LeBron James'], 'season': []}),
    ('draft_information | full draft overview',
     'draft_information',
     'Show me the complete 2003 NBA draft',
     {'player': [], 'season': ['2003']},
     'Expect First + Second round cards (58 picks in 2003).'),
    ('draft_information | ordinal word pick',
     'draft_information',
     'Who was the second overall pick in 1996?',
     {'player': [], 'season': ['1996']}),

    # --- Team cards -------------------------------------------
    ('team_information | franchise overview',
     'team_information',
     'Tell me about the Chicago Bulls franchise',
     {'team': ['Chicago Bulls']}),
    ('team_summary | SummaryCard',
     'team_summary', 'How did the Boston Celtics do in 2024?',
     {'team': ['Boston Celtics'], 'season': ['2024']}),
    ('team_summary | latest season default',
     'team_summary',
     'What was the Boston Celtics record?',
     {'team': ['Boston Celtics'], 'season': []},
     'No year given: must return the NEWEST season row.'),
    ('team_summary | record comparison',
     'compare_teams',
     'Team comparison: Portland Trail Blazers against '
     'Minnesota Timberwolves in 2000',
     {'team1': ['Portland Trail Blazers'],
      'team2': ['Minnesota Timberwolves'],
      'season': ['2000'], 'stat': []}),
    ('team_season_stats | full table',
     'team_season_stats',
     'What were the Boston Celtics stats in 2024?',
     {'team': ['Boston Celtics'], 'season': ['2024'],
      'stat': []}),
    ('team_season_stats | single stat',
     'team_season_stats',
     'How many points per game did the Golden State '
     'Warriors average in 2016?',
     {'team': ['Golden State Warriors'], 'season': ['2016'],
      'stat': ['points']}),
    ('team_opponent_stats | defensive table',
     'team_opponent_stats',
     'How stingy was the defense of the Detroit Pistons in 1989?',
     {'team': ['Detroit Pistons'], 'season': ['1989'],
      'stat': []}),
    ('team_opponent_stats | single stat',
     'team_opponent_stats',
     'Opponent points against the Chicago Bulls in 1996',
     {'team': ['Chicago Bulls'], 'season': ['1996'],
      'stat': ['points']}),

    # --- Comparisons -------------------------------------------
    ('compare_players | bare (career totals)',
     'compare_players',
     'Compare LeBron James and Michael Jordan',
     {'player1': ['LeBron James'],
      'player2': ['Michael Jordan'], 'stat': [], 'season': []}),
    ('compare_players | season + stat',
     'compare_players',
     'Compare the rebounds of Nikola Jokic and Joel Embiid in 2023',
     {'player1': ['Nikola Jokic'],
      'player2': ['Joel Embiid'], 'season': ['2023'],
      'stat': ['rebounds']}),
    ('compare_players | career keyword',
     'compare_players',
     'Kevin Durant vs Carmelo Anthony career scoring',
     {'player1': ['Kevin Durant'],
      'player2': ['Carmelo Anthony'], 'stat': [],
      'season': []}),
    ('compare_teams | numeric stat',
     'compare_teams',
     'Which team scored more points in 2010, the Lakers or Celtics?',
     {'team1': ['Los Angeles Lakers'],
      'team2': ['Boston Celtics'],
      'season': ['2010'], 'stat': ['points']}),
    ('compare_teams | best seasons',
     'compare_teams',
     'Compare the Bulls and Lakers best seasons',
     {'team1': ['Chicago Bulls'],
      'team2': ['Los Angeles Lakers'],
      'season': [], 'stat': []},
     'Each team judged on its best win% season; footer says so.'),

    # --- Robustness ---------------------------------------------
    ('robustness | misspelled player',
     'player_season_stats',
     'How many points does Joel Embid average this season?',
     {'player': ['Joel Embid'], 'season': [], 'stat': ['points']},
     'Engine should auto-correct to Joel Embiid and say so.'),
    ('robustness | unknown player',
     'player_season_stats',
     'Stats of Zydrunas Jones in 2010',
     {'player': ['Zydrunas Jones'], 'season': ['2010'],
      'stat': ['points']},
     'Graceful refusal expected.'),
    ('robustness | unmappable stat',
     'player_advanced_stats',
     'What is LeBron James warp?',
     {'player': ['LeBron James'], 'stat': ['warp']},
     'Graceful suggestion message expected.'),
]

# Some rows carry an extra expectation note.


def main() -> None:

    engine = NBAQueryEngine()

    lines = [
        '# HoopMind - Manual Test Checklist',
        '',
        f'_Generated {date.today().isoformat()} from the live engine. '
        'Expected answers are pre-filled; verify value AND formatting._',
        '',
        f'**{len(CASES)} cases** across all 23 intents.',
        '',
        'Legend: tick Pass/Fail after testing in the Streamlit '
        'chat UI (run_hoopmind.bat).',
        '',
        '---',
        '',
    ]

    passed = 0
    failed = 0

    current_section = None

    for idx, case in enumerate(CASES, start=1):

        section, intent, question, params = case[:4]

        note = case[4] if len(case) > 4 else ''

        if section != current_section:

            major = section.split(' | ')[0]

            if major != current_section:

                lines += [f'## {major}', '']
                current_section = major

        result = engine.query(
            intent,
            dict(params),
            query_text=question
        )

        status = ''

        if result.ok:

            answer = generate(
                result.answer_data,
                intent,
                question
            )

            passed += 1

        else:

            answer = f'[ENGINE ERROR] {result.error}'
            failed += 1
            status = ' ⚠️ engine error'

        lines += [
            f'### {idx}. {section}{status}',
            '',
            f'**Ask:** `{question}`',
            '',
        ]

        if note:
            lines += [f'> Note: {note}', '']

        lines += [
            '**Expected answer:**',
            '',
            '```text',
            answer,
            '```',
            '',
            '- [ ] Pass  - [ ] Fail',
            '',
        ]

    lines += [
        '---',
        '',
        f'**Engine snapshot when generated: {passed} ok, '
        f'{failed} error paths (error cases above are intentional).**',
        '',
    ]

    out = EVAL_DIR / 'manual_test_checklist.md'

    out.write_text(
        '\n'.join(lines),
        encoding='utf-8-sig',  # BOM so Notepad/PowerShell detect UTF-8
    )

    print(f'Wrote {out}')
    print(f'Cases: {len(CASES)} ({passed} ok, {failed} graceful errors)')


if __name__ == '__main__':
    main()
