# HoopMind

## Overview

HoopMind is a multi-platform AI chatbot project built with three conversational AI frameworks:

- [Rasa Pro](https://rasa.com/docs/rasa-pro/) — open-source, LLM-powered dialogue engine
- [Botpress](https://botpress.com/) — visual chatbot builder
- [Dialogflow ES](https://cloud.google.com/dialogflow/es/docs) — Google's event-driven conversational agent

Each platform is developed independently under its own directory.

## Prerequisites

### Rasa Pro

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **API key** — OpenAI or Google Gemini (for LLM-powered dialogue understanding)

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

#### 2. Create a virtual environment

```powershell
cd rasa
uv venv --python 3.13
.venv\Scripts\activate
```

#### 3. Install Rasa Pro

```powershell
uv pip install rasa-pro
```

#### 4. Initialize the project

```powershell
uv run rasa init
```

For the full installation transcript, see [`rasa/docs/INSTALLATION.md`](rasa/docs/INSTALLATION.md).

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
OPENAI_API_KEY=your-api-key-here
```

Or configure Gemini credentials if using Google's LLM.

#### Model Configuration

The assistant is configured in `rasa/config.yml`:

- **Pipeline**: `WhitespaceTokenizer` → `RegexFeaturizer` → `CountVectorsFeaturizer` (word + char_wb) → `EntitySynonymMapper` → `DIETClassifier` (100 epochs) → `FallbackClassifier`
- **Policies**: `FlowPolicy`

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
rasa train nlu
```

Trains intent classification only (no dialogue). Model saved to `rasa/models/`.

#### Test NLU model

```powershell
rasa test nlu
```

Runs 80/20 train-test split evaluation. Results saved to `rasa/results/`.

#### Cross-validation

```powershell
rasa test nlu --cross-validation -f 10
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
│   ├── data/nba/           # NBA raw data files
│   ├── domain/             # Domain definitions
│   ├── models/             # Trained model archives
│   ├── results/            # NLU evaluation reports
│   ├── config.yml          # Pipeline & policy configuration
│   ├── credentials.yml     # Input/output channel credentials
│   └── endpoints.yml       # Action server & tracker store config
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
