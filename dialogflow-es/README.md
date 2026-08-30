# 🏀 HoopMind — NBA Knowledge Chatbot (Dialogflow ES)

> Part of the [HoopMind](../README.md) multi-platform chatbot project.
> Sibling implementations: [Rasa Pro](../rasa/README.md) · [Botpress](../botpress/README.md)

HoopMind is a conversational chatbot that answers questions about NBA
players, teams, statistics, awards, All-Star selections and draft history —
covering seasons from 1947 to the present across 22 Basketball-Reference
datasets.

**Architecture:** Streamlit chat UI → Flask backend (`webhook.py`) → NLU
(Google Dialogflow ES, with an offline fallback classifier) → pandas query
engine over the CSV datasets (`query_engine.py`) → rich answer cards
(`response_generator.py`). Dialogflow ES is used purely for intent and
entity **detection**; the actual answer is generated locally by the Flask
app, not by a Dialogflow fulfillment webhook.

---

## Requirements

- **Python 3.10 – 3.12** (developed on 3.12) — <https://www.python.org/downloads/>
  - On the installer's first screen, tick **"Add python.exe to PATH."**
- Windows (one-click launcher) or macOS/Linux (two terminal commands — see below).
- Internet is only needed for the optional live Dialogflow ES mode; everything
  else, including all evaluation scripts, runs fully offline.

## Setup

**Step 1 — Get the project.** Copy/download the whole `dialogflow-es` folder
to your machine, keeping the folder structure intact — especially `data/`
(22 CSV files, ~32 MB).

**Step 2 — Install dependencies.** Open a terminal in the project folder:

```bash
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

One-time; downloads roughly 200 MB.

---

## How to open / run the chatbot

**Windows** — double-click:

```bat
run_hoopmind.bat
```

This opens two windows (Flask API on `:5000`, Streamlit chat UI on
`:8501`) and prints the URLs. Open your browser at:

**<http://localhost:8501>**

**macOS / Linux** — in two separate terminals, from the project folder:

```bash
python webhook.py                          # terminal 1: API on :5000
python -m streamlit run streamlit_app.py   # terminal 2: UI on :8501
```

To stop, close the two console windows (or `Ctrl+C` in each).

By default HoopMind classifies questions with its built-in **offline
classifier** — no Google account or internet needed. See §6 to switch it to
live Dialogflow ES.

## How to use it

Type an NBA question into the chat box at `http://localhost:8501`. Example
questions it understands:

- *"How many points did Stephen Curry average in 2016?"*
- *"Compare Kobe and Jordan career scoring"*
- *"Was Kevin Durant an All-Star in 2022?"* (he was selected but injured)
- *"Show me the complete 2003 NBA draft"*
- *"Which team drafted LeBron James?"*
- *"What awards has Giannis won?"*
- *"Tell me about the Golden State Warriors"*

Tappable suggestion chips under most answers let you continue the
conversation without typing (e.g. drilling into a player's career totals
after seeing their season stats). Say *"bye"* / *"goodbye"* to end.

**Supported question types:** player info & career stats, team info &
season stats, player/team comparisons, awards (won and voting share),
league (single-award) winners, draft history, All-Star selections, and
general "what can you tell me" / dataset-scope questions.

## View HoopMind's Dialogflow ES intents & entities
1. Open Dialogflow ES console and create a new agent
- Go to dialogflow.cloud.google.com
- Sign in with the Google account
- Accept the terms of service on first login
- In the left sidebar, click Create Agent (or the agent dropdown → Create new agent)
- Give it any name (e.g. HoopMind-Import), leave default language (English) and time zone
- Under Google Project, Dialogflow auto-creates a new GCP project for you — leave the default, or pick an existing GCP project if they have one
- Click Create
- This step alone spins up a blank agent and a backing GCP project — no billing required for Dialogflow ES's free tier.

