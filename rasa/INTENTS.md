# HoopMind - Intents and Training Phrases

Total intents: 13 | Total training phrases: 541

Source: `rasa/data/nlu.yml`

## Entities

| Entity | Purpose | Examples |
|---|---|---|
| `player` | Player name | LeBron James, Stephen Curry |
| `team` | Team name | Boston Celtics, Golden State Warriors |
| `season` | Season/year | 2023, 2016 |
| `stat` | Which statistic | points, rebounds, PER, true_shooting |
| `award` | Award type | MVP, All-Star, Defensive Player of the Year |
| `league` | League name | NBA, ABA |
| `stat_type` | Stat format | per 36, per 100, advanced |

## Evaluation Results

**Model**: DIETClassifier (100 epochs) + WhitespaceTokenizer + RegexFeaturizer + CountVectorsFeaturizer

| Intent | Precision | Recall | F1-Support |
|---|---|---|---|
| team_stats | 1.00 | 1.00 | 1.00 (4) |
| compare | 1.00 | 1.00 | 1.00 (4) |
| all_star | 1.00 | 0.83 | 0.91 (6) |
| draft_info | 1.00 | 1.00 | 1.00 (6) |
| player_info | 0.93 | 1.00 | 0.97 (14) |
| player_stats | 1.00 | 0.94 | 0.97 (16) |
| league_info | 1.00 | 1.00 | 1.00 (4) |
| award_winner | 1.00 | 1.00 | 1.00 (2) |
| player_awards | 1.00 | 1.00 | 1.00 (2) |
| **weighted avg** | **0.99** | **0.99** | **0.99 (60)** |

**Overall accuracy**: 98.8% (was 82.8%)

## 1. greeting (26 phrases)

1. Hi
2. Hello
3. Hey
4. Hi HoopMind
5. Hello HoopMind
6. Hey HoopMind
7. Good morning
8. Good afternoon
9. Good evening
10. Hey there
11. Hi there
12. Hello there
13. What's up
14. Sup
15. Yo
16. Howdy
17. Greetings
18. What's good
19. Hey hey
20. Hiya
21. Hello hello
22. Morning
23. Afternoon
24. Evening
25. Hi, how are you?
26. Hey, what's up?

## 2. goodbye (24 phrases)

1. Bye
2. Goodbye
3. See you
4. See you later
5. That's all
6. I'm done
7. Thanks, bye
8. Thank you, goodbye
9. Talk to you later
10. See ya
11. Bye HoopMind
12. Goodbye HoopMind
13. Later
14. Peace
15. Take care
16. Catch you later
17. I gotta go
18. That's all I needed
19. Thanks for the help, bye
20. Alright, bye
21. Have a good one
22. Good night
23. Cya
24. I'm out

## 3. player_info (81 phrases)

