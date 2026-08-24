# 🏀 HoopMind - NBA Knowledge Chatbot

HoopMind is a conversational chatbot that answers questions about NBA players,
teams, statistics, awards, All-Star selections and draft history - covering
seasons from 1947 to the present across 22 datasets.

**Ask things like:**

- *"How many points did Stephen Curry average in 2016?"*
- *"Compare Kobe and Jordan career scoring"*
- *"Was Kevin Durant an All-Star in 2022?"* (he was selected but injured)
- *"Show me the complete 2003 NBA draft"*
- *"How stingy was the defense of the Detroit Pistons in 1989?"*
- *"Which team scored more points in 2010, the Lakers or Celtics?"*

**Architecture:** Streamlit chat UI → Flask backend → NLU (Google Dialogflow ES
with an offline fallback classifier) → pandas query engine over Basketball
Reference CSVs → rich answer cards.

---

## Requirements

- **Python 3.10 - 3.12** (developed on 3.12) - <https://www.python.org/downloads/>
  - On the installer's first screen, tick **"Add python.exe to PATH"**.
- Windows (double-click launcher). macOS/Linux work too - see step 3.
- Internet only needed for the optional Google Dialogflow mode; everything
  else runs fully offline.

## Setup

### 1. Get the project

Copy/download the whole `HoopMind_Implementation` folder to your device.
Keep the folder structure intact - especially `data\` (22 CSV files, ~31 MB).

### 2. Install dependencies

Open a terminal **in the project folder**:

```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

(One-time; downloads ~200 MB.)

### 3. Run

**Windows:** double-click

```bat
run_hoopmind.bat
```

Two windows open (API server + chat UI), then use the app at:
**<http://localhost:8501>**

**macOS / Linux:** from the project folder, in two terminals:

```bash
python -X utf8 webhook.py                          # terminal 1: API on :5000
python -X utf8 -m streamlit run streamlit_app.py   # terminal 2: UI on :8501
```

### 4. Stop

Close the two console windows (or Ctrl+C in each).

---

## Optional: enable live Google Dialogflow NLU

Out of the box HoopMind classifies questions with its built-in offline
classifier. To route every message through your Dialogflow ES agent instead:

1. In Google Cloud Console (the project that owns your agent):
   *IAM & Admin → Service Accounts → Create* with the
   **Dialogflow API Client** role, then *Keys → Add key → JSON* and download it.
2. Point the standard Google variable at the key:

   ```bat
   setx GOOGLE_APPLICATION_CREDENTIALS "C:\path\to\your-key.json"
   ```

   Close and reopen the terminal before starting the app.
3. Ask something - the API window log now shows `source=dialogflow`.
   Without a key you'll see `source=local-classifier`; both are fully functional.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Port already in use | Kill leftovers: `Get-NetTCPConnection -LocalPort 5000 -State Listen \| ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }` (same for 8501) |
| `'python' is not recognized` | Reinstall Python with "Add to PATH" ticked, reopen terminal |
| `streamlit: command not found` | Use `python -m streamlit run streamlit_app.py` |
| Emoji look broken in console logs | Harmless display issue; the browser UI is unaffected |
| First question is slow | The engine loads CSVs lazily on first use |

---

## Project layout

```
HoopMind_Implementation\
├── run_hoopmind.bat        one-click launcher
├── webhook.py              Flask /chat endpoint + message pipeline
├── streamlit_app.py        chat interface (rich cards + suggestion chips)
├── dialogflow_client.py    Dialogflow ES detection + offline fallback classifier
├── entity_extractor.py     player/team/season/stat recovery from raw text
├── query_engine.py         all NBA queries over the CSV datasets
├── response_generator.py   text answers + rich card payloads
├── config.py               paths
├── data\                   22 Basketball Reference CSV datasets
└── evaluation\             test suites, metrics scripts, checklists
```

For developers/testers: see **TESTING.md** for the regression suites,
BLEU/ROUGE + intent-F1 evaluation harnesses, the 50-case manual checklist
and the user-satisfaction survey tooling.

## Credits

- Data: [Basketball Reference](https://www.basketball-reference.com/)
- NLU platform: [Google Dialogflow ES](https://cloud.google.com/dialogflow/es/docs)
- UI: [Streamlit](https://streamlit.io/) · API: [Flask](https://flask.palletsprojects.com/)
