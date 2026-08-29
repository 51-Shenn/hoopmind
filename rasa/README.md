# 🏀 HoopMind — Rasa Pro Assistant

> Part of the [HoopMind](../README.md) multi-platform chatbot project.
> Sibling implementations: [Dialogflow ES](../dialogflow-es/README.md) · [Botpress](../botpress/README.md)

A Rasa Pro 3.18 assistant that answers NBA questions over the shared HoopMind
[dataset](#datasets) — 22 CSVs covering the NBA, ABA and BAA from **1947 to 2026**, 5,367 players
and 96 teams. It runs in two interchangeable
modes from the same flows and the same custom actions:

- **NLU mode** — DIETClassifier, fully offline, no API key.
- **LLM mode** — Gemini command generation plus LLM-composed answers grounded in the CSV data.

**Ask things like:**

- *"How many points did Stephen Curry average in 2016?"*
- *"Compare Kobe and Jordan career scoring"*
- *"Was Kevin Durant an All-Star in 2022?"*
- *"Who was the first overall pick in 2003?"*
- *"What was Nikola Jokić's PER in 2023?"*

---

## Table of contents

- [Requirements](#requirements)
- [Setup](#setup)
- [Running](#running)
- [The two modes](#the-two-modes)
- [Architecture](#architecture)
- [Custom actions and data access](#custom-actions-and-data-access)
- [Grounded LLM answers and key rotation](#grounded-llm-answers-and-key-rotation)
- [Training data](#training-data)
- [Evaluating NLU](#evaluating-nlu)
- [Project layout](#project-layout)
- [Command reference](#command-reference)
- [Troubleshooting](#troubleshooting)

---

## Requirements

| | |
|---|---|
| **Python** | 3.11 (pinned by `pyproject.toml`: `>=3.11,<3.12` — Rasa Pro 3.18 requires it) |
| **Package manager** | [uv](https://docs.astral.sh/uv/) |
| **Rasa Pro license** | Free developer license from [app.rasa.com](https://app.rasa.com/) — required for *both* modes |
| **Gemini API key(s)** | Optional — LLM mode only. Get them at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| **OS** | Windows-first (PowerShell launchers). The `uv run rasa …` commands work anywhere. |

Pinned dependencies (`pyproject.toml`, locked in `uv.lock`):

```
rasa-pro==3.18.1
rasa-sdk==3.18.0
setuptools==80.10.2
```

---

## Setup

### 1. Install uv

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Create the environment

```powershell
cd rasa
.\setup.ps1
```

`setup.ps1` runs `uv sync` (creating `.venv` from the exact `uv.lock` pins) and writes a `.env`
template if one does not already exist.

### 3. Fill in `.env`

`rasa/.env` is gitignored. The PowerShell launchers parse it manually into process environment
variables — Rasa itself never reads the file.

```env
# Rasa Pro license (https://app.rasa.com/) — required
RASA_LICENSE=your-license-here

# Gemini API keys (https://aistudio.google.com/apikey) — LLM mode only.
# Any number from GEMINI_API_KEY_1..GEMINI_API_KEY_9 may be added; the proxy
# rotates through all of them on rate limits.
GEMINI_API_KEY=your-primary-key-here
GEMINI_API_KEY_1=your-second-key-here
GEMINI_API_KEY_2=your-third-key-here
GEMINI_API_KEY_3=your-fourth-key-here

# Model used by actions/llm_answer.py
GEMINI_MODEL=gemini-3.1-flash-lite
```

`run_rasa_llm.ps1` refuses to start if every key is still a placeholder (`your-…-key-here`).

---

## Running

One launcher does everything — mode switch, retrain, action server, Inspector, cleanup on exit:

```powershell
cd rasa
```

```powershell
.\run_rasa.ps1            # interactive picker: [1] NLU  [2] LLM
```

```powershell
.\run_rasa.ps1 -Mode nlu  # offline DIETClassifier, no API key needed
```

```powershell
.\run_rasa.ps1 -Mode llm  # Gemini + key-rotation proxy
```

The Inspector opens at **<http://localhost:5005>**. Press `Ctrl+C` to stop; the launcher kills
the background action server (and the proxy, in LLM mode) on the way out.

| Port | Process |
|---|---|
| `5005` | Rasa server / Inspector UI |
| `5055` | Rasa SDK action server (`rasa_sdk --actions actions`) |
| `8300` | `gemini_proxy.py` key-rotation proxy (LLM mode only; `GET /status` reports key health) |
| `5006` / `5056` | second Inspector and second action server — side-by-side mode only (see below) |

### Both modes side by side

For demos where you want to compare the two modes live, `run_rasa_both.ps1` runs them at the
same time. The single-mode launchers **cannot** be used together — they share `config.yml` /
`domain.yml`, both retrain on start, `run_rasa_nlu.ps1` prunes `models/` down to one archive,
both bind `:5005`, and both reuse one action server on `:5055`, so whichever starts first
decides `HOOPMIND_GROUND_ANSWERS` for both bots.

```powershell
.\run_rasa_both.ps1                              # train both, launch both
.\run_rasa_both.ps1 -SkipTrain                   # reuse the existing archives
.\run_rasa_both.ps1 -NluPort 5006 -LlmPort 5005  # swap the Inspector ports
```

It sidesteps every one of those collisions:

1. Trains both models up front under fixed names — `models/hoopmind_nlu.tar.gz` and
   `models/hoopmind_llm.tar.gz` — so `config.yml` only matters during training.
2. Serves each bot from its archive with `rasa inspect --model …`. A model archive carries its
   own config and domain, so the generated files are irrelevant once the servers are up. The two
   bot windows invoke `.venv\Scripts\python.exe -m rasa` by absolute path rather than
   `uv run` — a spawned window does not inherit the parent's activated environment, so `uv` is
   not on its PATH and `uv run rasa inspect` dies with *'uv' is not recognized*.
3. Gives each bot its **own action server**: `:5055` with `HOOPMIND_GROUND_ANSWERS` cleared for
   the NLU bot, `:5056` with it set for the LLM bot. `compose_answer()` reads that variable from
   its own process at call time, so a shared server would leak Gemini grounding into the
   supposedly-offline NLU demo.
4. Points each at its own endpoints file — `endpoints_nlu.yml` (action server `:5055`, no
   `model_groups`) and `endpoints_llm.yml` (action server `:5056`, proxy model groups kept).

Five processes in total: the proxy, two action servers (hidden), and one Inspector per bot in
its own window. It refuses to start if any of `8300`, `5055`, `5056`, `5005`, `5006` is already
taken, so a leftover launcher window gives a clear error instead of a half-broken demo. Press
Enter in the parent window to stop everything (`taskkill /T`, since `uv` spawns children that
would otherwise keep holding the ports).

A bot binds its port only after loading its model, and the NLU archive carries DIET, so cold
start is **~60-90 s**. The launcher waits for both Inspector ports (up to 4 min) and prints
`NLU Inspector is up on :5005` per bot before it shows the URLs — otherwise the links are handed
out dead and look like a failure. If one never binds, the parent says so and points you at that
bot's window, which stays open (`-NoExit`) with the error.

> Training leaves `config.yml` / `domain.yml` in **LLM** mode. The running bots ignore that, but
> a later bare `uv run rasa train` builds an LLM model. And do not run `run_rasa_nlu.ps1`
> afterwards — its pruning step deletes every archive but the newest, taking out one of the two
> demo models.

### What the launchers do

`run_rasa_nlu.ps1`:

1. Verifies `.venv` exists (tells you to run `setup.ps1` otherwise).
2. Loads `.env` into the process environment.
3. Switches to NLU mode if `config.yml` is not currently DIET-based.
4. **Always retrains** — an NLU-only archive has no core model and silently breaks the flows.
5. Prunes `models/` down to the newest `.tar.gz`.
6. Reuses a live action server on `:5055`, or starts a hidden one it later stops.
7. Runs `uv run rasa inspect`.

`run_rasa_llm.ps1` does the same, plus: sets `HOOPMIND_GROUND_ANSWERS=true`, validates the
Gemini keys, and starts `gemini_proxy.py` on `:8300` (aborting if the proxy fails its health
check) before training.

Manual equivalent, if you prefer separate terminals:

```powershell
python gemini_proxy.py                                              # :8300 (LLM mode only)
python -m rasa_sdk --actions actions --port 5055                    # :5055 — must run from rasa/
uv run rasa inspect --port 5005 -i 127.0.0.1 --cors "*"             # :5005
```

---

## The two modes

`config.yml` and `domain.yml` are **generated files**. `switch_mode.ps1` copies
`config_nlu.yml` / `config_llm.yml` onto `config.yml`, and `domain_modes/domain_nlu.yml` /
`domain_modes/domain_llm.yml` onto `domain.yml`. Edit the mode-specific sources — edits to
`config.yml` or `domain.yml` are overwritten on the next switch or launch. When you add an
intent, slot or response, **update both files in `domain_modes/`**.

```powershell
.\switch_mode.ps1 -Mode nlu               # DIETClassifier, offline
.\switch_mode.ps1 -Mode llm               # Gemini command generator
.\switch_mode.ps1 -Mode nlu -SkipTrain    # swap the files only
.\switch_mode.ps1                         # print the current mode and exit
```

Without `-SkipTrain` the switch retrains automatically.

### NLU mode (`config_nlu.yml`)

```yaml
pipeline:
  - WhitespaceTokenizer
  - RegexFeaturizer
  - CountVectorsFeaturizer            # word level
  - CountVectorsFeaturizer            # char_wb, 1–4 grams
  - EntitySynonymMapper
  - DIETClassifier                    # 30 epochs, BILOU, softmax confidence
  - FallbackClassifier                # threshold 0.3
  - NLUCommandAdapter
policies:
  - FlowPolicy
  - RulePolicy                        # core fallback → action_default_fallback
```

> **`NLUCommandAdapter` must stay last in the pipeline.** It is what turns a predicted intent
> into a flow command; without it the `nlu_trigger` intents never reach the flows and every
> message falls through to the default fallback.

### LLM mode (`config_llm.yml`)

```yaml
pipeline:
  - CompactLLMCommandGenerator
    prompt_template: prompts/gemini_command_prompt.jinja2
    llm:             { model_group: gemini_llm }
    flow_retrieval:  { embeddings: { model_group: gemini_embeddings } }
```

The `gemini_llm` and `gemini_embeddings` model groups are declared in `endpoints.yml` and point
at `http://127.0.0.1:8300/v1beta` — the local proxy — so *all* Gemini-bound traffic (Rasa's own
command generation and embeddings, plus the actions' answer composition) is key-rotated.

---

## Architecture

```
user message
   │
   ├─ NLU mode:  DIETClassifier → intent → NLUCommandAdapter ─┐
   │                                                          ├→ FlowPolicy
   └─ LLM mode:  CompactLLMCommandGenerator (Gemini) ─────────┘        │
                                                                       ▼
                                        data/flows/hoopmind.yml (14 flows)
                                                                       │
                                                    one custom action per flow
                                                                       │
                                              actions/data_loader.py (pandas)
                                                                       │
                                                       data/nba/*.csv (22 files)
                                                                       │
                                       actions/llm_answer.py → template, or Gemini-composed
```

Both modes drive the **same** flows. Every flow in `data/flows/hoopmind.yml` is a single step
that either utters a response or calls one custom action, then ends:

| Flow | Trigger intent | Action / response |
|---|---|---|
| `greeting` | `greeting` | `utter_greeting` |
| `goodbye` | `goodbye` | `utter_goodbye` |
| `default_fallback` | `nlu_fallback` | `utter_default` |
| `player_info` | `player_info` | `action_player_info` |
| `player_stats` | `player_stats` | `action_player_stats` |
| `team_info` | `team_info` | `action_team_info` |
| `team_stats` | `team_stats` | `action_team_stats` |
| `compare` | `compare` | `action_compare` |
| `all_star` | `all_star` | `action_all_star` |
| `draft_info` | `draft_info` | `action_draft_info` |
| `league_info` | `league_info` | `action_league_info` |
| `dataset_scope` | `dataset_scope` | `action_dataset_scope` |
| `award_winner` | `award_winner` | `action_award_winner` |
| `player_awards` | `player_awards` | `action_player_awards` |

In NLU mode the `nlu_trigger:` block selects the flow. In LLM mode the command generator picks
the flow from its `description:` — which is why those descriptions are written as capability
sentences rather than labels.

### Entities and slots

| Entity | Purpose | Examples |
|---|---|---|
| `player` | Player name | LeBron James, Stephen Curry |
| `team` | Team name | Boston Celtics, Golden State Warriors |
| `season` | Season / year | 2023, 2016 |
| `stat` | Which statistic | points, rebounds, PER, true_shooting |
| `stat_type` | Stat format | per 36, per 100, advanced |
| `award` | Award type | MVP, All-Star, Defensive Player of the Year |
| `league` | League | NBA, ABA |
| `position` | Position | PG, C |

Slots (`player`, `player2` via the `second` role, `team`, `season`, `stat_type`, plus the
controlled `return_value`) are all `influence_conversation: false` — they carry data to actions,
they do not steer dialogue.

---

## Custom actions and data access

`actions/action_*.py` — one module per flow, one `Action` subclass per handler
(`action_awards.py` holds both `ActionAwardWinner` and `ActionPlayerAwards`).

**Actions parse the raw utterance themselves.** Each one runs static `_extract_*_from_text`
regex helpers (see [actions/action_player_stats.py](actions/action_player_stats.py)) and only
falls back to slots and entities. Do not assume slot filling populated anything — in LLM mode it
frequently has not.

`actions/entity_extract.py` does name-based extraction against the real CSV vocabularies: it
builds alias tables for players and teams (`TEAM_SYNONYMS`, nickname variants, surname matching
with a minimum length, an ambiguity guard for aliases like `pg` / `ai`), compiles them into one
regex, and exposes `extract_entities(text)` plus the singular/plural helpers
`extract_player(s)`, `extract_team(s)`, `extract_season(s)`.

All data access goes through **`actions/data_loader.py`** (952 lines). Module-level pandas
DataFrames are populated once behind `_ensure_loaded()`; reuse the getters rather than reading
CSVs directly:

```
find_player            get_player_info        get_player_stats        get_career_per_game
find_team              get_team_info          get_team_stats          get_career_totals
get_per_36_stats       get_per_100_stats      get_advanced_stats      get_shooting_stats
get_all_star           get_draft_info         get_draft_year          get_award_winner
get_player_awards      compare_players        get_league_info         get_dataset_scope
normalize_stat_type
```

Name resolution is handled by `_fuzzy_find_player()`, which layers a hand-written nickname map
(`_PLAYER_SYNONYMS` — *mj*, *kd*, *shaq*, *cp3*, *the beard*, …), `difflib` close matching,
last-name lookup, and popularity-weighted substring matching. Traded seasons are collapsed by
`_dedupe_traded_seasons()` so a mid-season trade does not double-count.

### Datasets

`data/nba/` holds the shared HoopMind dataset:
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
byte-identical to `dialogflow-es/data/` — the two implementations share no code, so changing the
CSVs here does not affect the Dialogflow build (and vice versa). Keep them in sync manually if
you refresh the data.

```
Advanced.csv                         Player Career Info.csv        Team Abbrev.csv
All-Star Selections.csv              Player Per Game.csv           Team Stats Per 100 Poss.csv
Draft Pick History.csv               Player Play By Play.csv       Team Stats Per Game.csv
End of Season Teams (Voting).csv     Player Season Info.csv        Team Summaries.csv
End of Season Teams.csv              Player Shooting.csv           Team Totals.csv
Opponent Stats Per 100 Poss.csv      Player Totals.csv
Opponent Stats Per Game.csv          Per 100 Poss.csv
Opponent Totals.csv                  Per 36 Minutes.csv
Player Award Shares.csv
```

---

## Grounded LLM answers and key rotation

Every action builds a **deterministic template string** from the CSV facts first, then passes it
through `compose_answer(question, data_text, fallback)` from
[actions/llm_answer.py](actions/llm_answer.py).

`compose_answer` is a **no-op that returns the template unless `HOOPMIND_GROUND_ANSWERS` is
truthy** (`1` / `true` / `yes`) — only `run_rasa_llm.ps1` sets it. That is what keeps NLU mode
completely offline.

When it is active, it tries three things in order:

1. **The local proxy** at `http://127.0.0.1:8300/v1beta` (which rotates keys internally).
2. **A direct Gemini call** using `actions/gemini_key_manager.py` for local rotation.
3. **The template fallback.**

So an unreachable or rate-limited API degrades to plain template text instead of failing the
turn. The prompt instructs the model to use *only* the supplied data, never to invent numbers,
and never to mention "the data" — the numbers always come from pandas, never from the model.

### `gemini_proxy.py`

A dependency-free `http.server` proxy on `:8300`:

- Loads `GEMINI_API_KEY` and `GEMINI_API_KEY_1..9`.
- Rotates on `429` and `5xx`, with per-key cooldown that grows after `_MAX_FAILURES` (3)
  consecutive failures; `mark_success` clears the record.
- When every key is cooling down it picks the one with the shortest remaining wait and logs it.
- `GET /status` returns per-key availability and remaining cooldown — check it at
  <http://localhost:8300/status>.

```powershell
python gemini_proxy.py                # :8300 (or $env:GEMINI_PROXY_PORT)
python gemini_proxy.py --port 9090
```

`actions/gemini_key_manager.py` is the in-process equivalent used by the direct-call path.

---

## Training data

[data/nlu.yml](data/nlu.yml) is the **source of truth and is hand-maintained**: 1,200 lines,
13 intents, 619 training phrases, 53 synonym blocks and 6 lookup tables
(`player`, `team`, `award`, `stat`, `stat_type`, `league`).
[INTENTS.md](INTENTS.md) documents every intent with its full phrase list.

Two things about this file are easy to get wrong:

> **Synonyms and lookup tables must be items of the top-level `nlu:` list** (`- lookup: player`).
> A sibling top-level `lookup_tables:` key is silently ignored by Rasa — no error, no warning,
> the tables simply never load. Fixing exactly this moved 5-fold accuracy from 0.8000 to 0.8298.

> **Do not run `generate_nlu.py`.** Its hardcoded intent lists are stale: it regenerates only
> ~726 lines (`draft_info` drops from 26 examples to 5), silently destroying roughly 40 % of the
> training data. It carries the `- synonym:` / `- lookup:` blocks over verbatim but rewrites
> every intent block from source. It survives only as a scaffold.

`data/rules.yml` holds the core rules; `prompts/gemini_command_prompt.jinja2` is the LLM-mode
command-generation prompt.

The original Dialogflow ES export and its `convert_dialogflow.py` importer were removed once the
lookup tables they produced lived correctly in `data/nlu.yml`. The live Dialogflow implementation
is [`dialogflow-es/`](../dialogflow-es/README.md).

---

## Evaluating NLU

**Always evaluate with cross-validation:**

```powershell
uv run rasa test nlu --nlu data/nlu.yml --config config.yml --cross-validation -f 5 --out results
```

> A plain `uv run rasa test nlu --nlu data/nlu.yml` has **no held-out split** — it trains and
> tests on the same examples and reports ~99 %. That is a train-set score, not accuracy. The real
> cross-validated figure is ~83 %.

### Cross-validation results

5-fold cross-validation over `config_nlu.yml`, measured on the **605-example snapshot** of
`data/nlu.yml`.

> The file has since grown to 619 examples (`player_stats` 82, `compare` 78, `dataset_scope` 41),
> so the supports below no longer match the current corpus. Re-run the command above to refresh
> the table.

| Intent | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| team_stats | 0.85 | 0.95 | 0.90 | 109 |
| player_info | 0.79 | 0.74 | 0.76 | 81 |
| player_stats | 0.85 | 0.89 | 0.87 | 79 |
| compare | 0.88 | 0.81 | 0.84 | 69 |
| team_info | 0.80 | 0.50 | 0.62 | 40 |
| league_info | 0.86 | 0.92 | 0.89 | 39 |
| dataset_scope | 0.89 | 0.82 | 0.85 | 39 |
| all_star | 0.87 | 0.89 | 0.88 | 37 |
| greeting | 0.51 | 0.85 | 0.64 | 26 |
| draft_info | 0.93 | 1.00 | 0.96 | 26 |
| goodbye | 0.89 | 0.67 | 0.76 | 24 |
| player_awards | 0.80 | 0.67 | 0.73 | 18 |
| award_winner | 0.94 | 0.83 | 0.88 | 18 |
| **macro avg** | **0.83** | **0.81** | **0.81** | **605** |
| **weighted avg** | **0.84** | **0.83** | **0.83** | **605** |

**Overall accuracy: 83.0 %.** The weak spots are `team_info` (recall 0.50 — mostly absorbed by
`team_stats`) and `greeting` (precision 0.51 — it acts as a catch-all for short unrecognised
inputs).

### Held-out test set

`tests/nlu_test.yml` is a separate evaluation set generated from `tests/test.csv`
(`test_id,expected_intent,test_phrase`):

```powershell
uv run python tests/csv_to_nlu.py                                      # test.csv -> nlu_test.yml
uv run rasa test nlu -m models --nlu tests/nlu_test.yml --out results  # score the latest model
```

There is no Python unit-test suite on the Rasa side; NLU evaluation is the test layer.

---

## Project layout

```
rasa/
├── actions/                        custom actions (one module per flow)
│   ├── action_all_star.py          All-Star + end-of-season team selections
│   ├── action_awards.py            ActionAwardWinner + ActionPlayerAwards
│   ├── action_compare.py           player-vs-player and team-vs-team
│   ├── action_dataset_scope.py     "what data do you have?"
│   ├── action_draft_info.py        draft pick / draft class
│   ├── action_league_info.py       league-level facts
│   ├── action_player_info.py       bio, position, height, career span
│   ├── action_player_stats.py      season / career / per-36 / per-100 / advanced / shooting
│   ├── action_team_info.py         arena, conference, division, record
│   ├── action_team_stats.py        team season stats
│   ├── data_loader.py              pandas layer + fuzzy player/team resolution (952 lines)
│   ├── entity_extract.py           CSV-vocabulary alias extraction from raw text
│   ├── gemini_key_manager.py       in-process key rotation for direct Gemini calls
│   └── llm_answer.py               compose_answer(): grounded answer or template fallback
├── data/
│   ├── flows/hoopmind.yml          14 single-step flows
│   ├── nba/                        the 22-CSV Kaggle dataset (~32 MB)
│   ├── nlu.yml                     hand-maintained: 13 intents, 619 phrases, 6 lookup tables
│   └── rules.yml
├── domain_modes/
│   ├── domain_nlu.yml              source domain for NLU mode
│   └── domain_llm.yml              source domain for LLM mode
├── prompts/
│   └── gemini_command_prompt.jinja2
├── tests/
│   ├── csv_to_nlu.py               test.csv -> nlu_test.yml
│   ├── test.csv                    shared intent test phrases (source for nlu_test.yml)
│   └── nlu_test.yml                held-out evaluation set
├── config.yml                      GENERATED — copied from config_{nlu,llm}.yml
├── config_nlu.yml                  DIETClassifier pipeline
├── config_llm.yml                  CompactLLMCommandGenerator pipeline
├── domain.yml                      GENERATED — copied from domain_modes/
├── endpoints.yml                   action endpoint + Gemini model groups (via the proxy)
├── endpoints_nlu.yml               side-by-side mode: action server :5055, no model groups
├── endpoints_llm.yml               side-by-side mode: action server :5056 + model groups
├── credentials.yml                 channel credentials
├── gemini_proxy.py                 local :8300 key-rotation proxy
├── generate_nlu.py                 STALE scaffold — do not run (see Training data)
├── setup.ps1                       uv sync + .env template
├── run_rasa.ps1                    unified launcher / mode picker
├── run_rasa_nlu.ps1                offline launcher
├── run_rasa_llm.ps1                proxy + grounded-answers launcher
├── run_rasa_both.ps1               both modes at once, on separate ports (demos)
├── switch_mode.ps1                 swap config + domain, retrain
├── pyproject.toml / uv.lock        pinned dependencies
├── INTENTS.md                      intents, entities, full phrase lists, eval results
├── .env                            gitignored — created by setup.ps1
├── models/                         trained archives (gitignored)
└── results/                        latest NLU evaluation report (gitignored)
```

---

## Command reference

All commands run from `rasa/`.

| Command | What it does |
|---|---|
| `.\setup.ps1` | `uv sync` → `.venv`, create `.env` template |
| `.\run_rasa.ps1 [-Mode nlu\|llm]` | switch mode if needed, train, start actions + Inspector |
| `.\run_rasa_both.ps1 [-SkipTrain]` | both modes at once — NLU on `:5005`, LLM on `:5006` |
| `.\switch_mode.ps1 -Mode nlu\|llm [-SkipTrain]` | swap `config.yml` + `domain.yml`, retrain |
| `uv run rasa train` | train the full model (NLU + core) into `models/` |
| `uv run rasa inspect` | Inspector UI on `:5005` |
| `uv run rasa run` | HTTP server on `:5005` |
| `uv run rasa shell` | CLI chat |
| `python -m rasa_sdk --actions actions --port 5055` | action server alone (**must run from `rasa/`**) |
| `python gemini_proxy.py` | key-rotation proxy on `:8300` |
| `uv run rasa test nlu --nlu data/nlu.yml --config config.yml --cross-validation -f 5 --out results` | the evaluation that counts |
| `uv run python tests/csv_to_nlu.py` | regenerate `tests/nlu_test.yml` from `tests/test.csv` |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Venv not found at …\.venv\Scripts\python.exe` | Run `.\setup.ps1` from `rasa/` |
| Every message hits the default fallback | `NLUCommandAdapter` missing from the end of the pipeline, or you trained with `rasa train nlu` (no core model). Retrain with `uv run rasa train`. |
| Actions never fire / "action server not reachable" | `:5055` is not up, or `rasa_sdk` was started from the wrong directory — it must run from `rasa/` so `actions.data_loader` resolves |
| Lookup tables seem to have no effect | They must be items of the top-level `nlu:` list (`- lookup: player`), not a separate `lookup_tables:` key |
| `ERROR: No valid API keys found in .env` | Replace the `your-…-key-here` placeholders in `rasa/.env` |
| LLM mode answers look like flat templates | `HOOPMIND_GROUND_ANSWERS` is unset (you launched NLU mode) or Gemini is unreachable — check <http://localhost:8300/status> |
| Edits to `config.yml` / `domain.yml` keep disappearing | They are generated. Edit `config_{nlu,llm}.yml` and `domain_modes/domain_{nlu,llm}.yml`. |
| `rasa test nlu` reports ~99 % accuracy | No held-out split. Add `--cross-validation -f 5`. |
| Port already in use | `Get-NetTCPConnection -LocalPort 5005 -State Listen \| ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }` (same for 5055 / 8300) |
| `port(s) reserved by Windows` / proxy `WinError 10013` | WinNAT/Hyper-V claimed that TCP block at boot — nothing is listening, the port just cannot be bound. List the ranges with `netsh interface ipv4 show excludedportrange protocol=tcp`, then either move `$ProxyPort` (and `api_base` in `endpoints.yml` / `endpoints_llm.yml`) outside them, or release the reservations from an elevated shell with `net stop winnat; net start winnat`. This is why the proxy defaults to `8300`, not `8080`. |
| `run_rasa_both.ps1` says `port(s) already in use` | A single-mode launcher is still running. Close its window, and check `5006` / `5056` too — a crashed Inspector can leave the port held. |
| Side-by-side: `models/hoopmind_*.tar.gz is missing` | You ran `run_rasa_nlu.ps1` after `run_rasa_both.ps1` — its pruning step deleted the older archive. Re-run `run_rasa_both.ps1` without `-SkipTrain`. |
| Side-by-side: the NLU bot gives Gemini-style prose | Both bots are pointing at the same action server. Check that `endpoints_nlu.yml` says `:5055` and `endpoints_llm.yml` says `:5056`. |

---

## Reference

- [INTENTS.md](INTENTS.md) — intents, entities, full training phrase lists, evaluation results
- [example-queries.md](../example-queries.md) — representative and edge-case queries for smoke testing
- [Rasa Pro documentation](https://rasa.com/docs/rasa-pro/)

## Credits

- Data: [NBA / ABA / BAA Stats](https://www.kaggle.com/datasets/sumitrodatta/nba-aba-baa-stats)
  by Sumitro Datta, via [Basketball Reference](https://www.basketball-reference.com/)
- Dialogue engine: [Rasa Pro 3.18](https://rasa.com/docs/rasa-pro/)
- LLM: [Google Gemini](https://ai.google.dev/)