1. Who is [Stephen Curry](player)
2. Tell me about [LeBron James](player)
3. What position does [Kevin Durant](player) play?
4. How tall is [LeBron James](player)?
5. When did [Kobe Bryant](player) debut?
6. Where did [Stephen Curry](player) go to college?
7. Who is [Michael Jordan](player)
8. Tell me about [Giannis Antetokounmpo](player)
9. Who is [mj](player)
10. Who is [kd](player)
11. Tell me about [shaq](player)
12. [cp3](player)
13. [ai](player)
14. [ad](player)
15. [pg](player)
16. [scottie](player)
17. [magic](player)
18. [bird](player)
19. What team does [Luka Doncic](player) play for
20. How old is [Jayson Tatum](player)
21. Give me info on [Nikola Jokic](player)
22. What is [Damian Lillard](player) height
23. Who is [Joel Embiid](player)
24. Tell me about [Anthony Davis](player)
25. What does [Stephen Curry](player) play
26. Information about [Kevin Durant](player)
27. What position is [LeBron James](player)
28. Details about [James Harden](player)
29. [Luka Doncic](player) who is he
30. What can you tell me about [Stephen Curry](player)
31. I want to know about [LeBron James](player)
32. Describe [Michael Jordan](player)
33. [LeBron James](player)
34. [king james](player)
35. [lebron james](player)
36. [lebron](player)
37. [Stephen Curry](player)
38. [Kevin Durant](player)
39. What was [Tim Duncan](player)'s career span?
40. When did [Shaquille O'Neal](player) start and finish his career?
41. Did [Bill Russell](player) make the Hall of Fame?
42. When did [Magic Johnson](player) make his debut?
43. Who is [steph](player)
44. Tell me about [jordan](player)
45. Who is [kobe](player)
46. Tell me about [jokic](player)
47. Who is [luka](player)
48. Who is [dame](player)
49. Info on [harden](player)
50. Who is [embiid](player)
51. Tell me about [giannis](player)
52. Who is [dirk](player)
53. Tell me about [wade](player)
54. Who is [melo](player)
55. Who is [russ](player)
56. Tell me about [jimmy](player)
57. Who is [klay](player)
58. Who is [dwight](player)
59. Tell me about [vince](player)
60. Who is [ray allen](player)
61. Who is [reggie](player)
62. Tell me about [barkley](player)
63. Who is [hakeem](player)
64. Tell me about [stockton](player)
65. Who is [malone](player)
66. Who is [penny](player)
67. Profile of [Wilt Chamberlain](player)
68. Bio for [Allen Iverson](player)
69. Career background of [Kareem Abdul-Jabbar](player)
70. Career overview for [Charles Barkley](player)
71. How tall is [Shaquille O'Neal](player)?
72. Tell me about [Larry Bird](player)'s career
73. Give me a profile of [Wilt Chamberlain](player)
74. Is [Tracy McGrady](player) in the Hall of Fame?
75. Is [Kobe Bryant](player) a Hall of Famer?
76. Did [Michael Jordan](player) make the Hall of Fame?
77. Is [Shaquille O'Neal](player) in the Hall of Fame?
78. Did [Tim Duncan](player) get inducted into the Hall of Fame?
79. Is [LeBron James](player) a Hall of Famer?
80. Did [Magic Johnson](player) make the Hall of Fame?
81. Is [Larry Bird](player) in the Hall of Fame?

## 4. player_stats (82 phrases)

1. What were [Stephen Curry](player)'s stats in [2016](season)?
2. Show me [LeBron James](player)'s statistics for [2018](season)
3. How many points did [Michael Jordan](player) average in [1991](season)?
4. What was [Kevin Durant](player)'s [points](stat) in [2014](season)?
5. Give me the [rebounds](stat) for [Nikola Jokic](player) in [2023](season)
6. [LeBron James](player) stats [2013](season)
7. Show [Stephen Curry](player) [2016](season) numbers
8. What are [Giannis Antetokounmpo](player) stats for [2021](season)
9. [Kevin Durant](player) statistics [2014](season)
10. How did [James Harden](player) perform in [2019](season)
11. Show me [Jayson Tatum](player) stats for [2023](season)
12. What were [Joel Embiid](player) numbers in [2022](season)
13. [Luka Doncic](player) stats [2024](season)
14. [Damian Lillard](player) stats [2020](season)
15. How many assists did [Chris Paul](player) have in [2015](season)
16. Show [Anthony Davis](player) [2020](season) stats
17. What were the [rebounds](stat) for [Nikola Jokic](player) in [2022](season)
18. [LeBron James](player) in [2013](season)
19. [Stephen Curry](player) numbers [2016](season)
20. [Michael Jordan](player) [1991](season)
21. What are [LeBron James](player)'s career totals?
22. How many career points does [LeBron James](player) have?
23. How many career assists did [John Stockton](player) record?
24. Show career [rebounds](stat) for [Dennis Rodman](player)
25. What was [Nikola Jokic](player)'s [PER](stat) in [2023](season)?
26. Show [Giannis Antetokounmpo](player)'s [true shooting percentage](stat).
27. What was [Stephen Curry](player)'s [usage percentage](stat) in [2016](season)?
28. What was [LeBron James](player)'s [VORP](stat) in [2013](season)?
29. How good was [Stephen Curry](player) from three in [2016](season)?
30. What was [Klay Thompson](player)'s [three-point percentage](stat)?
31. How many dunks did [LeBron James](player) have in [2013](season)?
32. What are [James Harden](player)'s [per 100](stat_type) possession [points](stat)?
33. Show [Stephen Curry](player)'s [per 100](stat_type) possession statistics in [2016](season)
34. What was [LeBron James](player)'s offensive rating in [2013](season)?
35. What are [Anthony Davis](player)'s [per 36](stat_type) [points](stat)?
36. Show [Kevin Durant](player)'s [per 36](stat_type) statistics in [2014](season)
37. What is [Nikola Jokic](player)'s [per 36](stat_type) [rebounds](stat)?
38. How many [assists](stat) did [Chris Paul](player) generate in [2015](season)?
39. What was [Stephen Curry](player)'s [plus-minus](stat) [per 100](stat_type) possessions?
40. How many shooting fouls did [James Harden](player) draw?
41. How many dunks did [Rudy Gobert](player) have in [2019](season)?
42. [Trae Young](player) points generated by assists in [2022](season)
43. What was [Draymond Green](player)'s plus-minus impact in [2017](season)?
44. Show me [Kawhi Leonard](player)'s numbers in [2017](season)
45. Show me [Stephen Curry](player)'s numbers in [2016](season)
46. What were [LeBron James](player)'s numbers in [2018](season)?
47. How many points did [Stephen Curry](player) average in [2016](season)?
48. How many points did [Kawhi Leonard](player) average in [2017](season)?
49. How many points did [Kevin Durant](player) average in [2014](season)?
50. Career points of [Kareem Abdul-Jabbar](player)
51. Career points of [LeBron James](player)
52. Career points of [Michael Jordan](player)
53. Career stats for [Magic Johnson](player)
54. Show me [Damian Lillard](player)'s stats for [2020](season)
55. What is [Nikola Jokic](player)'s PER in [2023](season)?
56. What is [Stephen Curry](player)'s PER in [2016](season)?
57. Show [Luka Doncic](player)'s shooting splits for [2024](season)
58. [Trae Young](player) shooting splits for [2023](season)
59. Per 36 minutes stats for [Zion Williamson](player) in [2021](season)
60. Per 36 stats for [Giannis Antetokounmpo](player) in [2020](season)
61. Per 100 possessions for [James Harden](player) in [2019](season)
62. Draw fouls stats for [Jimmy Butler](player) in [2023](season)
63. [DeMar DeRozan](player) points [per 36](stat_type) in [2016](season)
64. Per minute production of [Manu Ginobili](player) in [2007](season)
65. [per 100](stat_type) possessions, [Stephen Curry](player)'s points in [2016](season)
66. What did [Joel Embiid](player) score [per 100](stat_type) possessions in [2021](season)?
67. [Giannis Antetokounmpo](player) rebounds [per 100](stat_type) poss in [2020](season)
68. Show [Damian Lillard](player]'s [per 100](stat_type) assists for [2019](season)
69. What was [Stephen Curry](player)'s [plus-minus](stat) [per 100](stat_type) possessions?
70. How many [blocks](stat) did [Hakeem Olajuwon](player) have?
71. What was [Kobe Bryant](player)'s [free throw percentage](stat)?
72. How many [minutes](stat) did [Kevin Durant](player) play?
73. What is [James Harden](player)'s [usage percentage](stat)?
74. How many [games played](stat) did [Robert Parish](player) have?
75. What was [Tim Duncan](player)'s [win shares](stat)?
76. How many [steals](stat) did [Michael Jordan](player) average?
77. What is [Stephen Curry](player)'s [three point percentage](stat)?
78. What was [LeBron James](player)'s [field goal percentage](stat)?
79. How many [assists](stat) did [Chris Paul](player) generate in [2015](season)?
80. What are [Anthony Edwards](player)'s [per 36](stat_type) points this season?
81. Show me [Kawhi Leonard](player)'s numbers in [2017](season)
82. Show me [Stephen Curry](player)'s numbers in [2016](season)

## 5. team_info (41 phrases)

1. Tell me about the [Boston Celtics](team)
2. What is the abbreviation for the [Golden State Warriors](team)?
3. Which league did the [Los Angeles Lakers](team) play in?
4. Who owns the [Miami Heat](team)
5. What conference are the [Boston Celtics](team) in
6. Tell me about [Chicago Bulls](team)
7. Information on the [Phoenix Suns](team)
8. What division are the [Golden State Warriors](team) in
9. Tell me about [gsw](team)
10. [lakers](team)
11. [celtics](team)
12. [heat](team)
13. [bulls](team)
14. Who is the coach of the [Los Angeles Lakers](team)
15. Details about [Milwaukee Bucks](team)
16. [Boston Celtics](team) info
17. What arena do the [Golden State Warriors](team) play in
18. Tell me about [Denver Nuggets](team)
19. Who plays for the [Philadelphia 76ers](team)
20. [Los Angeles Lakers](team)
21. [Golden State Warriors](team)
22. [Boston Celtics](team)
23. Who are the [Los Angeles Lakers](team) starters?
24. What is the [Boston Celtics](team) roster?
25. Who is the star player on the [Golden State Warriors](team)?
26. When was the [Miami Heat](team) founded?
27. What city are the [Chicago Bulls](team) from?
28. How many championships have the [Boston Celtics](team) won?
29. Who is the owner of the [Phoenix Suns](team)?
30. What is the home arena for the [Milwaukee Bucks](team)?
31. Tell me about the history of the [Los Angeles Lakers](team)
32. [warriors](team)
33. [knicks](team)
34. [sixers](team)
35. [cavs](team)
36. [clips](team)
37. Tell me about the [New York Knicks](team)
38. Info on [Cleveland Cavaliers](team)
39. What about the [Dallas Mavericks](team)
40. [Toronto Raptors](team) info
41. Tell me about the [Brooklyn Nets](team)

## 6. team_stats (89 phrases)

1. What were the [Boston Celtics](team)'s stats in [2024](season)?
2. How many points per game did the [Golden State Warriors](team) average in [2016](season)?
3. What was the [Milwaukee Bucks](team)'s [three-point percentage](stat) in [2021](season)?
4. Show me the [Los Angeles Lakers](team) statistics for [2023](season)
5. What was the [Denver Nuggets](team)'s record in [2023](season)?
6. How many wins did the [Boston Celtics](team) have in [2024](season)?
7. What was the [Phoenix Suns](team)'s [offensive rating](stat) in [2022](season)?
8. Show [Miami Heat](team) stats for [2023](season)
9. How many [rebounds](stat) did the [Milwaukee Bucks](team) average last season?
10. What was the [Philadelphia 76ers](team)'s [pace](stat) in [2024](season)?
11. Show me the [Golden State Warriors](team) shooting stats for [2022](season)
12. How many [assists](stat) did the [Denver Nuggets](team) average in [2023](season)?
13. What was the [Boston Celtics](team)'s [defensive rating](stat) last season?
14. Show the [Los Angeles Clippers](team) stats for [2024](season)
15. How many [turnovers](stat) did the [Phoenix Suns](team) average last season?
16. What was the [Dallas Mavericks](team)'s record in [2023](season)?
17. Show me the [Miami Heat](team) [three-point percentage](stat) for [2024](season)
18. How many [steals](stat) did the [Boston Celtics](team) average last season?
19. What was the [Milwaukee Bucks](team)'s [field goal percentage](stat) in [2024](season)?
20. Show the [Golden State Warriors](team) [rebounds](stat) for [2023](season)
21. What was the record of the [Boston Celtics](team) in [2024](season)?
22. What was the point differential for the [Golden State Warriors](team) in [2016](season)?
23. What was the pace of the [Sacramento Kings](team) in [2023](season)?
24. What was the offensive rating of the [Phoenix Suns](team) in [2021](season)?
25. How many [points](stat) per game did the [Boston Celtics](team) average in [2024](season)?
26. What was the [field goal percentage](stat) of the [Golden State Warriors](team) in [2016](season)?
27. How many [wins](stat) did the [Milwaukee Bucks](team) have last season?
28. [Lakers](team) stats [2024](season)
29. [Bulls](team) record in [1996](season)
30. [Celtics](team) [points](stat) allowed in [2008](season)
31. [Warriors](team) [points](stat) in [2017](season)
32. [Lakers](team) [assists](stat) in [2020](season)
33. [Heat](team) [rebounds](stat) in [2013](season)
34. [Spurs](team) record in [2014](season)
35. [Nets](team) [points](stat) in [2002](season)
36. [Knicks](team) record in [1999](season)
37. [76ers](team) [points](stat) in [2001](season)
38. [Mavericks](team) record in [2011](season)
39. [Suns](team) [points](stat) in [2021](season)
40. [Nuggets](team) record in [2023](season)
41. [Bucks](team) [points](stat) in [2021](season)
42. [Raptors](team) record in [2019](season)
43. [Clippers](team) [points](stat) in [2024](season)
44. [Hawks](team) record in [2015](season)
45. [Trail Blazers](team) [points](stat) in [2019](season)
46. [Cavaliers](team) record in [2016](season)
47. [Pistons](team) [points](stat) in [2004](season)
48. [Magic](team) record in [1995](season)
49. [Kings](team) [points](stat) in [2002](season)
50. [Pelicans](team) [points](stat) in [2024](season)
51. [Timberwolves](team) record in [2024](season)
52. [Grizzlies](team) [points](stat) in [2024](season)
53. [Thunder](team) record in [2012](season)
54. [Jazz](team) [points](stat) in [1997](season)
55. [Hornets](team) [points](stat) in [2016](season)
56. [Pacers](team) record in [2000](season)
57. [Wizards](team) [points](stat) in [2024](season)
58. [Rockets](team) record in [2018](season)
59. [Bulls](team) [points](stat) in [1996](season)
60. [Lakers](team) [points](stat) per game in [2000](season)
61. [Celtics](team) [points](stat) per game in [2008](season)
62. [Warriors](team) [points](stat) per game in [2016](season)
63. [Heat](team) [points](stat) per game in [2012](season)
64. [Golden State Warriors](team) stats [2016](season)
65. [Celtics](team) stats [2024](season)
66. [Heat](team) stats [2023](season)
67. [Bucks](team) stats [2021](season)
68. [Nets](team) stats [2022](season)
69. [76ers](team) stats [2024](season)
70. [Mavericks](team) stats [2023](season)
71. [Suns](team) stats [2022](season)
72. [Nuggets](team) stats [2023](season)
73. lakers stats 2024
74. golden state warriors stats 2016
75. boston celtics stats 2024
76. miami heat stats 2023
77. [Jazz](team) points per game in [1997](season)
78. [Spurs](team) stats in [2014](season)
79. [Rockets](team) points per game in [2018](season)
80. [Thunder](team) stats in [2012](season)
81. [Pistons](team) record in [2004](season)
82. [Knicks](team) stats in [1999](season)
83. [Sixers](team) points per game in [2001](season)
84. [Blazers](team) stats in [1990](season)
85. How many points per game did the [Jazz](team) average in [1997](season)?
86. What was the [Spurs](team)'s record in [2014](season)?
87. [Rockets](team) [three-point percentage](stat) in [2018](season)
88. [Thunder](team) [offensive rating](stat) in [2012](season)
89. [Pistons](team) [defensive rating](stat) in [2004](season)

## 7. compare (56 phrases)

1. Compare [LeBron James](player) and [Michael Jordan](player)
2. Who had more [points](stat), [LeBron James](player) or [Kevin Durant](player)?
3. Compare the [rebounds](stat) of [Nikola Jokic](player) and [Joel Embiid](player)
4. Compare the [Boston Celtics](team) and [Los Angeles Lakers](team)
5. Which team scored more, the [Golden State Warriors](team) or the [Phoenix Suns](team)?
6. Compare [Boston Celtics](team) and [Miami Heat](team) in [2024](season)
7. Who scored more points, [Kobe Bryant](player) or [Tim Duncan](player)?
8. Compare [Stephen Curry](player) and [Kyrie Irving](player) in assists
9. rebounds comparison between [Dennis Rodman](player) and [Ben Wallace](player)
10. Which player averaged more steals : [Chris Paul](player) or [Gary Payton](player)?
11. [Kevin Durant](player) vs [Carmelo Anthony](player) career scoring
12. Which team was better in [2016](season), the [Golden State Warriors](team) or the [San Antonio Spurs](team)?
13. Head to head stats for the [Miami Heat](team) versus the [Dallas Mavericks](team) in [2011](season)
14. Compare the [Los Angeles Clippers](team) with the [Sacramento Kings](team) this season
15. Team comparison: [Portland Trail Blazers](team) against [Minnesota Timberwolves](team) in [2000](season)
16. Who is better, [Stephen Curry](player) or [Kevin Durant](player)?
17. Compare the [assists](stat) of [Chris Paul](player) and [John Stockton](player)
18. Which player has more rings, [LeBron James](player) or [Michael Jordan](player)?
19. Compare [Giannis Antetokounmpo](player) and [Nikola Jokic](player)
20. Who won more [MVP](award)s, [LeBron James](player) or [Stephen Curry](player)?
21. Compare the stats of [Jayson Tatum](player) and [Luka Doncic](player)
22. Which team had a better record, [Boston Celtics](team) or [Denver Nuggets](team)?
23. Compare [Philadelphia 76ers](team) and [Milwaukee Bucks](team)
24. Who is taller, [Kevin Durant](player) or [Giannis Antetokounmpo](player)?
25. Compare the shooting percentage of [Stephen Curry](player) and [Klay Thompson](player)
26. How do [LeBron James](player) and [Kobe Bryant](player) compare?
27. Which player scored more points last season, [Jayson Tatum](player) or [Luka Doncic](player)?
28. Compare [Phoenix Suns](team) and [Dallas Mavericks](team) in [2024](season)
29. Who had more [rebounds](stat) last season, [Nikola Jokic](player) or [Anthony Davis](player)?
30. Compare the career stats of [Tim Duncan](player) and [Kevin Garnett](player)
31. Which team has more championships, [Boston Celtics](team) or [Los Angeles Lakers](team)?
32. Compare [Golden State Warriors](team) dynasty to [Chicago Bulls](team) dynasty
33. Who was more dominant, [Shaquille O'Neal](player) or [Hakeem Olajuwon](player)?
34. Compare [Trae Young](player) and [Damian Lillard](player)
35. compare lebron james and michael jordan
36. compare stephen curry and kevin durant
37. kobe vs lebron
38. kobe or lebron
39. who scored more kobe or lebron
40. who is better curry or durant
41. Compare [Jordan](player) and [LeBron](player) scoring
42. [Bulls](team) vs [Lakers](team) best seasons
43. [Warriors](team) or [Spurs](team) better in [2016](season)?
44. [Celtics](team) versus [Nets](team) in [2023](season)
45. Compare [Lakers](team) and [Celtics](team) all time
46. [Heat](team) vs [Spurs](team) in [2013](season)
47. Compare the shooting percentage of [Stephen Curry](player) and [Klay Thompson](player)
48. How do [LeBron James](player) and [Kobe Bryant](player) compare?
49. Which player scored more points last season, [Jayson Tatum](player) or [Luka Doncic](player)?
50. Compare [Phoenix Suns](team) and [Dallas Mavericks](team) in [2024](season)
51. Who had more [rebounds](stat) last season, [Nikola Jokic](player) or [Anthony Davis](player)?
52. Compare the career stats of [Tim Duncan](player) and [Kevin Garnett](player)
53. Which team has more championships, [Boston Celtics](team) or [Los Angeles Lakers](team)?
54. Compare [Golden State Warriors](team) dynasty to [Chicago Bulls](team) dynasty
55. Who was more dominant, [Shaquille O'Neal](player) or [Hakeem Olajuwon](player)?
56. Compare [Trae Young](player) and [Damian Lillard](player)

## 8. all_star (33 phrases)

1. Was [LeBron James](player) an All-Star in [2020](season)?
2. How many All-Star selections does [LeBron James](player) have?
3. How many All-Star selections does [Stephen Curry](player) have?
4. How many All-Star selections does [Michael Jordan](player) have?
5. How many All-Star selections does [Kobe Bryant](player) have?
6. How many All-Star selections does [Tim Duncan](player) have?
7. How many All-Star selections does [Kevin Durant](player) have?
8. How many All-Star selections does [Shaquille O'Neal](player) have?
9. How many times was [LeBron James](player) an All-Star?
10. How many All-Star games did [LeBron James](player) make?
11. Total All-Star selections for [Dirk Nowitzki](player)
12. How many times did [Michael Jordan](player) make the All-Star team?
13. How many All-Star appearances does [Magic Johnson](player) have?
14. Which team did [Stephen Curry](player) represent as an All-Star in [2016](season)?
15. Who was selected as an All-Star in [2015](season)?
16. Was [LeBron James](player) selected to an All-NBA team in [2013](season)?
17. Which All-NBA team was [Stephen Curry](player) selected to in [2016](season)?
18. Did [Giannis Antetokounmpo](player) make an end of season team in [2019](season)?
19. How many times was [Michael Jordan](player) an All-Star?
20. Is [Kevin Durant](player) an All-Star?
21. Was [Kobe Bryant](player) an All-Star in [2010](season)?
22. How many All-Star games has [Tim Duncan](player) played in?
23. Show me [LeBron James](player)'s All-Star history
24. All-Star selections for [Shaquille O'Neal](player)
25. Was [Nikola Jokic](player) an All-Star in [2022](season)?
26. Did [Jayson Tatum](player) make the All-Star team?
27. Which All-Defensive team was [Michael Jordan](player) on?
28. All-NBA selections for [Kevin Durant](player)
29. Was [Kawhi Leonard](player) on the All-NBA First Team in [2017](season)?
30. End of season awards for [Giannis Antetokounmpo](player) in [2020](season)
31. Did [LeBron James](player) play in the All-Star game?
32. Has [Stephen Curry](player) been an All-Star?
33. Were you an All-Star [Karl Malone](player)?

## 9. draft_info (26 phrases)

1. Where was [Stephen Curry](player) drafted?
2. What pick was [LeBron James](player) in the draft?
3. Which college did [Michael Jordan](player) enter the draft from?
4. Who was the first overall pick in [2003](season)?
5. What round was [Kobe Bryant](player) drafted in?
6. When was [Stephen Curry](player) drafted?
7. What was the draft position of [Giannis Antetokounmpo](player)?
8. Who got picked first overall in [2003](season)?
9. Tell me about the draft history of [Kobe Bryant](player)
10. Where did [Tim Duncan](player) get drafted?
11. Draft info for [Kevin Garnett](player)
12. What pick was [Luka Doncic](player)?
13. Which team drafted [Zion Williamson](player)?
14. What was [Jayson Tatum](player)'s draft position?
15. [2024](season) nba draft
16. nba draft [2023](season)
17. draft [2022](season)
18. who was drafted in [2021](season)
19. [2020](season) draft picks
20. nba draft results [2019](season)
21. Who was the number one pick in [2019](season)?
22. What round was [Nikola Jokic](player) drafted in?
23. Tell me about [Anthony Edwards](player) draft
24. Where was [James Harden](player) selected in the draft?
25. What pick was [Dwyane Wade](player)?
26. Who was the second overall pick in [2003](season)?

## 10. league_info (22 phrases)

1. What league did [Michael Jordan](player) play in?
2. What is the difference between the NBA and ABA?
3. Was [Kareem Abdul-Jabbar](player) in the ABA?
4. Which league was active in [1975](season)?
5. Which basketball leagues do you support?
6. Do you cover the NBA?
7. Tell me about the league data you have
8. What is the NBA?
9. How many teams are in the NBA?
10. When was the NBA founded?
11. What is the history of the NBA?
12. Tell me about the ABA
13. What happened to the ABA?
14. When did the NBA and ABA merge?
15. What leagues existed before the NBA?
16. What is the BAA?
17. Tell me about basketball league history
18. How many championships have been won in the NBA?
19. What is the current NBA season?
20. How is the NBA season structured?
21. What are the NBA divisions?
22. How does the NBA playoffs work?

## 11. dataset_scope (21 phrases)

1. What NBA data do you have?
2. What seasons are available?
3. Which players are in the database?
4. What statistics can you provide?
5. Which teams are included?
6. What data do you have access to?
7. Tell me about your database
8. What information can you give me?
9. Do you have historical NBA data?
10. What years of data do you have?
11. Can you tell me about the data available?
12. What stats are stored in your database?
13. How far back does your data go?
14. Do you have data on all NBA teams?
15. What players are in your system?
16. Can you access NBA statistics?
17. What kind of basketball data do you have?
18. Do you have ABA data too?
19. What is the scope of your knowledge?
20. Do you have data from the 1990s?
21. What can you answer questions about?

## 12. award_winner (20 phrases)

1. Who won [MVP](award) in [2016](season)?
2. Who won the [Most Valuable Player](award) award in [2015](season)?
3. Who was the [DPOY](award) in [2020](season)?
4. Who won [Defensive Player of the Year](award) in [2019](season)?
5. Who won [Rookie of the Year](award) in [2018](season)?
6. Who won the [ROY](award) in [2017](season)?
7. Who was the [Finals MVP](award) in [2016](season)?
8. Who won [MVP](award) in [2014](season)?
9. Who won [MVP](award) in [2013](season)?
10. Who won [Most Improved Player](award) in [2021](season)?
11. Who won [Sixth Man of the Year](award) in [2020](season)?
12. Who was [MVP](award) in [2012](season)?
13. Who won [MVP](award) in [2011](season)?
14. Who won [MVP](award) in [2010](season)?
15. Who was the [SMOY](award) in [2019](season)?
16. Who won [DPOY](award) in [2018](season)?
17. Who won [ROY](award) in [2020](season)?
18. Who was the [Finals MVP](award) in [2015](season)?
19. Who won [MVP](award) in [2009](season)?
20. Who won [MVP](award) in [2008](season)?

## 13. player_awards (20 phrases)

1. What awards did [Michael Jordan](player) win?
2. What awards has [LeBron James](player) won?
3. How many awards did [Kobe Bryant](player) win?
4. Did [Tim Duncan](player) win any awards?
5. What honors did [Magic Johnson](player) receive?
6. List [Larry Bird](player)'s awards
7. Show me [Shaquille O'Neal](player)'s awards
8. What trophies did [Stephen Curry](player) win?
9. How many MVPs did [Michael Jordan](player) win?
10. How many championships did [LeBron James](player) win?
11. Did [Kevin Durant](player) win MVP?
12. What awards does [Giannis Antetokounmpo](player) have?
13. Show [Nikola Jokic](player]'s awards
14. List [Tim Duncan](player]'s honors
15. What did [Hakeem Olajuwon](player) win?
16. How many DPOY did [Kevin Garnett](player) win?
17. Did [Dennis Rodman](player) win any awards?
18. What awards has [Stephen Curry](player) won?
19. How many All-Star selections does [LeBron James](player) have?
20. Show me [Kobe Bryant](player]'s trophy case
