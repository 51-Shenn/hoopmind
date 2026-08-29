"""Evaluate response quality from completed test_results.csv.

After run_dialogflow_evaluation.py + generate_chatbot_responses.py, fill
reference_response for the cases you want scored (see
build_reference_responses.py for an automated way to do this from raw data),
and fill response_quality_1_to_5 manually with your own judgement.

Usage:
    python evaluation/evaluate_responses.py
"""
from __future__ import annotations
import csv, math, re, json
from collections import Counter, defaultdict
from pathlib import Path

E = Path(__file__).resolve().parent
F = E / 'test_results.csv'
OUT = E / 'response_metrics.json'
REPORT_OUT = E / 'response_report_formatted.txt'
WIDTH = 78


def tok(s): return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", (s or '').lower())
def ngrams(x, n): return Counter(tuple(x[i:i + n]) for i in range(max(0, len(x) - n + 1)))


def bleu(ref, hyp, max_n=4):
    r, h = tok(ref), tok(hyp)
    if not h or not r: return 0.0
    ps = []
    for n in range(1, max_n + 1):
        hc, rc = ngrams(h, n), ngrams(r, n); total = sum(hc.values())
        match = sum(min(c, rc[g]) for g, c in hc.items())
        ps.append((match + 1) / (total + 1))
    bp = 1.0 if len(h) > len(r) else math.exp(1 - len(r) / len(h))
    return bp * math.exp(sum(math.log(p) for p in ps) / max_n)


def rouge_l(ref, hyp):
    a, b = tok(ref), tok(hyp)
    if not a or not b: return 0.0
    dp = [0] * (len(b) + 1)
    for x in a:
        prev = 0
        for j, y in enumerate(b, 1):
            old = dp[j]; dp[j] = prev + 1 if x == y else max(dp[j], dp[j - 1]); prev = old
    l = dp[-1]; p = l / len(b); r = l / len(a)
    return 2 * p * r / (p + r) if p + r else 0.0


def fmt_pct(x):
    return f"{x * 100:.2f}%" if x is not None else "n/a"


def fmt_avg(x, dp=2):
    return f"{x:.{dp}f}" if x is not None else "n/a"


def main():
    if not F.exists(): raise SystemExit('Run run_dialogflow_evaluation.py first.')
    with F.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))

    pairs = [r for r in rows if r.get('reference_response', '').strip() and r.get('chatbot_response', '').strip()]
    ratings_rows = [r for r in rows if r.get('response_quality_1_to_5', '').strip()]
    ratings = [float(r['response_quality_1_to_5']) for r in ratings_rows]

    for r in pairs:
        r['_bleu'] = bleu(r['reference_response'], r['chatbot_response'])
        r['_rouge'] = rouge_l(r['reference_response'], r['chatbot_response'])

    result = {
        'scored_responses': len(pairs),
        'average_bleu_4': sum(r['_bleu'] for r in pairs) / len(pairs) if pairs else None,
        'average_rouge_l': sum(r['_rouge'] for r in pairs) / len(pairs) if pairs else None,
        'manual_quality_ratings': len(ratings),
        'average_response_quality_1_to_5': sum(ratings) / len(ratings) if ratings else None,
    }
    OUT.write_text(json.dumps(result, indent=2), encoding='utf-8')

    # ---- per-intent breakdown ----
    by_intent = defaultdict(lambda: {'bleu': [], 'rouge': [], 'quality': []})
    for r in pairs:
        by_intent[r['expected_intent']]['bleu'].append(r['_bleu'])
        by_intent[r['expected_intent']]['rouge'].append(r['_rouge'])
    for r in ratings_rows:
        by_intent[r['expected_intent']]['quality'].append(float(r['response_quality_1_to_5']))

    def avg(lst): return sum(lst) / len(lst) if lst else None

    bar, dash = "=" * WIDTH, "-" * WIDTH
    lines = [bar, "HOOPMIND RESPONSE QUALITY EVALUATION (BLEU / ROUGE / Manual Rating)", bar, ""]
    lines.append(f"Scored responses (BLEU/ROUGE) : {result['scored_responses']}")
    lines.append(f"Average BLEU-4                : {fmt_pct(result['average_bleu_4'])}")
    lines.append(f"Average ROUGE-L               : {fmt_pct(result['average_rouge_l'])}")
    lines.append(f"Manual quality ratings        : {result['manual_quality_ratings']}")
    lines.append(f"Average quality (1-5)         : {fmt_avg(result['average_response_quality_1_to_5'])}")
    lines.append("")
    lines.append(dash)
    lines.append(f"{'Intent':<18}{'Scored':>8}{'Avg BLEU-4':>13}{'Avg ROUGE-L':>14}{'Avg Quality':>14}")
    lines.append(dash)
    for name in sorted(by_intent):
        d = by_intent[name]
        n_scored = max(len(d['bleu']), len(d['quality']))
        if n_scored == 0:
            continue
        lines.append(
            f"{name:<18}{n_scored:>8}{fmt_pct(avg(d['bleu'])):>13}"
            f"{fmt_pct(avg(d['rouge'])):>14}{fmt_avg(avg(d['quality'])):>14}"
        )
    lines.append(bar)

    text = "\n".join(lines)
    REPORT_OUT.write_text(text, encoding='utf-8')
    print(text)
    if not pairs:
        print('\nNo BLEU/ROUGE calculated yet: fill reference_response and ensure chatbot_response exists.')
    if not ratings:
        print('No manual quality average yet: fill response_quality_1_to_5 with 1-5 ratings.')
    print(f"\nSaved: {OUT.name}, {REPORT_OUT.name}")


if __name__ == '__main__':
    main()