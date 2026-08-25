# HoopMind - Manual Test Checklist

_Generated 2026-08-25 from the live engine. Expected answers are pre-filled; verify value AND formatting._

**50 cases** across all 23 intents.

Legend: tick Pass/Fail after testing in the Streamlit chat UI (run_hoopmind.bat).

---

## greeting

### 1. greeting

**Ask:** `Hello!`

**Expected answer:**

```text
👋 Welcome to HoopMind!
Your NBA knowledge assistant.

I can help you with:
👤 Players      📊 Statistics
🏀 Teams        🏆 Awards
🎓 Drafts       ⭐ All-Stars
```

- [ ] Pass  - [ ] Fail

## goodbye

### 2. goodbye

**Ask:** `Bye bye!`

**Expected answer:**

```text
👋 Thanks for using HoopMind!
Come back anytime for more NBA information. 🏀
```

- [ ] Pass  - [ ] Fail

## dataset_scope

### 3. dataset_scope

**Ask:** `What NBA data do you have?`

**Expected answer:**

```text
📚 HoopMind Data
I can provide information about:

👤 NBA Players (profiles & careers)
📊 Player statistics (season, advanced,
   shooting, per-36, per-100, play-by-play)
🏀 Teams (records, season stats, defense)
🏆 Awards & All-Star selections
🎓 Draft history
📅 Seasons covered across 22 datasets
```

- [ ] Pass  - [ ] Fail

## league_information

### 4. league_information

**Ask:** `What league do you cover?`

**Expected answer:**

```text
🌎 NBA coverage
HoopMind currently covers NBA history from the first season through recent seasons,
spanning player, team and awards data.
```

- [ ] Pass  - [ ] Fail

## player_information

### 5. player_information | InfoCard

**Ask:** `Who is LeBron James?`

**Expected answer:**

```text
👤 LeBron James
F/G
Player Profile
Position: F/G
Height: 6'9" (206 cm)
Weight: 250 lb (113 kg)
Born: 1984-12-30
Career: 2004 - 2026
Hall of Fame: No
```

- [ ] Pass  - [ ] Fail

### 6. player_information | single attribute

**Ask:** `How tall is Kevin Durant?`

**Expected answer:**

```text
👤 Kevin Durant
F/G
Player Profile
Position: F/G
Height: 6'11" (211 cm)
Weight: 240 lb (109 kg)
Born: 1988-09-29
College: Texas
Career: 2008 - 2026
Hall of Fame: No
```

- [ ] Pass  - [ ] Fail

### 7. player_information | full profile

**Ask:** `Career overview of Tim Duncan`

**Expected answer:**

```text
👤 Tim Duncan
F/C
Player Profile
Position: F/C
Height: 6'11" (211 cm)
Weight: 250 lb (113 kg)
Born: 1976-04-25
College: Wake Forest
Career: 1998 - 2016
Hall of Fame 🏆: Yes
```

- [ ] Pass  - [ ] Fail

## player_season_stats

### 8. player_season_stats | mini card

**Ask:** `How many points did Stephen Curry average in 2016?`

**Expected answer:**

```text
📊 Stephen Curry - 2016
Golden State Warriors
Points

⭐ 30.1
Games: 79  •  Age: 27
```

- [ ] Pass  - [ ] Fail

### 9. player_season_stats | full table

**Ask:** `What were Stephen Currys stats in 2016?`

**Expected answer:**

```text
📊 Stephen Curry - 2016
Golden State Warriors
Statistics
Points per game: 30.1
Rebounds per game: 5.4
Assists per game: 6.7
Steals per game: 2.1
Blocks per game: 0.2
Minutes per game: 34.2
Team: Golden State Warriors  •  Games: 79
```

- [ ] Pass  - [ ] Fail

## player_advanced_stats

### 10. player_advanced_stats | mini card

**Ask:** `What was Nikola Jokics PER in 2023?`

**Expected answer:**

```text
📊 Nikola Jokić - 2023
Denver Nuggets, Advanced
Player Efficiency Rating

⭐ 31.5
Games: 69  •  Age: 27
```

- [ ] Pass  - [ ] Fail

### 11. player_advanced_stats | full table

**Ask:** `Show me Nikola Jokics advanced stats in 2023`

**Expected answer:**

