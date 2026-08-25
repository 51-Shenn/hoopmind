# HoopMind - Testing Guide

Four layers, from fastest to slowest. Run 1-3 yourself; layer 4 needs human testers.

---

## 1. Start the app

```bat
run_hoopmind.bat
```

Starts Flask (:5000) + Streamlit (:8501). Health check: <http://127.0.0.1:5000/>
Watch the console for `[chat] <raw intent> -> <resolved> | Params=...` lines while testing - they show exactly what the NLU decided.

---

## 2. Automated regression suites (no server needed)

```bat
python -X utf8 evaluation\test_all11.py       :: one case per external intent, rich cards verified
python -X utf8 evaluation\test_no_params.py   :: params arrive EMPTY - entity recovery must fill them
python -X utf8 evaluation\test_messenger.py   :: full card render for every handler shape
```

All three call `webhook.process_message()` directly - the same pipeline `/chat` uses.
**Expected: `FAILURES: none`.**

---

## 3. Automated metrics (put these numbers in the report)

### Intent classification (requirement f/g)

```bat
python -X utf8 evaluation\evaluate_intent.py
```

59 held-out paraphrases (never seen in training) scored P / R / F1 per intent.
Latest offline run (nearest-centroid TF-IDF simulation):

| Metric | Value |
|---|---|
| Accuracy | **0.695** |
| Macro-F1 | **0.595** |

Note: this scores ONLY the classifier. In the app, misroutes are recovered by
`entity_extractor`, the local-classifier reroute guard and chip rules - which is
why end-to-end behaviour is stronger than these raw numbers.
For authoritative Dialogflow numbers: set `GOOGLE_APPLICATION_CREDENTIALS`,
then `python -X utf8 evaluation\evaluate_intent.py --api YOUR_PROJECT_ID`.

### Response quality (BLEU / ROUGE-L)

```bat
python -X utf8 evaluation\evaluate_responses.py
```

21 cases vs human-written reference answers. Latest run:

| Metric | Value |
|---|---|
| Corpus BLEU-4 | 0.037 |
| Avg sentence BLEU | 0.105 |
| Avg ROUGE-L (F1) | **0.233** |

Report caveat: BLEU punishes our structured card output ("Points ⭐ 30.1") against
narrative references ("he averaged 30.1 points"), so low n-gram scores are expected;
ROUGE-L's longest-common-subsequence is the fairer metric here. Results land in
`evaluation\response_eval_results.json`.

---

## 4. Manual UI pass (you)

Open `evaluation\manual_test_checklist.md` - **50 cases** with pre-filled expected
answers generated from the CURRENT engine (regenerate any time):

```bat
python -X utf8 evaluation\gen_manual_checklist.py
```

Covers every handler shape plus the newest features: All-Star tri-state
(played / selected-but-injured / replacement), roster wording modes, draft
overview cards, best-season team compare, latest-season defaults, career-totals
compares, graceful errors.

While ticking boxes, also verify:

- **Chips:** starter chips under greeting/dataset_scope; season-carrying chips on
  team summary cards ("{team} stats in {season}"); compare chip never repeats the
  team you just asked about.
- **Typos:** `Joel Embid` auto-corrects (fuzzy note shown); `warp` stat gives a
  suggestion error; unknown player refuses politely.
- **Empty input:** sending blank does nothing harmful.

Log any failure as: query typed / expected line / actual line.

---

## 5. User satisfaction survey (needs 5+ people)

1. Give each tester `evaluation\usability_survey.md` (8 tasks + SUS + satisfaction).
2. Enter their ratings into `evaluation\usability_responses.csv`
   (copy `usability_responses_template.csv`; integers 1-5).
3. Score it:

```bat
python -X utf8 evaluation\score_usability.py
```

Prints the SUS score (0-100) plus average satisfaction per dimension - quote both
in the report.

---

## 6. Optional: prove the live Dialogflow layer

```bat
setx GOOGLE_APPLICATION_CREDENTIALS "C:\path\to\service-account-key.json"
:: close and reopen the terminal, then start the app again
```

Ask anything; the `[chat]` log should show `source=dialogflow` instead of
`local-classifier`. Then optionally re-run `evaluate_intent.py --api PROJECT_ID`.
(The Dialogflow console "Try It Now" panel cannot display rich cards - those are
built by Flask, not by Google.)
