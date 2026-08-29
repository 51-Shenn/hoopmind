#!/usr/bin/env python
"""Generate merged NLU file with combined intents."""
import os
import re

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Read existing file to get the hand-maintained synonym + lookup blocks
with open('data/nlu.yml', 'r', encoding='utf-8') as f:
    content = f.read()

# Everything from the first `- synonym:` onward is carried over verbatim:
# the synonym blocks and the `- lookup:` tables that follow them. Both must
# stay as items of the top-level `nlu:` list or Rasa silently ignores them.
carry_match = re.search(r'^- synonym:', content, re.M)
if carry_match is None:
    raise SystemExit('data/nlu.yml: no `- synonym:` block found to carry over')
carry_section = content[carry_match.start():]

# Build merged NLU
nlu_intents = [
    {
        'intent': 'greeting',
        'examples': [
            '- Hi',
            '- Hello',
            '- Hey',
            '- Hi HoopMind',
            '- Hello HoopMind',
            '- Hey HoopMind',
            '- Good morning',
            '- Good afternoon',
            '- Good evening',
            '- Hey there',
            '- Hi there',
            '- Hello there',
        ]
    },
    {
        'intent': 'goodbye',
        'examples': [
            '- Bye',
            '- Goodbye',
            '- See you',
            '- See you later',
            '- That\'s all',
            '- I\'m done',
            '- Thanks, bye',
            '- Thank you, goodbye',
            '- Talk to you later',
            '- See ya',
            '- Bye HoopMind',
            '- Goodbye HoopMind',
        ]
    },
    {
        'intent': 'player_info',
        'examples': [
            '- Who is [Stephen Curry](player)',
            '- Tell me about [LeBron James](player)',
            '- What position does [Kevin Durant](player) play?',
            '- How tall is [LeBron James](player)?',
            '- When did [Kobe Bryant](player) debut?',
            '- Where did [Stephen Curry](player) go to college?',
            '- Who is [Michael Jordan](player)',
            '- Tell me about [Giannis Antetokounmpo](player)',
            '- What team does [Luka Doncic](player) play for',
            '- How old is [Jayson Tatum](player)',
            '- Give me info on [Nikola Jokic](player)',
            '- What is [Damian Lillard](player) height',
            '- Who is [Joel Embiid](player)',
            '- Tell me about [Anthony Davis](player)',
            '- What does [Stephen Curry](player) play',
            '- Information about [Kevin Durant](player)',
            '- What position is [LeBron James](player)',
            '- Details about [James Harden](player)',
            '- [Luka Doncic](player) who is he',
            '- What can you tell me about [Stephen Curry](player)',
            '- I want to know about [LeBron James](player)',
            '- Describe [Michael Jordan](player)',
            '- [LeBron James](player)',
            '- [Stephen Curry](player)',
            '- [Kevin Durant](player)',
            '- What was [Tim Duncan](player)\'s career span?',
            '- When did [Shaquille O\'Neal](player) start and finish his career?',
            '- Did [Bill Russell](player) make the Hall of Fame?',
            '- When did [Magic Johnson](player) make his debut?',
            '- What awards did [LeBron James](player) win?',
            '- Did [Stephen Curry](player) win the [MVP](award)?',
            '- Who won [MVP](award) in [2016](season)?',
            '- How many times did [Michael Jordan](player) win [MVP](award)?',
        ]
    },
    {
        'intent': 'player_stats',
        'examples': [
            '- What were [Stephen Curry](player)\'s stats in [2016](season)?',
            '- Show me [LeBron James](player)\'s statistics for [2018](season)',
            '- How many points did [Michael Jordan](player) average in [1991](season)?',
            '- What was [Kevin Durant](player)\'s [points](stat) in [2014](season)?',
            '- Give me the [rebounds](stat) for [Nikola Jokic](player) in [2023](season)',
            '- [LeBron James](player) stats [2013](season)',
            '- Show [Stephen Curry](player) [2016](season) numbers',
            '- What are [Giannis Antetokounmpo](player) stats for [2021](season)',
            '- [Kevin Durant](player) statistics [2014](season)',
            '- How did [James Harden](player) perform in [2019](season)',
            '- Show me [Jayson Tatum](player) stats for [2023](season)',
            '- What were [Joel Embiid](player) numbers in [2022](season)',
            '- [Luka Doncic](player) stats [2024](season)',
            '- [Damian Lillard](player) stats [2020](season)',
            '- How many assists did [Chris Paul](player) have in [2015](season)',
            '- Show [Anthony Davis](player) [2020](season) stats',
            '- What were the [rebounds](stat) for [Nikola Jokic](player) in [2022](season)',
            '- [LeBron James](player) in [2013](season)',
            '- [Stephen Curry](player) numbers [2016](season)',
            '- [Michael Jordan](player) [1991](season)',
            '- What are [LeBron James](player)\'s career totals?',
            '- How many career points does [LeBron James](player) have?',
            '- How many career assists did [John Stockton](player) record?',
            '- Show career [rebounds](stat) for [Dennis Rodman](player)',
            '- What was [Nikola Jokic](player)\'s [PER](stat) in [2023](season)?',
            '- Show [Giannis Antetokounmpo](player)\'s [true shooting percentage](stat).',
            '- What was [Stephen Curry](player)\'s [usage percentage](stat) in [2016](season)?',
            '- What was [LeBron James](player)\'s [VORP](stat) in [2013](season)?',
            '- How good was [Stephen Curry](player) from three in [2016](season)?',
            '- What was [Klay Thompson](player)\'s [three-point percentage](stat)?',
            '- How many dunks did [LeBron James](player) have in [2013](season)?',
            '- What are [James Harden](player)\'s per 100 possession [points](stat)?',
            '- Show [Stephen Curry](player)\'s per 100 possession statistics in [2016](season)',
            '- What was [LeBron James](player)\'s offensive rating in [2013](season)?',
            '- What are [Anthony Davis](player)\'s per 36 [points](stat)?',
            '- Show [Kevin Durant](player)\'s per 36 statistics in [2014](season)',
            '- What is [Nikola Jokic](player)\'s per 36 [rebounds](stat)?',
            '- How many [assists](stat) did [Chris Paul](player) generate in [2015](season)?',
            '- What was [Stephen Curry](player)\'s [plus-minus](stat) per 100 possessions?',
            '- How many shooting fouls did [James Harden](player) draw?',
        ]
    },
    {
        'intent': 'team_info',
        'examples': [
            '- Tell me about the [Boston Celtics](team)',
            '- What is the abbreviation for the [Golden State Warriors](team)?',
            '- Which league did the [Los Angeles Lakers](team) play in?',
            '- Who owns the [Miami Heat](team)',
            '- What conference are the [Boston Celtics](team) in',
            '- Tell me about [Chicago Bulls](team)',
            '- Information on the [Phoenix Suns](team)',
            '- What division are the [Golden State Warriors](team) in',
            '- Who is the coach of the [Los Angeles Lakers](team)',
            '- Details about [Milwaukee Bucks](team)',
            '- [Boston Celtics](team) info',
            '- What arena do the [Golden State Warriors](team) play in',
            '- Tell me about [Denver Nuggets](team)',
            '- Who plays for the [Philadelphia 76ers](team)',
            '- [Los Angeles Lakers](team)',
            '- [Golden State Warriors](team)',
            '- [Boston Celtics](team)',
            '- What was the record of the [Boston Celtics](team) in [2024](season)?',
            '- What was the point differential for the [Golden State Warriors](team) in [2016](season)?',
            '- What was the pace of the [Sacramento Kings](team) in [2023](season)?',
            '- What was the offensive rating of the [Phoenix Suns](team) in [2021](season)?',
            '- How many points per game did opponents score against the [Boston Celtics](team) in [2024](season)?',
            '- What was the opponent three-point percentage against the [Golden State Warriors](team) in [2016](season)?',
            '- How many rebounds did opponents average against the [Milwaukee Bucks](team)?',
        ]
    },
    {
        'intent': 'team_stats',
        'examples': [
            '- What were the [Boston Celtics](team)\'s stats in [2024](season)?',
            '- How many points per game did the [Golden State Warriors](team) average in [2016](season)?',
            '- What was the [Milwaukee Bucks](team)\'s [three-point percentage](stat) in [2021](season)?',
        ]
    },
    {
        'intent': 'compare',
        'examples': [
            '- Compare [LeBron James](player) and [Michael Jordan](player)',
            '- Who had more [points](stat), [LeBron James](player) or [Kevin Durant](player)?',
            '- Compare the [rebounds](stat) of [Nikola Jokic](player) and [Joel Embiid](player)',
            '- Compare the [Boston Celtics](team) and [Los Angeles Lakers](team)',
            '- Which team scored more, the [Golden State Warriors](team) or the [Phoenix Suns](team)?',
            '- Compare [Boston Celtics](team) and [Miami Heat](team) in [2024](season)',
        ]
    },
    {
        'intent': 'all_star',
        'examples': [
            '- Was [LeBron James](player) an All-Star in [2020](season)?',
            '- How many All-Star selections does [LeBron James](player) have?',
            '- Which team did [Stephen Curry](player) represent as an All-Star in [2016](season)?',
            '- Who was selected as an All-Star in [2015](season)?',
            '- Was [LeBron James](player) selected to an All-NBA team in [2013](season)?',
            '- Which All-NBA team was [Stephen Curry](player) selected to in [2016](season)?',
            '- Did [Giannis Antetokounmpo](player) make an end of season team in [2019](season)?',
        ]
    },
    {
        'intent': 'draft_info',
        'examples': [
            '- Where was [Stephen Curry](player) drafted?',
            '- What pick was [LeBron James](player) in the draft?',
            '- Which college did [Michael Jordan](player) enter the draft from?',
            '- Who was the first overall pick in [2003](season)?',
            '- What round was [Kobe Bryant](player) drafted in?',
        ]
    },
    {
        'intent': 'league_info',
        'examples': [
            '- What league did [Michael Jordan](player) play in?',
            '- What is the difference between the NBA and ABA?',
            '- Was [Kareem Abdul-Jabbar](player) in the ABA?',
            '- Which league was active in [1975](season)?',
        ]
    },
    {
        'intent': 'dataset_scope',
        'examples': [
            '- What NBA data do you have?',
            '- What seasons are available?',
            '- Which players are in the database?',
            '- What statistics can you provide?',
            '- Which teams are included?',
        ]
    },
]

# Write merged NLU
with open('data/nlu.yml', 'w', encoding='utf-8') as f:
    f.write('version: "3.1"\n')
    f.write('nlu:\n')
    for intent_data in nlu_intents:
        f.write(f'- intent: {intent_data["intent"]}\n')
        f.write('  examples: |\n')
        for ex in intent_data['examples']:
            f.write(f'    {ex}\n')
        f.write('\n')
    f.write('\n')
    f.write(carry_section)

print(f'Done! Wrote {len(nlu_intents)} intents to data/nlu.yml')
for intent_data in nlu_intents:
    print(f'  {intent_data["intent"]}: {len(intent_data["examples"])} examples')
