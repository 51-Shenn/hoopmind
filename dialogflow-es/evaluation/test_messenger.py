import json
import sys

sys.path.insert(0, r'C:\Users\Chen Wilson\OneDrive\Desktop\HoopMind_Implementation')

from webhook import process_message


def send(intent, params, text):
    return process_message(intent, params or {}, text)


def show(label, data):
    rich = data.get('rich') or []
    bubble = data.get('text') or ''
    print('=' * 70)
    print(f'{label}')
    print(f'BUBBLE: {bubble}')
    if rich:
        for row in rich:
            for widget in row:
                t = widget.get('type')
                title = widget.get('title', '')
                subtitle = widget.get('subtitle', '')
                body = ' | '.join(widget.get('text', []))[:150]
                chips = ', '.join(
                    o.get('text', '')
                    for o in widget.get('options', [])
                )[:120]
                print(f'  [{t}] {title} :: {subtitle}')
                if body:
                    print(f'      {body}')
                if chips:
                    print(f'      CHIPS: {chips}')
    else:
        print(f'TEXT: {(data.get("text") or "")[:200]}')


cases = [
    ('player_info profile',
     'player_info', {'player': ['LeBron James']},
     'Tell me about LeBron James'),
    ('player_info awards',
     'player_info', {'player': ['Michael Jordan']},
     'What awards did Michael Jordan win'),
    ('player_info draft',
     'player_info', {'player': ['Kobe Bryant']},
     'Where was Kobe Bryant drafted'),
    ('player_info allstar yes/no',
     'player_info', {'player': ['Dirk Nowitzki'], 'season': '2010'},
     'Was Dirk Nowitzki an all star in 2010'),
    ('player_stats season full',
     'player_stats', {'player': ['Stephen Curry'], 'season': '2016'},
     'Show me Stephen Curry stats in 2016'),
    ('player_stats mini ppg',
     'player_stats', {'player': ['Stephen Curry'],
                      'season': '2016', 'stat': 'PTS'},
     'How many points did Curry average in 2016'),
    ('player_stats career totals',
     'player_stats', {'player': ['Kareem Abdul-Jabbar']},
     'Career totals of Kareem Abdul-Jabbar'),
    ('player_stats advanced',
     'player_stats', {'player': ['LeBron James'], 'season': '2013',
                      'stat': 'PER'},
     'LeBron PER and TS percent in 2013'),
    ('team_info franchise',
     'team_info', {'team': ['Los Angeles Lakers']},
     'Tell me about the Lakers franchise'),
    ('team_info summary',
     'team_info', {'team': ['Chicago Bulls'], 'season': '1996'},
     'Bulls record in 1996'),
    ('team_info opponents',
     'team_info', {'team': ['Boston Celtics'], 'season': '2008'},
     'How many points did the Celtics allow in 2008'),
    ('team_stats single',
     'team_stats', {'team': ['Golden State Warriors'],
                    'season': '2017'},
     'Warriors team stats in 2017'),
    ('compare players',
     'compare', {'player': ['Michael Jordan', 'LeBron James'],
                 'stat': 'PTS'},
     'Compare Jordan and LeBron scoring'),
    ('compare teams',
     'compare', {'team': ['Chicago Bulls',
                          'Los Angeles Lakers']},
     'Compare Bulls and Lakers best seasons'),
    ('all_star roster',
     'all_star', {'season': '1998'},
     'Who played in the 1998 all star game'),
    ('all_star honors',
     'all_star', {'player': ['LeBron James'], 'season': '2013'},
     'All-NBA teams of LeBron James in 2013'),
    ('draft_info by pick',
     'draft_info', {'season': '2003'},
     'Who was the first overall pick in 2003'),
    ('draft_info player',
     'draft_info', {'player': ['Tim Duncan']},
     'Where was Tim Duncan drafted'),
    ('league_info compare',
     'league_info', {},
     'What is the difference between NBA and ABA'),
    ('league_info plain',
     'league_info', {'league': 'NBA'},
     'Tell me about the NBA'),
    ('dataset_scope', 'dataset_scope', {},
     'What information do you have'),
    ('greeting', 'greeting', {}, 'Hello'),
    ('goodbye', 'goodbye', {}, 'Goodbye'),
]

for label, intent, params, text in cases:
    data = send(intent, params, text)
    show(label, data)

# Non-messenger fallback must still be fulfillmentText.

# Text-only fallback path: same query, no rich payload expected
# to crash - process_message must always return a text field.

pd = process_message(
    'player_stats',
    {'player': ['Stephen Curry'], 'season': '2016', 'stat': 'PTS'},
    'Curry points 2016',
)
print('=' * 70)
print('TEXT present:', bool(pd.get('text')),
      '| len:', len(pd.get('text') or ''))

print()
print('ALL DONE')