```text
📊 Nikola Jokić - 2023
Denver Nuggets, Advanced
Statistics
Player Efficiency Rating: 31.5
True shooting %: 70.1%
Win shares: 14.9
Usage %: 27.2%
Box plus/minus: 13
Value over replacement: 8.8
Team: Denver Nuggets  •  Games: 69
```

- [ ] Pass  - [ ] Fail

## player_per_36_stats

### 12. player_per_36_stats | mini card

**Ask:** `Michael Jordan points per 36 minutes in 1991`

**Expected answer:**

```text
📊 Michael Jordan - 1991
Chicago Bulls, Per 36 Minutes
Points

⭐ 30.6
Games: 82  •  Age: 27
```

- [ ] Pass  - [ ] Fail

## player_per_100_stats

### 13. player_per_100_stats | full table

**Ask:** `Shaquille ONeal per 100 possessions in 2000`

**Expected answer:**

```text
📊 Shaquille O'Neal - 2000
Los Angeles Lakers, Per 100 Possessions
Statistics
Points/100: 38.1
Rebounds/100: 17.5
Assists/100: 4.9
Team: Los Angeles Lakers  •  Games: 79
```

- [ ] Pass  - [ ] Fail

## player_shooting_stats

### 14. player_shooting_stats | mini card

**Ask:** `Stephen Curry 3 point percentage 2016`

**Expected answer:**

```text
📊 Stephen Curry - 2016
Golden State Warriors, Shooting
Three-point percentage

⭐ 45.4%
Games: 79  •  Age: 27
```

- [ ] Pass  - [ ] Fail

## player_play_by_play_stats

### 15. player_play_by_play_stats | full table

**Ask:** `Nikola Jokic play by play stats in 2023`

**Expected answer:**

```text
📊 Nikola Jokić - 2023
Denver Nuggets, Play-by-Play
Statistics
On-court +/-: 12
Net +/-: 21.9
Ast points: 1,564
And-1s: 64
Team: Denver Nuggets  •  Games: 69
```

- [ ] Pass  - [ ] Fail

## player_career_totals

### 16. player_career_totals | mini card

**Ask:** `How many career points does LeBron James have?`

**Expected answer:**

```text
👑 LeBron James
Career Points
Points

⭐ 43,440
Career span: 2004-2026  •  Teams: 3
```

- [ ] Pass  - [ ] Fail

### 17. player_career_totals | full table

**Ask:** `What are LeBron James career totals?`

**Expected answer:**

```text
👑 LeBron James
Career Totals
All-time totals
Points: 43,440
Rebounds: 12,095
Assists: 12,016
Steals: 2,417
Blocks: 1,185
Games: 1,622
Seasons played: 23 (2004-2026)
```

- [ ] Pass  - [ ] Fail

### 18. player_career_totals | another player

**Ask:** `Career assists of Magic Johnson`

**Expected answer:**

```text
👑 Magic Johnson
Career Assists
Assists

⭐ 10,141
Career span: 1980-1996  •  Teams: 1
```

- [ ] Pass  - [ ] Fail

## player_awards

### 19. player_awards | career table

**Ask:** `What awards has LeBron James won?`

**Expected answer:**

```text
🏆 LeBron James
Awards
NBA MVP x4: 2009, 2010, 2012, 2013
NBA ROY x1: 2004
```

- [ ] Pass  - [ ] Fail

### 20. player_awards | winner query MVP

**Ask:** `Who won MVP in 2016?`

**Expected answer:**

```text
🏆 2016 NBA MVP
Stephen Curry (share 1.000)
```

- [ ] Pass  - [ ] Fail

### 21. player_awards | winner query DPOY

**Ask:** `Who won Defensive Player of the Year in 2023?`

**Expected answer:**

```text
🏆 2023 NBA DPOY
Jaren Jackson Jr. (share 0.782)
```

- [ ] Pass  - [ ] Fail

### 22. player_awards | winner query ROY

**Ask:** `Who won Rookie of the Year in 2020?`

**Expected answer:**

```text
🏆 2020 NBA ROY
Ja Morant (share 0.996)
```

- [ ] Pass  - [ ] Fail

### 23. player_awards | voting only

**Ask:** `Did Ja Morant win any awards?`

**Expected answer:**

```text
🏆 Ja Morant
Awards
NBA ROY x1: 2020
NBA MIP x1: 2022
```

