import sys

sys.path.insert(0, r'C:\Users\Chen Wilson\OneDrive\Desktop\HoopMind_Implementation')

from webhook import process_message

# NO parameters at all - everything must come from the text.

CASES = [
    ('player_info', 'Tell me about LeBron James'),
    ('player_info', 'Is Tracy McGrady in the Hall of Fame?'),
    ('player_info', 'What awards did Michael Jordan win?'),
    ('player_stats', 'Show me Kawhi Leonard' + chr(39)
     + 's numbers in 2017'),
    ('player_stats', 'Stephen Curry stats in 2016'),
    ('player_info', 'Who won MVP in 2016?'),
    ('team_info', 'Bulls record in 1996'),
    ('compare', 'Compare Kobe and Jordan'),
    ('compare', 'Compare the Bulls and Lakers'),
    ('draft_info', 'First overall pick in 2003'),
    ('league_info', 'What league did Michael Jordan play in?'),
    ('all_star', 'Was Dirk an All-Star in 2010?'),
]

failures = []

for intent, text in CASES:

    data = process_message(intent, {}, text)

    bubble = data.get('text') or str(data)[:60]

    rich = data.get('rich') or []

    card_title = ''

    if rich and rich[0]:

        card_title = rich[0][0].get('title', '')

    bad = (
        'Biasatti' in str(data)
        or "couldn't" in bubble.lower()
        or 'could not' in bubble.lower()
        or 'not implemented' in bubble.lower()
    )

    if bad:
        failures.append((intent, text))

    print(('FAIL' if bad else 'OK  '), f'{intent:<13}',
          f'| {card_title[:44]:<44} | {bubble[:40]}')

print()
print('FAILURES:', failures if failures else 'none')
