"""Score usability_responses.csv into SUS, satisfaction, and task-success
metrics, and render a formatted report table.

Usage:
    python evaluation/score_usability.py
"""
from __future__ import annotations
import csv, json
from pathlib import Path

E = Path(__file__).resolve().parent
F = E / 'usability_responses.csv'
OUT = E / 'usability_metrics.json'
REPORT_OUT = E / 'usability_report_formatted.txt'
WIDTH = 78

SAT_KEYS = ['sat_overall', 'sat_accuracy', 'sat_quality', 'sat_speed', 'sat_paraphrase', 'sat_recommend']


def sus(r):
    total = 0
    for i in range(1, 11):
        x = float(r[f'sus{i}'])
        total += x - 1 if i % 2 else 5 - x
    return total * 2.5


def fmt(x, dp=2, suffix=''):
    return f"{x:.{dp}f}{suffix}" if x is not None else "n/a"


def main():
    with F.open(encoding='utf-8-sig', newline='') as f:
        rows = [r for r in csv.DictReader(f)
                if any((r.get(k) or '').strip() for k in r if k != 'respondent')]
    if not rows:
        raise SystemExit('No participant responses yet. Fill usability_responses.csv.')

    per_respondent = []
    for r in rows:
        s = sus(r)
        sat_vals = [float(r[k]) for k in SAT_KEYS if (r.get(k) or '').strip()]
        sat_avg = sum(sat_vals) / len(sat_vals) if sat_vals else None
        task = float(r['task_success_1_to_10']) / 10 * 100 if (r.get('task_success_1_to_10') or '').strip() else None
        per_respondent.append({'respondent': r.get('respondent', '?'), 'sus': s, 'sat': sat_avg, 'task': task})

    scores = [p['sus'] for p in per_respondent]
    sats = [p['sat'] for p in per_respondent if p['sat'] is not None]
    tasks = [p['task'] for p in per_respondent if p['task'] is not None]

    out = {
        'participants': len(rows),
        'average_sus': sum(scores) / len(scores),
        'average_satisfaction_1_to_5': sum(sats) / len(sats) if sats else None,
        'average_task_success_percent': sum(tasks) / len(tasks) if tasks else None,
    }
    OUT.write_text(json.dumps(out, indent=2), encoding='utf-8')

    bar, dash = "=" * WIDTH, "-" * WIDTH
    lines = [bar, "HOOPMIND USABILITY & SATISFACTION EVALUATION", bar, ""]
    lines.append(f"Participants                : {out['participants']}")
    lines.append(f"Average SUS (0-100)         : {fmt(out['average_sus'])}"
                 f"  ({'above' if out['average_sus'] >= 68 else 'below'} the 68 benchmark)")
    lines.append(f"Average Satisfaction (1-5)  : {fmt(out['average_satisfaction_1_to_5'])}")
    lines.append(f"Average Task Success        : {fmt(out['average_task_success_percent'], suffix='%')}")
    lines.append("")
    lines.append(dash)
    lines.append(f"{'Respondent':<18}{'SUS':>10}{'Satisfaction':>16}{'Task Success':>16}")
    lines.append(dash)
    for p in per_respondent:
        lines.append(
            f"{p['respondent']:<18}{fmt(p['sus']):>10}"
            f"{fmt(p['sat']):>16}{fmt(p['task'], suffix='%'):>16}"
        )
    lines.append(bar)

    text = "\n".join(lines)
    REPORT_OUT.write_text(text, encoding='utf-8')
    print(text)
    print(f"\nSaved: {OUT.name}, {REPORT_OUT.name}")


if __name__ == '__main__':
    main()