- [ ] Pass  - [ ] Fail

## all_star_selection

### 24. all_star_selection | yes/no

**Ask:** `Was LeBron James an All-Star in 2020?`

**Expected answer:**

```text
⭐ 2020 All-Star
LeBron James
Selected: ✅ YES
Team: Team LeBron
```

- [ ] Pass  - [ ] Fail

### 25. all_star_selection | career

**Ask:** `How many times was LeBron James an All-Star?`

**Expected answer:**

```text
⭐ LeBron James
All-Star Selections
⭐ 22
selections

First: 2005   Latest: 2026
2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018 +8 more
```

- [ ] Pass  - [ ] Fail

### 26. all_star_selection | roster list

**Ask:** `Who was selected as an All-Star in 2015?`

**Expected answer:**

```text
⭐ 2015 All-Star Roster
28 players were originally selected
Al Horford, Anthony Davis, Blake Griffin, Carmelo Anthony, Chris Bosh, Chris Paul, Damian Lillard, DeMarcus Cousins, Dirk Nowitzki, Dwyane Wade, James Harden, Jeff Teague, Jimmy Butler, John Wall, Kevin Durant, Klay Thompson, Kobe Bryant, Kyle Korver, Kyle Lowry, Kyrie Irving, LaMarcus Aldridge, LeBron James, Marc Gasol, Pau Gasol, Paul Millsap, Russell Westbrook, Stephen Curry, Tim Duncan

🚑 Injured, did not play: Anthony Davis, Blake Griffin, Dwyane Wade, Kobe Bryant
```

- [ ] Pass  - [ ] Fail

### 27. all_star_selection | injured yes/no

**Ask:** `Did Kevin Durant play in the 2022 All-Star Game?`

> Note: KD was selected but injured: expect NO + Injured line.

**Expected answer:**

```text
⭐ 2022 All-Star
Kevin Durant
❌ NO
Injured — selected but did not play
Team: Team Durant
```

- [ ] Pass  - [ ] Fail

### 28. all_star_selection | played wording

**Ask:** `Who played in the 1998 All-Star Game?`

> Note: Roster card should say how many players APPEARED.

**Expected answer:**

```text
⭐ 1998 All-Star Roster
24 players appeared in the game
Anfernee Hardaway, Antoine Walker, David Robinson, Dikembe Mutombo, Eddie Jones, Gary Payton, Glen Rice, Grant Hill, Jason Kidd, Jayson Williams, Karl Malone, Kevin Garnett, Kobe Bryant, Michael Jordan, Mitch Richmond, Nick Van Exel, Reggie Miller, Rik Smits, Shaquille O'Neal, Shawn Kemp, Steve Smith, Tim Duncan, Tim Hardaway, Vin Baker
```

- [ ] Pass  - [ ] Fail

### 29. all_star_selection | replacements wording

**Ask:** `Who were the injury replacements in the 2015 All-Star Game?`

> Note: Replacement pairs, or an honest note if the dataset does not record who replaced whom.

**Expected answer:**

```text
⭐ 2015 All-Star
Injury replacements
Missed the game through injury:
• Anthony Davis
• Blake Griffin
• Dwyane Wade
• Kobe Bryant
The dataset marks which selections missed the game but does not record who replaced them.
```

- [ ] Pass  - [ ] Fail

## end_of_season_team

### 30. end_of_season_team | honors

**Ask:** `Did Tim Duncan make All-NBA in 2003?`

**Expected answer:**

```text
🏆 Tim Duncan - 2003
End-of-Season Honors
⭐ All-Defense First Team
⭐ All-NBA First Team (F)
```

- [ ] Pass  - [ ] Fail

## draft_information

### 31. draft_information | DraftCard

**Ask:** `Where was Stephen Curry drafted?`

**Expected answer:**

```text
🎓 Stephen Curry
Draft Profile
Draft year: 2009
Round: 1st
Pick: 7th overall
Drafted by: Golden State Warriors
College: Davidson
```

- [ ] Pass  - [ ] Fail

### 32. draft_information | specific pick

**Ask:** `What pick was LeBron James?`

**Expected answer:**

```text
🎓 LeBron James
Draft Profile
Draft year: 2003
Round: 1st
Pick: 1st overall
Drafted by: Cleveland Cavaliers
College: N/A
```

