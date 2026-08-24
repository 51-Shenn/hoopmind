# HoopMind - Intents and Training Phrases

Total intents: 11 | Total training phrases: 217

Source: HoopMind_Intents_Entities_Latest.zip (exact contents imported into Google Dialogflow).
Restructured from 23 original intents to 11 combined intents for improved NLU accuracy.

## Entities

| Entity | Purpose | Examples |
|---|---|---|
| `player` | Player name | LeBron James, Stephen Curry |
| `team` | Team name | Boston Celtics, Golden State Warriors |
| `season` | Season/year | 2023, 2016 |
| `stat` | Which statistic | points, rebounds, PER, true_shooting |
| `award` | Award type | MVP, All-Star, Defensive Player of the Year |
| `league` | League name | NBA, ABA |

## 1. player_info (31 phrases)

Merged from: `player_information` + `player_career_information` + `player_awards`

1. Who is Stephen Curry
2. Tell me about LeBron James
3. What position does Kevin Durant play?
4. How tall is LeBron James?
5. When did Kobe Bryant debut?
6. Where did Stephen Curry go to college?
7. Who is Giannis Antetokounmpo
8. How tall is Shaquille O'Neal?
9. Tell me about Larry Bird's career
10. Give me a profile of Wilt Chamberlain
11. Is Tracy McGrady in the Hall of Fame?
12. Bio for Allen Iverson
13. What was Tim Duncan's career span?
14. When did Shaquille O'Neal start and finish his career?
15. Did Bill Russell make the Hall of Fame?
16. When did Magic Johnson make his debut?
17. Career background of Kareem Abdul-Jabbar
18. When did Magic Johnson play?
19. Which college did Shaq attend?
20. Career overview for Charles Barkley
21. What awards did LeBron James win?
22. Did Stephen Curry win the MVP?
23. Who won MVP in 2016?
24. How many times did Michael Jordan win MVP?
25. Did Giannis Antetokounmpo win Most Valuable Player in 2019?
26. How many times did Michael Jordan win Defensive Player of the Year?
27. List LeBron James's awards
28. Awards won by Stephen Curry
29. Who won Rookie of the Year in 2021?
30. Was Marc Gasol ever Sixth Man of the Year?
31. Show me Kawhi Leonard's numbers in 2017

## 2. player_stats (57 phrases)

Merged from: `player_season_stats` + `player_career_totals` + `player_advanced_stats` + `player_shooting_stats` + `player_per_36_stats` + `player_per_100_stats` + `player_play_by_play_stats`

1. What were Stephen Curry's stats in 2016?
2. Show me LeBron James's statistics for 2018
3. How many points did Michael Jordan average in 1991?
4. What was Kevin Durant's points in 2014?
5. Give me the rebounds for Nikola Jokic in 2023
6. How many points did James Harden average in 2019?
7. What did Russell Westbrook average rebounds in 2017?
8. Chris Paul assists for the 2008 season
9. I want to know Kyrie Irving's points in 2020
10. What were Luka Doncic's stats last season?
11. What are LeBron James's career totals?
12. How many career points does LeBron James have?
13. How many career assists did John Stockton record?
14. Show career rebounds for Dennis Rodman
15. Total career points for Kareem Abdul-Jabbar
16. How many assists did John Stockton record overall?
17. Career rebounds of Moses Malone
18. Sum up Ray Allen's career three-pointers
19. Overall blocks for Tim Duncan
20. What was Nikola Jokic's PER in 2023?
21. Show Giannis Antetokounmpo's true shooting percentage.
22. What was Stephen Curry's usage percentage in 2016?
23. What was LeBron James's VORP in 2013?
24. What was Nikola Jokic's player efficiency rating in 2021?
25. Show LeBron James's win shares for 2013
26. What was Michael Jordan's usage percentage in 1991?
27. David Robinson box plus/minus during 1995
28. Give me James Harden's true shooting percentage in 2019
29. How good was Stephen Curry from three in 2016?
30. What was Klay Thompson's three-point percentage?
31. How many dunks did LeBron James have in 2013?
32. What percentage of his shots did DeAndre Jordan make in 2017?
33. How efficient was Kevin Durant from three-point range in 2018?
34. Show Kyle Korver's corner three percentage in 2015
35. How many dunks did Dwight Howard attempt in 2010?
36. Klay Thompson shooting splits for 2018
37. What are James Harden's per 100 possession points?
38. Show Stephen Curry's per 100 possession statistics in 2016
39. What was LeBron James's offensive rating in 2013?
40. Per 100 possessions, Stephen Curry's points in 2016
41. What did Joel Embiid score per 100 possessions in 2021?
42. Giannis Antetokounmpo rebounds per 100 poss in 2020
43. Show Damian Lillard's per-100 assists for 2019
44. What are Anthony Davis's per 36 points?
45. Show Kevin Durant's per 36 statistics in 2014
46. What is Nikola Jokic's per 36 rebounds?
47. Per 36 minutes stats for Zion Williamson in 2021
48. What are Anthony Edwards's points per 36 minutes this season?
49. DeMar DeRozan points per 36 in 2016
50. Per-minute production of Manu Ginobili in 2007
51. How many assists did Chris Paul generate in 2015?
52. What was Stephen Curry's plus-minus per 100 possessions?
53. How many shooting fouls did James Harden draw?
54. How many dunks did Rudy Gobert have in 2019?
55. Trae Young points generated by assists in 2022
56. What was Draymond Green's plus-minus impact in 2017?
57. Draw fouls stats for Jimmy Butler in 2023

## 3. team_info (23 phrases)

Merged from: `team_information` + `team_summary` + `team_opponent_stats`