2. Import the agent zip
- In the blank agent, click the ⚙️ gear icon next to the agent name (top of left sidebar) → Export and Import tab
- Click IMPORT FROM ZIP
- Type IMPORT to confirm (this action overwrites the current blank agent — fine since it's empty)
- Upload Google_Dialogflow.zip (in the dialogflow-es folder)
- Wait for the "Agent imported successfully" confirmation

**IMPORTANT**
- Google Dialogflow only handles the detection of intents and entities.
- Hence, there is no responses if ask question in "Try it now".
- For better user interface, pls refer "3. How to open / run the chatbot"

## Optional: enable live Google Dialogflow ES NLU

Out of the box, HoopMind uses its offline classifier. To route messages
through your trained Dialogflow ES agent instead:

1. In Google Cloud Console (the project that owns your agent): **IAM &
   Admin → Service Accounts → Create**, with the **Dialogflow API Client**
   role, then **Keys → Add key → JSON** and download it.
2. Point the standard Google environment variable at the key:

   ```bash
   # Windows
   setx GOOGLE_APPLICATION_CREDENTIALS "C:\path\to\your-key.json"
   # macOS / Linux
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-key.json"
   ```

   Close and reopen the terminal before starting the app.
3. Ask something — the API window log now shows `source=dialogflow`
   (without a key you'll see `source=local-classifier`; both are fully
   functional). Below ~0.70 confidence the app automatically re-checks the
   offline classifier before falling back to a clarification prompt.

---

## Evaluation

Everything needed to reproduce the evaluation lives in `evaluation/`. It
tests the actual 13-intent Dialogflow ES agent — `team_stats`,
`league_info`, `team_info`, `draft_info`, `compare`, `player_stats`,
`player_awards`, `greeting`, `goodbye`, `dataset_scope`, `player_info`,
`award_winner`, `all_star` — against a **held-out set of 130 phrases**
(`test_phrases.csv`, 10 per intent). These phrases were written separately
from the training data and were never imported into Dialogflow.

### 1. Intent recognition — Accuracy, Precision, Recall, F1

Requires `GOOGLE_APPLICATION_CREDENTIALS` set to a Dialogflow-enabled
service account (see §6), plus `pip install google-cloud-dialogflow`.

```bash
python evaluation/run_dialogflow_evaluation.py YOUR_PROJECT_ID
```

Sends all 130 phrases to the live Dialogflow ES agent and writes:
- `test_results.csv` — expected vs. predicted intent, confidence
- `intent_metrics.json` — accuracy + macro/per-intent precision, recall, F1
- `intent_report.txt` — plain-text report for the write-up

**Latest run:**

| Metric | Value |
|---|---|
| Accuracy | **0.885** |
| Macro Precision | 0.865 |
| Macro Recall | 0.821 |
| Macro F1 | 0.831 |

Weakest intents: `greeting` (recall 0.50 — some phrasings are being
misread) and `dataset_scope` (recall 0.60). Full per-intent breakdown is in
`evaluation/intent_report.txt`.

### 2. Response relevancy, quality, and BLEU / ROUGE

Dialogflow's own `fulfillment_text` is never populated in this app —
HoopMind uses Dialogflow only for intent detection and builds the actual
answer locally, so real chatbot responses have to be generated separately:

```bash
python evaluation/generate_chatbot_responses.py
```

Runs the same local answer pipeline the `/chat` endpoint uses
(`webhook.process_message`) for all 130 phrases and fills
`chatbot_response` in `test_results.csv` with the flattened card text — no
network needed for this step.

Independent gold answers were then computed directly from the raw CSVs
(not from the app's own response text, to keep the comparison meaningful):

```bash
python evaluation/build_reference_responses.py
```

Fills `reference_response` for all 130 rows. Then:

```bash
python evaluation/evaluate_responses.py
```

Outputs `response_metrics.json`:

| Metric | Value |
|---|---|
| Scored responses | 130 |
| Average BLEU-4 | 0.164 |
| Average ROUGE-L | 0.309 |
| Manual quality rating | **4.48 / 5** (all 130 rated) |

Low BLEU is expected: the chatbot answers in structured card fragments
(`"📈 Boston Celtics — 2024 \| Points: 120.6"`) against narrative reference
sentences, so raw n-gram overlap is naturally low even when the content is
correct — ROUGE-L is the fairer of the two here. Use BLEU/ROUGE as
**supplementary** evidence, not the primary quality signal.

**How the manual quality score was produced:** every row of
`test_results.csv` carries a `response_quality_1_to_5` rating (1 = very
poor, 5 = excellent) judged against its `chatbot_response`; `evaluate_responses.py`
averages them into `response_metrics.json`. Re-rate a row and re-run the
script to refresh the number.

**Known response-generation issues found during this evaluation** (worth
citing as findings, separate from the raw accuracy numbers):
- `team_stats` for "Golden State's scoring average" fails to resolve the
  nickname "Golden State" and falls back to a clarification prompt. *Still
  open.*
- ~~`player_awards` for LeBron James returns a career-totals card instead
  of an awards list.~~ **Fixed** — now returns `NBA MVP x4: 2009, 2010,
  2012, 2013 / NBA ROY x1: 2004`.
- ~~`player_awards` for James Harden returns "no award record found."~~
  **Fixed** — now returns `NBA SMOY x1: 2012 / NBA MVP x1: 2018`.

### 3. Usability and user satisfaction

```
evaluation/usability_survey.md
```

is a three-part survey: 10 task-success checks, the standard 10-item
System Usability Scale (SUS), and 6 satisfaction ratings. It was given to
**10 real testers** using the live app; their raw answers are in
`evaluation/usability_responses.csv`.

Each participant's answers are transcribed as one row in
`evaluation/usability_responses.csv` (columns: `respondent`,
`task_success_1_to_10`, `sus1`–`sus10`, `sat_overall`, `sat_accuracy`,
`sat_quality`, `sat_speed`, `sat_paraphrase`, `sat_recommend`). Re-score
them with:

```bash
python evaluation/score_usability.py
```

Outputs `usability_metrics.json`: average SUS (0–100; ~68 is the
conventional "average" benchmark), average satisfaction (1–5), and average
task-success rate (%).

**Latest run (10 participants):**

| Metric | Value |
|---|---|
| Average SUS | **93.5** / 100 |
| Average satisfaction | 4.7 / 5 |
| Average task success | 96 % |

### 4. Recommended evidence for the report

- Screenshot of the Dialogflow ES console: intent list + a live "Try it
  now" test
- `evaluation/intent_report.txt`
- `evaluation/response_metrics.json`
- `evaluation/usability_metrics.json`
- A handful of example rows from `test_results.csv` showing both correct
  and incorrect responses (see §7.2 for pre-identified examples)

### 5. Limitations

- Manual response-quality ratings (§7.2) were made by the developer, not by
  independent raters, and the 10 usability participants (§7.3) are a small,
  self-selected sample — both are real data, but neither is blind.
- BLEU/ROUGE reference answers were written independently from the raw
  data rather than by a second human rater; treat them as a supplementary,
  not authoritative, quality signal (see §7.2).

---

## Project layout

```
dialogflow-es/
├── run_hoopmind.bat            one-click launcher (Windows)
├── requirements.txt            pip dependencies (§2)
├── webhook.py                  Flask /chat endpoint + message pipeline
├── streamlit_app.py            chat interface (rich cards + suggestion chips)
├── dialogflow_client.py        Dialogflow ES detection + offline fallback classifier
├── entity_extractor.py         player/team/season/stat recovery from raw text
├── query_engine.py             all NBA queries over the CSV datasets
├── response_generator.py       text answers + rich card payloads
├── config.py                   paths
├── data/                       22 Basketball Reference CSV datasets
└── evaluation/                 test set, evaluation scripts, metrics, survey
    ├── test_phrases.csv                held-out 130-phrase test set
    ├── intent_training_phrases.json    the 13 deployed intents + their training phrases
    ├── run_dialogflow_evaluation.py    §7.1 — intent P/R/F1 against live agent
    ├── generate_chatbot_responses.py   §7.2 — real chatbot answers for the test set
    ├── build_reference_responses.py    §7.2 — independent gold answers for BLEU/ROUGE
    ├── evaluate_responses.py           §7.2 — BLEU/ROUGE + quality scoring
    ├── usability_survey.md             §7.3 — survey given to testers
    ├── usability_responses.csv         §7.3 — 10 participants' raw answers
    ├── score_usability.py              §7.3 — SUS + satisfaction scoring
    └── test_results.csv, intent_metrics.json, intent_report.txt,
        response_metrics.json, usability_metrics.json   — generated outputs
```

## Troubleshooting

| Problem | Fix |
|---|---|
| Port already in use | `Get-NetTCPConnection -LocalPort 5000 -State Listen \| ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }` (same for 8501) |
| `'python' is not recognized` | Reinstall Python with "Add to PATH" ticked, then reopen the terminal |
| `streamlit: command not found` | Use `python -m streamlit run streamlit_app.py` |
| First question is slow | The engine loads CSVs lazily on first use |
| `run_dialogflow_evaluation.py` errors on import | `pip install google-cloud-dialogflow` and set `GOOGLE_APPLICATION_CREDENTIALS` |

## Credits

- Data: [NBA Stats](https://www.kaggle.com/datasets/sumitrodatta/nba-aba-baa-stats)
- NLU platform: [Google Dialogflow ES](https://cloud.google.com/dialogflow/es/docs)
- UI: [Streamlit](https://streamlit.io/) · API: [Flask](https://flask.palletsprojects.com/)