- [ ] Pass  - [ ] Fail

### 33. draft_information | full draft overview

**Ask:** `Show me the complete 2003 NBA draft`

> Note: Expect First + Second round cards (58 picks in 2003).

**Expected answer:**

```text
🎓 2003 NBA Draft
58 picks
🥇 First Round
#1 LeBron James — Cleveland Cavaliers
#2 Darko Miličić — Detroit Pistons
#3 Carmelo Anthony — Denver Nuggets
#4 Chris Bosh — Toronto Raptors
#5 Dwyane Wade — Miami Heat
#6 Chris Kaman — Los Angeles Clippers
#7 Kirk Hinrich — Chicago Bulls
#8 T.J. Ford — Milwaukee Bucks
#9 Mike Sweetney — New York Knicks
#10 Jarvis Hayes — Washington Wizards
#11 Mickaël Piétrus — Golden State Warriors
#12 Nick Collison — Seattle SuperSonics
#13 Marcus Banks — Memphis Grizzlies
#14 Luke Ridnour — Seattle SuperSonics
#15 Reece Gaines — Orlando Magic
#16 Troy Bell — Boston Celtics
#17 Žarko Čabarkapa — Phoenix Suns
#18 David West — New Orleans Hornets
#19 Sasha Pavlović — Utah Jazz
#20 Dahntay Jones — Boston Celtics
#21 Boris Diaw — Atlanta Hawks
#22 Zoran Planinić — New Jersey Nets
#23 Travis Outlaw — Portland Trail Blazers
#24 Brian Cook — Los Angeles Lakers
#25 Carlos Delfino — Detroit Pistons
#26 Ndudi Ebi — Minnesota Timberwolves
#27 Kendrick Perkins — Memphis Grizzlies
#28 Leandro Barbosa — San Antonio Spurs
#29 Josh Howard — Dallas Mavericks
🥈 Second Round
#30 Maciej Lampe — New York Knicks
#31 Jason Kapono — Cleveland Cavaliers
#32 Luke Walton — Los Angeles Lakers
#33 Jerome Beasley — Miami Heat
#34 Sofoklis Schortsanitis — Los Angeles Clippers
#35 Szymon Szewczyk — Milwaukee Bucks
#36 Mario Austin — Chicago Bulls
#37 Travis Hansen — Atlanta Hawks
#38 Steve Blake — Washington Wizards
#39 Slavko Vraneš — New York Knicks
#40 Derrick Zimmerman — Golden State Warriors
#41 Willie Green — Seattle SuperSonics
#42 Zaza Pachulia — Orlando Magic
#43 Keith Bogans — Milwaukee Bucks
#44 Malick Badiane — Houston Rockets
#45 Matt Bonner — Chicago Bulls
#46 Sani Bečirovič — Denver Nuggets
#47 Mo Williams — Utah Jazz
#48 James Lang — New Orleans Hornets
#49 James Jones — Indiana Pacers
#50 Paccelis Morlende — Philadelphia 76ers
#51 Kyle Korver — New Jersey Nets
#52 Remon van de Hare — Toronto Raptors
#53 Tommy Smith — Chicago Bulls
#54 Nedžad Sinanović — Portland Trail Blazers
#55 Rick Rickert — Minnesota Timberwolves
#56 Brandon Hunter — Boston Celtics
#57 Xue Yuyang — Dallas Mavericks
#58 Andreas Glyniadakis — Detroit Pistons
```

- [ ] Pass  - [ ] Fail

### 34. draft_information | ordinal word pick

**Ask:** `Who was the second overall pick in 1996?`

**Expected answer:**

```text
🎓 1996 NBA Draft
#2 Overall Pick: Marcus Camby
Toronto Raptors
```

- [ ] Pass  - [ ] Fail

## team_information

### 35. team_information | franchise overview

**Ask:** `Tell me about the Chicago Bulls franchise`

**Expected answer:**

```text
🏀 Chicago Bulls
Abbreviation: CHI
League: NBA
First season: 1967
Arena: United Center
Seasons completed: 60
All-time record: 2453-2391
Win rate: 50.6%
Playoff appearances: 60
Best season: 1996 (72-10)
Last season (2026): 31-51
```

- [ ] Pass  - [ ] Fail

## team_summary

### 36. team_summary | SummaryCard

**Ask:** `How did the Boston Celtics do in 2024?`

