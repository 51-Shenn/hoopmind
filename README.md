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

> Coming soon.

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

> Coming soon.

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

> Coming soon.

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

#### Inspect flows

### Botpress

> Coming soon.

### Dialogflow ES

> Coming soon.

## Project Structure

```
hoopmind/
├── rasa/                  # Rasa Pro assistant
│   ├── actions/           # Custom action code
│   ├── data/              # Training data (flows + NLU)
│   ├── data/nba/          # NBA raw data files
│   ├── domain/            # Domain definitions
│   ├── e2e_tests/         # End-to-end test stories
│   ├── models/            # Trained model archives
│   ├── results/           # NLU evaluation reports
│   ├── config.yml         # Pipeline & policy configuration
│   ├── credentials.yml    # Input/output channel credentials
│   └── endpoints.yml      # Action server & tracker store config
├── botpress/              # Botpress integration (planned)
├── dialogflow-es/         # Dialogflow ES integration (planned)
└── LICENSE
```

## License

[MIT](LICENSE) — Copyright (c) 2026 Tan Yit Shen
