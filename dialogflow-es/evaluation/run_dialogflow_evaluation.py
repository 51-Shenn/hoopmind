"""
Evaluate HoopMind's ACTUAL 13 Dialogflow ES intents using test_phrases.csv.

Usage:
    python evaluation/run_dialogflow_evaluation.py YOUR_PROJECT_ID

Requirements:
    pip install -r requirements.txt
    Set GOOGLE_APPLICATION_CREDENTIALS to a Dialogflow service-account JSON key.

The test phrases are NOT training data and must NOT be imported into Dialogflow.
Results are written to evaluation/test_results.csv and evaluation/intent_metrics.json.
"""
from __future__ import annotations
import argparse, csv, json, sys, uuid
from collections import defaultdict
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
TEST_FILE = EVAL_DIR / "test_phrases.csv"
RESULT_FILE = EVAL_DIR / "test_results.csv"
METRICS_FILE = EVAL_DIR / "intent_metrics.json"
REPORT_FILE = EVAL_DIR / "intent_report.txt"

FIELDS = ["test_id","expected_intent","test_phrase","predicted_intent","confidence","correct","chatbot_response","response_quality_1_to_5","reference_response"]

def metrics(rows):
    labels = sorted({r['expected_intent'] for r in rows} | {r['predicted_intent'] for r in rows})
    out={"per_intent":{},"overall":{}}
    correct=sum(r['expected_intent']==r['predicted_intent'] for r in rows)
    for label in labels:
        tp=sum(r['expected_intent']==label and r['predicted_intent']==label for r in rows)
        fp=sum(r['expected_intent']!=label and r['predicted_intent']==label for r in rows)
        fn=sum(r['expected_intent']==label and r['predicted_intent']!=label for r in rows)
        p=tp/(tp+fp) if tp+fp else 0.0
        rec=tp/(tp+fn) if tp+fn else 0.0
        f1=2*p*rec/(p+rec) if p+rec else 0.0
        out['per_intent'][label]={"precision":p,"recall":rec,"f1":f1,"support":tp+fn}
    vals=list(out['per_intent'].values())
    out['overall']={
        "total_tests":len(rows),
        "accuracy":correct/len(rows) if rows else 0.0,
        "macro_precision":sum(v['precision'] for v in vals)/len(vals) if vals else 0.0,
        "macro_recall":sum(v['recall'] for v in vals)/len(vals) if vals else 0.0,
        "macro_f1":sum(v['f1'] for v in vals)/len(vals) if vals else 0.0,
    }
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('project_id', help='Google Cloud project ID of the Dialogflow ES agent')
    ap.add_argument('--session-prefix', default='hoopmind-eval')
    args=ap.parse_args()
    try:
        from google.cloud import dialogflow
    except ImportError:
        sys.exit('Missing google-cloud-dialogflow. Run: pip install -r requirements.txt')
    with TEST_FILE.open(encoding='utf-8-sig', newline='') as f:
        tests=list(csv.DictReader(f))
    client=dialogflow.SessionsClient()
    rows=[]
    for i,t in enumerate(tests,1):
        session=client.session_path(args.project_id, f'{args.session_prefix}-{uuid.uuid4().hex[:12]}')
        qi=dialogflow.QueryInput(text=dialogflow.TextInput(text=t['test_phrase'], language_code='en'))
        result=client.detect_intent(request={'session':session,'query_input':qi}).query_result
        pred=result.intent.display_name if result.intent.display_name else 'Default Fallback Intent'
        conf=float(result.intent_detection_confidence)
        rows.append({
            'test_id':t['test_id'],'expected_intent':t['expected_intent'],'test_phrase':t['test_phrase'],
            'predicted_intent':pred,'confidence':f'{conf:.4f}',
            'correct':int(pred==t['expected_intent']),
            'chatbot_response':result.fulfillment_text or '',
            'response_quality_1_to_5':'','reference_response':''
        })
        print(f'[{i:03}/{len(tests)}] {t["expected_intent"]:<16} -> {pred:<16} {conf:.2f}')
    with RESULT_FILE.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    m=metrics(rows)
    METRICS_FILE.write_text(json.dumps(m,indent=2),encoding='utf-8')
    lines=['HOOPMIND DIALOGFLOW ES INTENT EVALUATION','='*55]
    lines.append(f"Tests: {m['overall']['total_tests']}")
    lines.append(f"Accuracy: {m['overall']['accuracy']:.4f}")
    lines.append(f"Macro Precision: {m['overall']['macro_precision']:.4f}")
    lines.append(f"Macro Recall: {m['overall']['macro_recall']:.4f}")
    lines.append(f"Macro F1: {m['overall']['macro_f1']:.4f}\n")
    lines.append('INTENT                 PRECISION  RECALL   F1      SUPPORT')
    for label,v in m['per_intent'].items():
        lines.append(f"{label:<22} {v['precision']:<10.4f} {v['recall']:<8.4f} {v['f1']:<7.4f} {v['support']}")
    REPORT_FILE.write_text('\n'.join(lines),encoding='utf-8')
    print('\n'+REPORT_FILE.read_text(encoding='utf-8'))
    print(f'\nSaved: {RESULT_FILE.name}, {METRICS_FILE.name}, {REPORT_FILE.name}')
if __name__=='__main__': main()