**Expected answer:**

```text
🏀 Boston Celtics — 2024
Season Summary
Record: 64 - 18
Win percentage: 78.0%
Point differential: +11.3
Offensive rating: 123.2
Defensive rating: 111.6
Pace: 97.2
📈 Made the playoffs.
```

- [ ] Pass  - [ ] Fail

### 37. team_summary | latest season default

**Ask:** `What was the Boston Celtics record?`

> Note: No year given: must return the NEWEST season row.

**Expected answer:**

```text
🏀 Boston Celtics — 2026
Season Summary
Record: 56 - 26
Win percentage: 68.3%
Point differential: +7.7
Offensive rating: 120.8
Defensive rating: 112.7
Pace: 94.8
```

- [ ] Pass  - [ ] Fail

### 38. team_summary | record comparison

**Ask:** `Team comparison: Portland Trail Blazers against Minnesota Timberwolves in 2000`

**Expected answer:**

```text
⚔️ Team Comparison
Portland Trail Blazers vs Minnesota Timberwolves
Portland Trail Blazers
• Season: 2000
• Record: 59-23
• Point differential: +6.4
• Offensive rating: 107.9
• Defensive rating: 100.8
• Pace: 89.9
• Playoffs: Yes
Minnesota Timberwolves
• Season: 2000
• Record: 50-32
• Point differential: +2.5
• Offensive rating: 106.1
• Defensive rating: 103.4
• Pace: 91.8
• Playoffs: Yes
🏆 Result: The Portland Trail Blazers had the better record (72.0% wins).
```

- [ ] Pass  - [ ] Fail

## team_season_stats

### 39. team_season_stats | full table

**Ask:** `What were the Boston Celtics stats in 2024?`

**Expected answer:**

```text
📈 Boston Celtics — 2024
Season Statistics
Points: 120.6
Field goal %: 48.7%
Three-point %: 38.8%
Record: 64-18
Playoffs: Yes
Pace: 97.2
```

- [ ] Pass  - [ ] Fail

### 40. team_season_stats | single stat

**Ask:** `How many points per game did the Golden State Warriors average in 2016?`

**Expected answer:**

```text
📈 Golden State Warriors — 2016
Season Statistics
Points: 114.9
Field goal %: 48.7%
Three-point %: 41.6%
Record: 73-9
Playoffs: Yes
Pace: 99.3
```

- [ ] Pass  - [ ] Fail

## team_opponent_stats

### 41. team_opponent_stats | defensive table

**Ask:** `How stingy was the defense of the Detroit Pistons in 1989?`

**Expected answer:**

```text
🛡️ Detroit Pistons — 1989
Opponent Statistics (per game allowed)
Points: 100.8
Rebounds: 40.5
Assists: 22.6
Field goal %: 44.7%
Three-point %: 28.5%
```

- [ ] Pass  - [ ] Fail

### 42. team_opponent_stats | single stat

**Ask:** `Opponent points against the Chicago Bulls in 1996`

**Expected answer:**

```text
🛡️ Chicago Bulls — 1996
Opponent Statistics (per game allowed)
Points: 92.9
Rebounds: 38
Assists: 19.4
Field goal %: 44.8%
Three-point %: 35.0%
```

- [ ] Pass  - [ ] Fail

## compare_players

### 43. compare_players | bare (career totals)

**Ask:** `Compare LeBron James and Michael Jordan`

**Expected answer:**

```text
⚔️ LeBron James vs Michael Jordan
Player Comparison
Head-to-head
Points
• LeBron James: 43,440
• Michael Jordan: 32,292

Rebounds
• LeBron James: 12,095
• Michael Jordan: 6,672

Assists
• LeBron James: 12,016
• Michael Jordan: 5,633

Steals
• LeBron James: 2,417
• Michael Jordan: 2,514

Blocks
• LeBron James: 1,185
• Michael Jordan: 893

Games
• LeBron James: 1,622
• Michael Jordan: 1,072
Based on career totals.
🏆 Result: LeBron James leads with 43,440 versus 32,292 for Michael Jordan.
```

- [ ] Pass  - [ ] Fail

### 44. compare_players | season + stat

**Ask:** `Compare the rebounds of Nikola Jokic and Joel Embiid in 2023`

**Expected answer:**