1. Tell me about the Boston Celtics
2. What is the abbreviation for the Golden State Warriors?
3. Which league did the Los Angeles Lakers play in?
4. Tell me about the Chicago Bulls franchise
5. How long have the Denver Nuggets existed?
6. Franchise overview for the Toronto Raptors
7. History of the Philadelphia 76ers
8. When did the Memphis Grizzlies join the NBA?
9. What was the record of the Boston Celtics in 2024?
10. What was the point differential for the Golden State Warriors in 2016?
11. What was the pace of the Sacramento Kings in 2023?
12. What was the offensive rating of the Phoenix Suns in 2021?
13. What was the Dallas Mavericks record in 2007?
14. How did the Detroit Pistons do in 1989?
15. Season summary for the Oklahoma City Thunder in 2013
16. Give me the win loss record of the Houston Rockets for 2018
17. How many points per game did opponents score against the Boston Celtics in 2024?
18. What was the opponent three-point percentage against the Golden State Warriors in 2016?
19. How many rebounds did opponents average against the Milwaukee Bucks?
20. How many points did teams score against the Boston Celtics in 2008?
21. Opponent scoring defense for the Miami Heat in 2012
22. What did opponents average against the San Antonio Spurs in 2016?
23. Defensive stats of the Indiana Pacers in 2004

## 4. team_stats (7 phrases)

Merged from: `team_season_stats`

1. What were the Boston Celtics's stats in 2024?
2. How many points per game did the Golden State Warriors average in 2016?
3. What was the Milwaukee Bucks's three-point percentage in 2021?
4. How many points did the Utah Jazz average per game in 1997?
5. Team assists for the Atlanta Hawks in 2015
6. What were the Milwaukee Bucks averaging in points this season?
7. Show the Phoenix Suns offensive stats in 2021

## 5. compare (15 phrases)

Merged from: `compare_players` + `compare_teams`

1. Compare LeBron James and Michael Jordan
2. Who had more points, LeBron James or Kevin Durant?
3. Compare the rebounds of Nikola Jokic and Joel Embiid
4. Who scored more points, Kobe Bryant or Tim Duncan?
5. Compare Stephen Curry and Kyrie Irving in assists
6. rebounds comparison between Dennis Rodman and Ben Wallace
7. Which player averaged more steals : Chris Paul or Gary Payton?
8. Kevin Durant vs Carmelo Anthony career scoring
9. Compare the Boston Celtics and Los Angeles Lakers
10. Which team scored more, the Golden State Warriors or the Phoenix Suns?
11. Compare Boston Celtics and Miami Heat in 2024
12. Which team was better in 2016, the Golden State Warriors or the San Antonio Spurs?
13. Head to head stats for the Miami Heat versus the Dallas Mavericks in 2011
14. Compare the Los Angeles Clippers with the Sacramento Kings this season
15. Team comparison: Portland Trail Blazers against Minnesota Timberwolves in 2000

## 6. all_star (18 phrases)

Merged from: `all_star_selection` + `end_of_season_team`

1. Was LeBron James an All-Star in 2020?
2. How many All-Star selections does LeBron James have?
3. Which team did Stephen Curry represent as an All-Star in 2016?
4. Who was selected as an All-Star in 2015?
5. Was LeBron James ever an All-Star?
6. Tell me if Stephen Curry made the All-Star game in 2015
7. How many times was Kevin Durant an All-Star?
8. Did Yao Ming play in the All-Star game in 2007?
9. All-Star appearances for Tim Duncan
10. Dirk Nowitzki All-Star selections
11. Was LeBron James selected to an All-NBA team in 2013?
12. Which All-NBA team was Stephen Curry selected to in 2016?
13. Did Giannis Antetokounmpo make an end of season team in 2019?
14. Did LeBron James make All-NBA First Team in 2013?
15. Was Kawhi Leonard on an All-Defensive team in 2016?
16. All-Rookie selections for Victor Wembanyama
17. Did Hakeem Olajuwon receive All-Defensive honors in 1993?
18. Dwyane Wade All-NBA history

## 7. draft_info (11 phrases)

Merged from: `draft_information`

1. Where was Stephen Curry drafted?
2. What pick was LeBron James in the draft?
3. Which college did Michael Jordan enter the draft from?
4. Who was the first overall pick in 2003?
5. What round was Kobe Bryant drafted in?
6. When was Stephen Curry drafted?
7. What was the draft position of Giannis Antetokounmpo?
8. Who got picked first overall in 2003?
9. Tell me about the draft history of Kobe Bryant
10. Where did Tim Duncan get drafted?
11. Draft info for Kevin Garnett

## 8. greeting (18 phrases)

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
13. what's up
14. yo hoopmind
15. hiya
16. good day
17. sup
18. howdy

## 9. goodbye (19 phrases)

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
13. catch you later
14. peace out
15. nothing else, thanks
16. that is all i wanted
17. quit
18. later
19. im good bye

## 10. league_info (7 phrases)

Merged from: `league_information`

1. What league did Michael Jordan play in?
2. What is the difference between the NBA and ABA?
3. Was Kareem Abdul-Jabbar in the ABA?
4. Which league was active in 1975?
5. Which basketball leagues do you support?
6. Do you cover the NBA?
7. Tell me about the league data you have

## 11. dataset_scope (11 phrases)

Merged from: `dataset_scope`

1. What NBA data do you have?
2. What seasons are available?
3. Which players are in the database?
4. What statistics can you provide?
5. Which teams are included?
6. What kind of data do you cover?
7. What can you tell me about?
8. How far back does your NBA data go?
9. What questions can you answer?
10. Show me your available datasets
11. What information do you have access to?
