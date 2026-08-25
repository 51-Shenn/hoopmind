# HoopMind

## Overview

HoopMind is a multi-platform AI chatbot project built with three conversational AI frameworks:

- [Rasa Pro](https://rasa.com/docs/rasa-pro/) — open-source, LLM-powered dialogue engine
- [Botpress](https://botpress.com/) — visual chatbot builder
- [Dialogflow ES](https://cloud.google.com/dialogflow/es/docs) — Google's event-driven conversational agent

Each platform is developed independently under its own directory.

## Prerequisites

### Rasa Pro

- **Python 3.11** (required by Rasa Pro 3.18)
- **[uv](https://docs.astral.sh/uv/)** package manager
- **Rasa Pro license** — from [app.rasa.com](https://app.rasa.com/), needed to run Rasa Pro
- **Gemini API key** *(optional)* — only needed for LLM mode

### Botpress

> Coming soon.

### Dialogflow ES

- **Python 3.10–3.12** (developed on 3.12)
- Internet only needed for optional Google Dialogflow NLU mode; the offline classifier works fully offline

## Installation

### Rasa Pro

#### 1. Install uv

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### 2. Create a virtual environment and install dependencies

```powershell
cd rasa
.\setup.ps1
```

This will:
- Create a `.venv` virtual environment (Python 3.11)
- Install exact locked dependencies from `uv.lock`
- Create a `.env` template if one doesn't exist

#### 3. Configure API keys

Edit `rasa/.env` with your credentials:

```env
RASA_LICENSE=your-license-here
GEMINI_API_KEY=your-primary-key-here
GEMINI_API_KEY_1=your-second-key-here
GEMINI_API_KEY_2=your-third-key-here
GEMINI_API_KEY_3=your-fourth-key-here
GEMINI_MODEL=gemini-2.0-flash
```

#### 4. Run the chatbot

```powershell
cd rasa

.\run_rasa.ps1            # asks which mode, then launches it
.\run_rasa.ps1 -Mode nlu  # straight to offline NLU mode (no API key needed)
.\run_rasa.ps1 -Mode llm  # straight to LLM mode (Gemini + key rotation)
```

The launcher automatically switches mode if needed and trains the model on first run (~2 min). See the [Modes](#modes) section for details.

### Botpress

> Coming soon.

### Dialogflow ES

#### 1. Install dependencies

```powershell
cd dialogflow-es
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

#### 2. Run

**Windows:** double-click `run_hoopmind.bat`

**macOS / Linux:** from `dialogflow-es/`, in two terminals:

```bash
python -X utf8 webhook.py                          # terminal 1: API on :5000
python -X utf8 -m streamlit run streamlit_app.py   # terminal 2: UI on :8501
```

Open **http://localhost:8501** in your browser.

## Configuration

### Rasa Pro

#### Environment Variables

Create a `.env` file in the `rasa/` directory:

```
RASA_LICENSE=your-license-key-here
GEMINI_API_KEY=your-primary-key-here
GEMINI_API_KEY_1=your-second-key-here
GEMINI_API_KEY_2=your-third-key-here
GEMINI_API_KEY_3=your-fourth-key-here
GEMINI_MODEL=gemini-2.0-flash
```

#### Modes

Switch between NLU and LLM modes:

```powershell
.\switch_mode.ps1 -Mode nlu    # DIETClassifier (default, offline)
.\switch_mode.ps1 -Mode llm    # Gemini-powered (requires API key)
```

Each switch automatically retrains the model with the new config.

To just chat, use one launcher — it switches mode if needed, trains on first run, manages the action server (`:5055`) in the background, and cleans up on exit:

```powershell
cd rasa                   # switch to rasa/ first
```

```powershell
.\run_rasa.ps1            # interactive mode picker
```

```powershell
.\run_rasa.ps1 -Mode nlu  # offline - Inspector UI on :5005, no API key needed
```

```powershell
.\run_rasa.ps1 -Mode llm  # Gemini - key-rotation proxy on :8080 + server on :5005
```

#### LLM Mode with Key Rotation

Custom actions compose natural-language answers with Gemini, grounded in the stats retrieved from the CSV datasets (`actions/llm_answer.py`). If the API is unreachable, actions fall back to their original template text.

Set up your Gemini API keys in `rasa/.env`:

```
GEMINI_API_KEY=your-primary-key
GEMINI_API_KEY_1=your-second-key
GEMINI_API_KEY_2=your-third-key
GEMINI_API_KEY_3=your-fourth-key
```

The project includes a built-in proxy (`gemini_proxy.py`) that rotates between keys automatically on rate limits or failures. Start everything with:

```powershell
.\run_rasa_llm.ps1
```

Or manually (with `.venv\Scripts\activate`):

```powershell
python gemini_proxy.py                                    # terminal 1: proxy on :8080
python -m rasa_sdk --actions actions --port 5055          # terminal 2: actions on :5055
python -m rasa run --enable-api --cors "*" --port 5005 -i 127.0.0.1   # terminal 3: Rasa on :5005 (localhost only)
```

Check proxy status at `http://localhost:8080/status`.

#### Model Configuration

**NLU mode** (`config.yml`): `WhitespaceTokenizer` → `RegexFeaturizer` → `CountVectorsFeaturizer` (word + char_wb) → `EntitySynonymMapper` → `DIETClassifier` (100 epochs) → `FallbackClassifier`

**LLM mode** (`config_llm.yml`): `CompactLLMCommandGenerator` with Gemini embeddings

### Botpress

> Coming soon.

### Dialogflow ES

No configuration required by default — the built-in offline classifier handles all queries. To enable live Google Dialogflow NLU:

1. Create a service account with the **Dialogflow API Client** role in Google Cloud Console
2. Download the JSON key and set:

   ```powershell
   setx GOOGLE_APPLICATION_CREDENTIALS "C:\path\to\your-key.json"
   ```

3. Restart the terminal — the API log will show `source=dialogflow` when active

## Usage

### Rasa Pro

All commands should be run from the `rasa/` directory with the virtual environment activated.

#### Train the model

```powershell
uv run rasa train
```

Trains a Rasa model and saves it to `rasa/models/`.

#### Inspect flows

```powershell
uv run rasa inspect
```

Opens the Rasa Inspector to debug and visualize conversation flows.

#### Run the server

```powershell
uv run rasa run
```

Starts the Rasa HTTP server (default: `http://localhost:5005`).

#### Train NLU model

```powershell
uv run rasa train nlu
```

Trains intent classification only (no dialogue). Model saved to `rasa/models/`.

#### Test NLU model

```powershell
uv run rasa test nlu
```

Runs 80/20 train-test split evaluation. Results saved to `rasa/results/`.

#### Cross-validation

```powershell
uv run rasa test nlu --cross-validation -f 10
```

Runs 10-fold cross-validation for more reliable intent performance estimates.

### Botpress

> Coming soon.

### Dialogflow ES

From `dialogflow-es/`:

```powershell
python -X utf8 webhook.py                          # API server on :5000
python -X utf8 -m streamlit run streamlit_app.py   # Chat UI on :8501
```

Stop with Ctrl+C in each terminal, or close the windows.

## Project Structure

```
hoopmind/
├── rasa/                   # Rasa Pro assistant
│   ├── actions/            # Custom action code
│   ├── data/               # Training data (flows + NLU)
│   │   └── nba/            # NBA raw data files
│   ├── domain.yml          # Active domain (copied from domain_modes/ by switch_mode)
│   ├── domain_modes/       # Per-mode domain templates (nlu + llm)
│   ├── models/             # Trained model archives
│   ├── results/            # NLU evaluation reports
│   ├── .env                # API keys + license (gitignored, created by setup.ps1)
│   ├── config.yml          # Active pipeline config (copied from config_*.yml)
│   ├── config_llm.yml      # LLM mode: CompactLLMCommandGenerator + Gemini
│   ├── config_nlu.yml      # NLU mode: DIETClassifier + TEDPolicy
│   ├── credentials.yml     # Input/output channel credentials
│   ├── endpoints.yml       # Action server & LLM endpoint config
│   ├── gemini_proxy.py     # Local key-rotation proxy (:8080)
│   ├── switch_mode.ps1     # Switch NLU/LLM mode + auto-train
│   ├── setup.ps1           # First-time venv + dependency setup
│   ├── run_rasa.ps1        # One-command launcher (mode picker → nlu/llm)
│   ├── run_rasa_llm.ps1    # LLM launcher (proxy + actions + server)
│   ├── run_rasa_nlu.ps1    # Offline NLU launcher (auto-train + Inspector)
│   └── INTENTS.md          # Intent & training phrase documentation
├── botpress/               # Botpress integration (planned)
├── dialogflow-es/          # Dialogflow ES integration
│   ├── data/               # 22 Basketball Reference CSV datasets
│   ├── evaluation/         # Test suites, metrics scripts, checklists
│   ├── webhook.py          # Flask /chat endpoint + message pipeline
│   ├── streamlit_app.py    # Chat UI (rich cards + suggestion chips)
│   ├── dialogflow_client.py# Dialogflow ES detection + offline fallback
│   ├── entity_extractor.py # Player/team/season/stat recovery from text
│   ├── query_engine.py     # NBA queries over CSV datasets
│   ├── response_generator.py# Text answers + rich card payloads
│   ├── config.py           # Paths
│   ├── run_hoopmind.bat    # One-click launcher (Windows)
│   └── requirements.txt    # Python dependencies
└── LICENSE
```

## License

[MIT](LICENSE) — Copyright (c) 2026 Tan Yit Shen
