# 🏀 HoopMind

**HoopMind** is an NBA knowledge chatbot built three times over — once on each of three
conversational AI platforms — so the same question set can be answered, measured and compared
across all of them.

All three answer from the **same dataset**: 22 CSV files covering **1947–2026** across the
NBA, ABA and BAA — **5,367 players** and **96 teams**.

> *"How many points did Stephen Curry average in 2016?"*
> *"Compare Kobe and Jordan career scoring"*
> *"Was Kevin Durant an All-Star in 2022?"*
> *"Who was the first overall pick in 2003?"*

---

## The three implementations

Each lives in its own directory, is documented in its own README, and is **completely
independent** — they share no code. They do share the [dataset](#dataset): the two local builds
each keep their own byte-identical copy of the same 22 CSVs, so a change to one does not affect
the other.

| Implementation | Stack | Runs | Docs |
|---|---|---|---|
| 🟣 **[Rasa Pro](rasa/README.md)** | Rasa Pro 3.18, Python 3.11 + `uv`, pandas, Gemini | Locally — PowerShell launcher, Inspector on `:5005` | **[rasa/README.md](rasa/README.md)** |
| 🔵 **[Dialogflow ES](dialogflow-es/README.md)** | Dialogflow ES, Flask + Streamlit, Python 3.10–3.12, pandas | Locally — API on `:5000`, chat UI on `:8501` | **[dialogflow-es/README.md](dialogflow-es/README.md)** |
| 🟠 **[Botpress](botpress/README.md)** | Botpress Cloud | Hosted — [open the webchat](https://cdn.botpress.cloud/webchat/v3.7/shareable.html?configUrl=https://files.bpcontent.cloud/2026/08/23/20/20260823204029-8F5ANTS0.json) | **[botpress/README.md](botpress/README.md)** |

### At a glance

**[Rasa Pro](rasa/README.md)** — 14 flows, 13 intents, 619 hand-maintained training phrases and
one custom action per flow over a pandas data layer. Runs in two interchangeable modes from the
same flows: an **offline DIETClassifier** pipeline (no API key, 83.0 % 5-fold accuracy) and an
**LLM mode** where Gemini both generates flow commands and composes answers grounded in the
retrieved CSV facts, behind a local key-rotation proxy.

**[Dialogflow ES](dialogflow-es/README.md)** — a Streamlit chat UI over a Flask backend.
Deterministic chip rules → Dialogflow ES `detect_intent` (optional) → a local TF-IDF fallback
classifier → entity recovery → a 2,275-line query engine → rich answer cards. Ships four layers
of testing: regression suites, intent P/R/F1 and BLEU/ROUGE harnesses, a 50-case manual
checklist, and SUS survey tooling.

**[Botpress](botpress/README.md)** — hosted on Botpress Cloud; nothing to install, just the
shareable webchat link.

---

## Dataset

**[NBA / ABA / BAA Stats](https://www.kaggle.com/datasets/sumitrodatta/nba-aba-baa-stats)** by
Sumitro Datta on Kaggle — scraped from
[Basketball Reference](https://www.basketball-reference.com/).

| | |
|---|---|
| **Files** | 22 CSVs (~32 MB) |
| **Seasons** | 1947 – 2026 |
| **Leagues** | NBA, ABA, BAA |
| **Players** | 5,367 |
| **Teams** | 96 |

All three chatbots answer from this same dataset. The two local builds each vendor their own
copy — `rasa/data/nba/` and `dialogflow-es/data/` — which are byte-identical across all 22
files, so neither implementation depends on the other.

<details>
<summary>The 22 files</summary>

```
Advanced.csv                        Player Award Shares.csv       Team Abbrev.csv
All-Star Selections.csv             Player Career Info.csv        Team Stats Per 100 Poss.csv
Draft Pick History.csv              Player Per Game.csv           Team Stats Per Game.csv
End of Season Teams (Voting).csv    Player Play By Play.csv       Team Summaries.csv
End of Season Teams.csv             Player Season Info.csv        Team Totals.csv
Opponent Stats Per 100 Poss.csv     Player Shooting.csv
Opponent Stats Per Game.csv         Player Totals.csv
Opponent Totals.csv                 Per 100 Poss.csv
Per 36 Minutes.csv
```

</details>

---

## Quick start

```powershell
git clone <this-repo>
cd hoopmind
```

**Rasa Pro** — full instructions in **[rasa/README.md](rasa/README.md)**:

```powershell
cd rasa
.\setup.ps1                 # uv sync -> .venv, creates .env template
.\run_rasa.ps1 -Mode nlu    # offline mode, Inspector at http://localhost:5005
```

**Dialogflow ES** — full instructions in **[dialogflow-es/README.md](dialogflow-es/README.md)**:

```powershell
cd dialogflow-es
python -m pip install -r requirements.txt
run_hoopmind.bat            # then open http://localhost:8501
```

**Botpress** — no setup; see **[botpress/README.md](botpress/README.md)** for the link.

---

## Repository layout

```
hoopmind/
├── rasa/                   Rasa Pro assistant          → rasa/README.md
├── dialogflow-es/          Dialogflow ES assistant     → dialogflow-es/README.md
├── botpress/               Botpress Cloud assistant    → botpress/README.md
├── example-queries.md      representative + edge-case queries for smoke testing either build
├── test.csv                shared intent test phrases (source for rasa/tests/nlu_test.yml)
├── CLAUDE.md               repository guidance for AI coding assistants
└── LICENSE
```

---

## Reference

- **[example-queries.md](example-queries.md)** — representative and edge-case queries per intent,
  useful for smoke-testing either local implementation after a change
- **[rasa/INTENTS.md](rasa/INTENTS.md)** — intents, entities, full training phrase lists and
  cross-validated evaluation results
- **[dialogflow-es/TESTING.md](dialogflow-es/TESTING.md)** — the six testing layers, from
  regression suites to the user-satisfaction survey

## Credits

Data: [NBA / ABA / BAA Stats](https://www.kaggle.com/datasets/sumitrodatta/nba-aba-baa-stats)
by Sumitro Datta, via [Basketball Reference](https://www.basketball-reference.com/) ·
Platforms: [Rasa Pro](https://rasa.com/docs/rasa-pro/),
[Google Dialogflow ES](https://cloud.google.com/dialogflow/es/docs),
[Botpress](https://botpress.com/)

## License

[MIT](LICENSE) — Copyright (c) 2026 Tan Yit Shen
