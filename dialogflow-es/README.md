# 🏀 HoopMind — Dialogflow ES Assistant

> Part of the [HoopMind](../README.md) multi-platform chatbot project.
> Sibling implementations: [Rasa Pro](../rasa/README.md) · [Botpress](../botpress/README.md)

A conversational chatbot that answers questions about NBA players, teams, statistics, awards,
All-Star selections and draft history — from the shared HoopMind [dataset](#dataset): 22 CSVs
covering the NBA, ABA and BAA from **1947 to 2026**, 5,367 players and 96 teams.

**Ask things like:**

- *"How many points did Stephen Curry average in 2016?"*
- *"Compare Kobe and Jordan career scoring"*
- *"Was Kevin Durant an All-Star in 2022?"* (he was selected but injured)
- *"Show me the complete 2003 NBA draft"*
- *"How stingy was the defense of the Detroit Pistons in 1989?"*
- *"Which team scored more points in 2010, the Lakers or Celtics?"*

**Architecture:** Streamlit chat UI → Flask backend → NLU (Google Dialogflow ES with an offline
fallback classifier) → pandas query engine over the CSVs → rich answer cards.

---

## Table of contents

- [Requirements](#requirements)
- [Setup](#setup)
- [Running](#running)
- [Optional: live Google Dialogflow NLU](#optional-live-google-dialogflow-nlu)
- [Request pipeline](#request-pipeline)
- [The two intent vocabularies](#the-two-intent-vocabularies)
- [Modules](#modules)
- [Testing and evaluation](#testing-and-evaluation)
- [Project layout](#project-layout)
- [Troubleshooting](#troubleshooting)

---

## Requirements

| | |
|---|---|
| **Python** | 3.10 – 3.12 (developed on 3.12) — <https://www.python.org/downloads/><br>On the installer's first screen, tick **"Add python.exe to PATH"**. |
| **OS** | Windows gets a double-click launcher; macOS and Linux run the two processes manually. |
| **Internet** | Only needed for the optional Google Dialogflow NLU mode. Everything else runs fully offline. |

Dependencies (`requirements.txt`):

```
Flask>=3.1,<4              pandas>=2.2,<3            streamlit>=1.62,<2
google-cloud-dialogflow>=2.29,<3                     scikit-learn>=1.5
google-auth>=2.40,<3       python-dotenv>=1.1,<2     requests>=2.32
```

---

## Setup

### 1. Get the project

Keep the folder structure intact — especially `data\` (22 CSV files, ~32 MB).

### 2. Install dependencies

From `dialogflow-es/`:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

One-time; downloads roughly 200 MB.

---

## Running

**Windows:** double-click

```bat
run_hoopmind.bat
```

Two console windows open (API server + chat UI). Then open **<http://localhost:8501>**.

**macOS / Linux / manual:** from `dialogflow-es/`, in two terminals:

```bash
python -X utf8 webhook.py                          # terminal 1: Flask API on :5000
python -X utf8 -m streamlit run streamlit_app.py   # terminal 2: Streamlit UI on :8501
```

`-X utf8` matters on Windows — the cards use box-drawing characters and emoji.

| Port | Process |
|---|---|
| `5000` | Flask API — `POST /chat`, health check at <http://127.0.0.1:5000/> |
| `8501` | Streamlit chat UI (posts to `:5000/chat`) |

**Stop:** `Ctrl+C` in each terminal, or close the windows.

While testing, watch the API console for the routing log — it shows exactly what the NLU decided:

```
[chat] <raw intent> -> <resolved intent> | Params={...}
```

---

## Optional: live Google Dialogflow NLU

Out of the box HoopMind classifies questions with its built-in offline classifier. To route every
message through your Dialogflow ES agent instead:

1. In Google Cloud Console (the project that owns your agent):
   **IAM & Admin → Service Accounts → Create**, with the **Dialogflow API Client** role.
   Then **Keys → Add key → JSON** and download it.
2. Point the standard Google variable at the key:

   ```powershell
   setx GOOGLE_APPLICATION_CREDENTIALS "C:\path\to\your-key.json"
   ```

   Close and reopen the terminal before starting the app.
3. Ask anything — the API log now shows `source=dialogflow`. Without a key you see
   `source=local-classifier`. **Both paths are fully functional.**

> The Dialogflow console's "Try It Now" panel cannot display rich cards — those are built by
> Flask, not by Google.

---

## Request pipeline

```
streamlit_app.py
   │  POST /chat
   ▼
webhook.py
   │
   ├─ 1. deterministic chip / override patterns      CHIP_PATTERNS, CHIP_SEASON_RULES
   │       (suggestion buttons send templated sentences — routed without NLU at all)
   │
   ├─ 2. Dialogflow ES detect_intent                 only when GOOGLE_APPLICATION_CREDENTIALS is set
   │       confidence < 0.35 → fall through
   │
   ├─ 3. local TF-IDF nearest-centroid classifier    over the 217 training phrases
   │
   ▼
process_message()
   │
   ├─ entity recovery       entity_extractor.extract()  — player / team / season from raw text
   ├─ intent fan-out        resolve_intent()            — 11 external → ~20 engine intents
   ├─ reroute guard         entity evidence beats a wrong local-classifier label
   ├─ param normalisation   _normalise_params(), _infer_stat_from_text()
   ├─ query                 query_engine.NBAQueryEngine.query() → QueryResult
   └─ rendering             response_generator.generate_cards() (or generate() on failure)
```

`webhook.process_message()` is the **shared pipeline used by `/chat` and by every regression
suite** — write tests against it, not against HTTP.

Pipeline facts that are easy to miss:

- The deployed training phrases are **not entity-annotated**, so Dialogflow parameters usually
  arrive empty. `entity_extractor.extract()` recovers player / team / season from the raw text
  **before** intent fan-out, so `compare` can see two entities. Genuine Dialogflow values always
  win over recovered ones.
- `_normalise_params()` splits list-valued entities (`{'team': [a, b]}`) into `team1` / `team2`.
- When `source == "local-classifier"`, entity evidence overrides the label: a detected player is
  rerouted out of a `team_*` handler, and a detected team out of a `player_*` handler.
- `NBAQueryEngine` lazily loads and caches the CSVs and has explicit **entity guards** — without
  them a missing or garbled name falls through to the first CSV row (alphabetically Hank
  Biasatti). It returns `QueryResult(ok, answer_data, error)`; failures carry user-facing text,
  not exceptions.
- `generate_cards()` builds Dialogflow-style `richContent` payloads (ASCII box cards +
  suggestion chips); `generate()` is the plaintext path used when card building fails.

---

## The two intent vocabularies

The deployed Dialogflow agent exposes **11 consolidated intents**; `query_engine` speaks about
**20 fine-grained ones**. `resolve_intent()` in [webhook.py](webhook.py) bridges them using
keyword tuples (`AWARD_WORDS`, `DRAFT_WORDS`, `ALL_STAR_WORDS`, `HONOR_WORDS`,
`CAREER_TOTAL_WORDS`, `ADVANCED_WORDS`, `SHOOTING_WORDS`, `PBP_WORDS`, `OPPONENT_WORDS`,
`SUMMARY_WORDS`, …) plus entity counts.

| External intent (11) | Resolves to engine intents |
|---|---|
| `player_info` | `player_information`, `player_season_stats`, `player_career_totals`, `player_awards`, `all_star_selection`, `end_of_season_team`, `draft_information` |
| `player_stats` | `player_season_stats`, `player_career_totals`, `player_per_36_stats`, `player_per_100_stats`, `player_advanced_stats`, `player_shooting_stats`, `player_play_by_play_stats` |
| `team_info` | `team_information`, `team_summary`, `team_opponent_stats` |
| `team_stats` | `team_season_stats`, `compare_teams` |
| `compare` | `compare_players`, `compare_teams` |
| `all_star` | `all_star_selection`, `end_of_season_team` |
| `draft_info` | `draft_information` |
| `league_info` | `league_information` |
| `dataset_scope` | `dataset_scope` |
| `greeting` / `goodbye` | passthrough |

**Adding a capability normally touches four places:**

1. the keyword tuple in `webhook.py`
2. a `resolve_intent()` branch
3. a `query_engine` handler
4. a `response_generator` card builder

---

## Modules

| File | Lines | Role |
|---|---:|---|
| [webhook.py](webhook.py) | 812 | Flask `/chat` endpoint, chip rules, `resolve_intent()`, `process_message()` |
| [query_engine.py](query_engine.py) | 2,275 | `NBAQueryEngine` — every NBA query over the CSVs, entity guards, fuzzy matching, season/stat canonicalisation |
| [response_generator.py](response_generator.py) | 3,063 | `generate_cards()` rich payloads + `generate()` plaintext |
| [entity_extractor.py](entity_extractor.py) | 283 | player / team / season / stat recovery from raw text |
| [dialogflow_client.py](dialogflow_client.py) | 161 | `detect_via_dialogflow()` (0.35 confidence floor) + `classify_locally()` TF-IDF fallback |
| [streamlit_app.py](streamlit_app.py) | 245 | chat UI, card rendering, suggestion chips, example prompts |
| [config.py](config.py) | 5 | `BASE_DIR` / `DATA_DIR` paths |

### Dataset

`data/` holds the shared HoopMind dataset:
**[NBA / ABA / BAA Stats](https://www.kaggle.com/datasets/sumitrodatta/nba-aba-baa-stats)** by
Sumitro Datta on Kaggle, scraped from
[Basketball Reference](https://www.basketball-reference.com/).

| | |
|---|---|
| **Files** | 22 CSVs (~32 MB) |
| **Seasons** | 1947 – 2026 |
| **Leagues** | NBA, ABA, BAA |
| **Players** | 5,367 |
| **Teams** | 96 |

All three HoopMind chatbots answer from this same dataset. This directory holds its **own copy**,
byte-identical to `rasa/data/nba/` — the two implementations share no code, so changing the CSVs
here does not affect the Rasa build (and vice versa). Keep them in sync manually if you refresh
the data.

---

## Testing and evaluation

Full detail lives in **[TESTING.md](TESTING.md)**. Summary:

### 1. Regression suites (no server needed)

```powershell
python -X utf8 evaluation\test_all11.py       # one case per external intent, rich cards verified
python -X utf8 evaluation\test_no_params.py   # params arrive EMPTY — entity recovery must fill them
python -X utf8 evaluation\test_messenger.py   # full card render for every handler shape
```

All three call `webhook.process_message()` directly. **Expected output: `FAILURES: none`.**

### 2. Metrics

```powershell
python -X utf8 evaluation\evaluate_intent.py      # 59 held-out paraphrases → P / R / F1
python -X utf8 evaluation\evaluate_responses.py   # 21 cases → BLEU / ROUGE-L
```

| Harness | Latest result |
|---|---|
| Intent classification (offline nearest-centroid TF-IDF over 217 training phrases) | Accuracy **0.695**, Macro-F1 **0.595** |
| Response quality (21 cases vs human references) | Corpus BLEU-4 0.037 · avg sentence BLEU 0.105 · **avg ROUGE-L F1 0.233** |

Two caveats worth carrying into any report:

- The intent numbers score **only the classifier**. In the app, misroutes are recovered by
  `entity_extractor`, the local-classifier reroute guard and the chip rules — end-to-end
  behaviour is materially stronger than these raw numbers. For authoritative Dialogflow figures,
  set `GOOGLE_APPLICATION_CREDENTIALS` and run
  `python -X utf8 evaluation\evaluate_intent.py --api YOUR_PROJECT_ID`.
- BLEU punishes structured card output (`Points ⭐ 30.1`) against narrative references ("he
  averaged 30.1 points"), so low n-gram scores are expected. ROUGE-L's longest-common-subsequence
  is the fairer metric here. Results land in `evaluation\response_eval_results.json`.

### 3. Manual UI pass

```powershell
python -X utf8 evaluation\gen_manual_checklist.py
```

Regenerates `evaluation\manual_test_checklist.md` — **50 cases** with expected answers taken from
the *current* engine. Covers every handler shape plus the All-Star tri-state (played /
selected-but-injured / replacement), roster wording modes, draft overview cards, best-season team
compare, latest-season defaults, career-totals compares and graceful errors.

### 4. User satisfaction survey (needs 5+ testers)

```powershell
python -X utf8 evaluation\score_usability.py
```

Give testers `evaluation\usability_survey.md` (8 tasks + SUS + satisfaction), enter their ratings
into `evaluation\usability_responses.csv` (copy the template; integers 1–5), then score it — it
prints the SUS score (0–100) and average satisfaction per dimension.

---

## Project layout

```
dialogflow-es/
├── run_hoopmind.bat            one-click launcher (Windows)
├── webhook.py                  Flask /chat endpoint + shared message pipeline
├── streamlit_app.py            chat interface (rich cards + suggestion chips)
├── dialogflow_client.py        Dialogflow ES detection + offline TF-IDF classifier
├── entity_extractor.py         player / team / season / stat recovery from raw text
├── query_engine.py             all NBA queries over the CSV datasets
├── response_generator.py       text answers + rich card payloads
├── config.py                   paths
├── requirements.txt
├── TESTING.md                  full testing guide (all 6 layers)
├── data/                       the 22-CSV Kaggle dataset (~32 MB)
└── evaluation/
    ├── test_all11.py                    one case per external intent
    ├── test_no_params.py                entity recovery with empty params
    ├── test_messenger.py                card render for every handler shape
    ├── e2e_test.py                      end-to-end pass
    ├── evaluate_intent.py               intent P / R / F1 (--api PROJECT_ID for live DF)
    ├── evaluate_responses.py            BLEU / ROUGE-L
    ├── gen_manual_checklist.py          regenerate the 50-case checklist
    ├── score_usability.py               SUS + satisfaction scoring
    ├── intent_training_phrases.json     217 phrases across 11 intents
    ├── intent_test_set.json             59 held-out paraphrases
    ├── response_test_set.json           21 reference answers
    ├── manual_test_checklist.md         50 manual cases
    ├── usability_survey.md              tester-facing survey
    └── usability_responses*.csv         survey data + template
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Port already in use | `Get-NetTCPConnection -LocalPort 5000 -State Listen \| ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }` (same for 8501) |
| `'python' is not recognized` | Reinstall Python with "Add to PATH" ticked, then reopen the terminal |
| `streamlit: command not found` | Use `python -m streamlit run streamlit_app.py` |
| Emoji look broken in console logs | Harmless display issue; the browser UI is unaffected. Keep `-X utf8`. |
| First question is slow | The engine loads the CSVs lazily on first use |
| Answers come back about the wrong player | Check the `[chat]` log — if `Params` is empty, entity recovery missed the name; add it to `entity_extractor` |
| `source=local-classifier` when you expected Dialogflow | `GOOGLE_APPLICATION_CREDENTIALS` is unset in *this* terminal, or confidence fell below 0.35 |

---

## Reference

- [TESTING.md](TESTING.md) — regression suites, metric harnesses, manual checklist, survey tooling
- [example-queries.md](../example-queries.md) — representative and edge-case queries for smoke testing

## Credits

- Data: [NBA / ABA / BAA Stats](https://www.kaggle.com/datasets/sumitrodatta/nba-aba-baa-stats)
  by Sumitro Datta, via [Basketball Reference](https://www.basketball-reference.com/)
- NLU platform: [Google Dialogflow ES](https://cloud.google.com/dialogflow/es/docs)
- UI: [Streamlit](https://streamlit.io/) · API: [Flask](https://flask.palletsprojects.com/)
