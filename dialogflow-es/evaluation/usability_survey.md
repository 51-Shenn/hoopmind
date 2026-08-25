# HoopMind Chatbot — Usability & User Satisfaction Survey

Thank you for testing **HoopMind**, an NBA knowledge chatbot. Please complete
the tasks below by chatting with the bot, then rate your experience.

---

## Part 1 — Task-Based Testing

Try each task, then mark whether the chatbot answered correctly:

| # | Task | Succeeded? (Y/N) |
|---|------|------------------|
| T1 | Ask for a greeting and a farewell | ☐ |
| T2 | Ask what data the chatbot has access to | ☐ |
| T3 | Get a player's per-game stat for a specific season *(e.g., Curry's points in 2016)* | ☐ |
| T4 | Ask about a player's career information *(e.g., height, college, Hall of Fame)* | ☐ |
| T5 | Ask whether a player was an All-Star in a given year | ☐ |
| T6 | Ask where a player was drafted | ☐ |
| T7 | Compare two players or two teams | ☐ |
| T8 | Ask for a team's record or opponent-defense stat in one season | ☐ |

**Task success rate = succeeded tasks ÷ 8 = ______ %**

---

## Part 2 — System Usability Scale (SUS)

Rate 1 = Strongly disagree … 5 = Strongly agree.

| # | Statement | 1–5 |
|---|-----------|-----|
| 1 | I think that I would like to use this chatbot frequently. | ☐ |
| 2 | I found the chatbot unnecessarily complex. | ☐ |
| 3 | I thought the chatbot was easy to use. | ☐ |
| 4 | I think that I would need the help of a technical person to be able to use this chatbot. | ☐ |
| 5 | I found the various functions in this chatbot were well integrated. | ☐ |
| 6 | I thought there was too much inconsistency in this chatbot. | ☐ |
| 7 | I would imagine that most people would learn to use this chatbot very quickly. | ☐ |
| 8 | I found the chatbot very cumbersome to use. | ☐ |
| 9 | I felt very confident using the chatbot. | ☐ |
| 10 | I needed to learn a lot of things before I could get going with this chatbot. | ☐ |

---

## Part 3 — Satisfaction Ratings

Rate 1 = Very poor … 5 = Excellent.

| # | Question | 1–5 |
|---|----------|-----|
| S1 | Overall satisfaction with HoopMind | ☐ |
| S2 | Accuracy of the answers given | ☐ |
| S3 | Relevance/quality of the responses' wording | ☐ |
| S4 | Speed of response | ☐ |
| S5 | Ability to understand differently-phrased questions | ☐ |
| S6 | How likely are you to recommend it? (1 = never, 5 = definitely) | ☐ |

Optional free-text: *What did you like most? What should be improved?*

_______________________________________________

---

## Scoring (handled automatically by `score_usability.py`)

* **SUS score**: items 1,3,5,7,9 contribute `(score − 1)`; items 2,4,6,8,10
  contribute `(5 − score)`. Sum × 2.5 → score out of 100.
  Interpretation bands: <51 Poor · 51–68 OK · 68–80.3 Good · 80.3–100 Excellent.
* **Satisfaction**: mean of S1–S6 per respondent plus overall mean.

Fill one row per respondent in `usability_responses.csv`
(see `usability_responses_template.csv`) and run:

```
python evaluation/score_usability.py
```
