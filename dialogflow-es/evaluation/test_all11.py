import sys

sys.path.insert(0, r'C:\Users\Chen Wilson\OneDrive\Desktop\HoopMind_Implementation')

from webhook import process_message

SRC = {'source': 'DIALOGFLOW_MESSENGER'}

CASES = [
    ('player_info', {'player': ['LeBron James']},
     'Tell me about LeBron James'),
    ('player_info', {'player': ['Michael Jordan']},
     'What awards did Michael Jordan win'),
    ('player_stats', {'player': ['Stephen Curry'], 'season': '2016'},
     'Curry stats in 2016'),
    ('team_info', {'team': ['Boston Celtics']},
     'Tell me about the Boston Celtics'),
    ('team_info', {'team': ['Chicago Bulls'], 'season': '1996'},
     'Bulls record in 1996'),
    ('team_stats', {'team': ['Utah Jazz'], 'season': '1997'},
     'Jazz team stats 1997'),
    ('compare', {'player': ['Michael Jordan', 'LeBron James']},
     'Compare Jordan and LeBron'),
    ('compare', {'team': ['Chicago Bulls', 'Los Angeles Lakers']},
     'Compare Bulls and Lakers'),
    ('all_star', {'player': ['LeBron James'], 'season': '2020'},
     'Was LeBron an All-Star in 2020?'),
    ('all_star', {'player': ['LeBron James'], 'season': '2013'},
     'All-NBA First Team LeBron 2013'),
    ('draft_info', {'season': '2003'},
     'First overall pick in 2003'),
    ('league_info', {'league': 'NBA'}, 'Do you cover the NBA?'),
    ('dataset_scope', {}, 'What NBA data do you have?'),
    ('greeting', {}, 'Hello'),
    ('goodbye', {}, 'Goodbye'),
]

failures = []

for intent, params, text in CASES:

    data = process_message(intent, params, text)

    bubble = data.get('text') or ''

    has_rich = bool(data.get('rich'))

    bad = (
        'not implemented' in bubble.lower()
        or "couldn't" in bubble.lower()
        or 'could not' in bubble.lower()
    )

    status = 'FAIL' if bad else 'OK'

    if bad:
        failures.append((intent, bubble[:80]))

    print(f'{status:4} {intent:<14} rich={str(has_rich):<5} '
          f'| {bubble[:70]}')

print()
print('FAILURES:', failures if failures else 'none')