```text
⚔️ Nikola Jokić vs Joel Embiid
Player Comparison
Head-to-head
Rebounds
• Nikola Jokić: 11.8
• Joel Embiid: 10.2
🏆 Result: Nikola Jokić leads with 11.8 versus 10.2 for Joel Embiid.
```

- [ ] Pass  - [ ] Fail

### 45. compare_players | career keyword

**Ask:** `Kevin Durant vs Carmelo Anthony career scoring`

**Expected answer:**

```text
⚔️ Kevin Durant vs Carmelo Anthony
Player Comparison
Head-to-head
Points
• Kevin Durant: 33,963
• Carmelo Anthony: 30,259

Rebounds
• Kevin Durant: 8,567
• Carmelo Anthony: 8,371

Assists
• Kevin Durant: 5,515
• Carmelo Anthony: 3,643

Steals
• Kevin Durant: 1,270
• Carmelo Anthony: 1,291

Blocks
• Kevin Durant: 1,411
• Carmelo Anthony: 690

Games
• Kevin Durant: 1,248
• Carmelo Anthony: 1,337
Based on career totals.
🏆 Result: Kevin Durant leads with 33,963 versus 30,259 for Carmelo Anthony.
```

- [ ] Pass  - [ ] Fail

## compare_teams

### 46. compare_teams | numeric stat

**Ask:** `Which team scored more points in 2010, the Lakers or Celtics?`

**Expected answer:**

```text
⚔️ Los Angeles Lakers vs Boston Celtics
Team Comparison
Los Angeles Lakers — 2010
• Points: 101.7
• Field goal %: 45.7%
• Three-point %: 34.1%
Boston Celtics — 2010
• Points: 99.2
• Field goal %: 48.3%
• Three-point %: 34.8%
Season records
• Records: 57-25 (Los Angeles Lakers, 2010)
• Records: 50-32 (Boston Celtics, 2010)
🏆 Result: The Los Angeles Lakers leads with 101.7 versus 99.2 for the Boston Celtics.
Result: The Los Angeles Lakers had the better record (69.5% wins).
```

- [ ] Pass  - [ ] Fail

### 47. compare_teams | best seasons

**Ask:** `Compare the Bulls and Lakers best seasons`

> Note: Each team judged on its best win% season; footer says so.

**Expected answer:**

```text
⚔️ Chicago Bulls vs Los Angeles Lakers
Team Comparison
Chicago Bulls — 1996
• Points: 105.2
• Field goal %: 47.8%
• Three-point %: 40.3%
Los Angeles Lakers — 1972
• Points: 121
• Field goal %: 49.0%
Season records
• Records: 72-10 (Chicago Bulls, 1996)
• Records: 69-13 (Los Angeles Lakers, 1972)
🏆 Result: The Los Angeles Lakers leads with 121 versus 105.2 for the Chicago Bulls.
Each team's best season used.
Result: The Chicago Bulls had the better record (87.8% wins).
```

- [ ] Pass  - [ ] Fail

## robustness

### 48. robustness | misspelled player

**Ask:** `How many points does Joel Embid average this season?`

> Note: Engine should auto-correct to Joel Embiid and say so.

**Expected answer:**

```text
📊 Joel Embiid - 2026
Philadelphia 76ers
Statistics
Points per game: 26.9
Rebounds per game: 7.7
Assists per game: 3.9
Steals per game: 0.6
Blocks per game: 1.2
Minutes per game: 31.6
Team: Philadelphia 76ers  •  Games: 38
```

- [ ] Pass  - [ ] Fail

### 49. robustness | unknown player ⚠️ engine error

**Ask:** `Stats of Zydrunas Jones in 2010`

> Note: Graceful refusal expected.

**Expected answer:**

```text
[ENGINE ERROR] I could not find the requested player/statistic combination.
```

- [ ] Pass  - [ ] Fail

### 50. robustness | unmappable stat ⚠️ engine error

**Ask:** `What is LeBron James warp?`

> Note: Graceful suggestion message expected.

**Expected answer:**

```text
[ENGINE ERROR] I couldn't map 'warp' to a statistic. Supported examples: points, rebounds, assists, steals, blocks, field goal percentage, three-pointers.
```

- [ ] Pass  - [ ] Fail

---

**Engine snapshot when generated: 48 ok, 2 error paths (error cases above are intentional).**
