# HoopMind Evaluation Folder

This folder evaluates the **actual 13-intent Dialogflow ES chatbot**:

`team_stats`, `league_info`, `team_info`, `draft_info`, `compare`, `player_stats`, `player_awards`, `greeting`, `goodbye`, `dataset_scope`, `player_info`, `award_winner`, `all_star`.

## Important

`test_phrases.csv` is a **held-out evaluation set** of 130 phrases (10 per intent). **Do not upload it to Dialogflow and do not add it as training phrases.** It is used to test the trained agent.

## 1. Intent recognition: Accuracy, Precision, Recall, F1

Set Google credentials and run:

```bash
python evaluation/run_dialogflow_evaluation.py YOUR_PROJECT_ID
```

This sends all 130 phrases to the real Dialogflow ES agent. It creates:

- `test_results.csv` — expected intent, predicted intent, confidence, fulfillment response
- `intent_metrics.json` — Accuracy and macro metrics plus per-intent metrics
- `intent_report.txt` — report suitable for the evaluation section

If the Dialogflow fulfillment webhook is enabled and reachable, `chatbot_response` is also captured. This means the test evaluates the live agent used by HoopMind, not a substitute local classifier.

## 2. Response relevancy/quality and BLEU/ROUGE

After Step 1:

1. Review the chatbot responses in `test_results.csv`.
2. Fill `response_quality_1_to_5` (1=very poor, 5=excellent).
3. For the responses selected for automatic comparison, write a correct `reference_response`.
4. Run:

```bash
python evaluation/evaluate_responses.py
```

It outputs average BLEU-4, ROUGE-L and manual response-quality average to `response_metrics.json`.

Use BLEU/ROUGE as **supplementary** metrics because HoopMind's data-driven answers may be correct even when phrased differently from the reference.

## 3. Usability and satisfaction

Give `usability_survey.md` to participants. Record one row per participant in `usability_responses.csv`, then run:

```bash
python evaluation/score_usability.py
```

This outputs average SUS, satisfaction and task-success rate.

## Recommended final evidence

- Screenshot of Dialogflow ES intent testing / agent configuration
- `intent_report.txt`
- `response_metrics.json`
- `usability_metrics.json`
- Selected examples of correct and incorrect responses

This folder intentionally replaces the older evaluation suite that tested obsolete fine-grained engine routes (23-intent style) or a local centroid approximation. The old files are preserved in `evaluation_legacy/` for reference and are not needed for the final evaluation.
