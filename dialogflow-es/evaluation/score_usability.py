from __future__ import annotations
import csv, json
from pathlib import Path
E=Path(__file__).resolve().parent; F=E/'usability_responses.csv'; OUT=E/'usability_metrics.json'
rows=[]
with F.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f):
        if any((r.get(k) or '').strip() for k in r if k!='respondent'): rows.append(r)
if not rows: raise SystemExit('No participant responses yet. Fill usability_responses.csv.')
def sus(r):
    total=0
    for i in range(1,11):
        x=float(r[f'sus{i}']); total += x-1 if i%2 else 5-x
    return total*2.5
scores=[sus(r) for r in rows]
sats=[]; tasks=[]
for r in rows:
    sats.extend(float(r[k]) for k in ['sat_overall','sat_accuracy','sat_quality','sat_speed','sat_paraphrase','sat_recommend'] if (r.get(k) or '').strip())
    if (r.get('task_success_1_to_10') or '').strip(): tasks.append(float(r['task_success_1_to_10'])/10*100)
out={'participants':len(rows),'average_sus':sum(scores)/len(scores),'average_satisfaction_1_to_5':sum(sats)/len(sats) if sats else None,'average_task_success_percent':sum(tasks)/len(tasks) if tasks else None}
OUT.write_text(json.dumps(out,indent=2),encoding='utf-8'); print(json.dumps(out,indent=2))
