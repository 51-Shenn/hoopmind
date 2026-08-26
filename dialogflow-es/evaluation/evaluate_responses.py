"""Evaluate response quality from completed test_results.csv.

After run_dialogflow_evaluation.py, fill reference_response for the cases you
want to score. The chatbot_response is collected automatically when Dialogflow
fulfillment/webhook is active. Also fill response_quality_1_to_5 manually.

Usage:
    python evaluation/evaluate_responses.py
"""
from __future__ import annotations
import csv, math, re, json
from collections import Counter
from pathlib import Path
E=Path(__file__).resolve().parent
F=E/'test_results.csv'
OUT=E/'response_metrics.json'

def tok(s): return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", (s or '').lower())
def ngrams(x,n): return Counter(tuple(x[i:i+n]) for i in range(max(0,len(x)-n+1)))
def bleu(ref,hyp,max_n=4):
    r,h=tok(ref),tok(hyp)
    if not h or not r:return 0.0
    ps=[]
    for n in range(1,max_n+1):
        hc,rc=ngrams(h,n),ngrams(r,n); total=sum(hc.values())
        match=sum(min(c,rc[g]) for g,c in hc.items())
        ps.append((match+1)/(total+1))
    bp=1.0 if len(h)>len(r) else math.exp(1-len(r)/len(h))
    return bp*math.exp(sum(math.log(p) for p in ps)/max_n)
def rouge_l(ref,hyp):
    a,b=tok(ref),tok(hyp)
    if not a or not b:return 0.0
    dp=[0]*(len(b)+1)
    for x in a:
        prev=0
        for j,y in enumerate(b,1):
            old=dp[j]; dp[j]=prev+1 if x==y else max(dp[j],dp[j-1]); prev=old
    l=dp[-1]; p=l/len(b); r=l/len(a)
    return 2*p*r/(p+r) if p+r else 0.0
def main():
    if not F.exists(): raise SystemExit('Run run_dialogflow_evaluation.py first.')
    with F.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    pairs=[r for r in rows if r.get('reference_response','').strip() and r.get('chatbot_response','').strip()]
    ratings=[float(r['response_quality_1_to_5']) for r in rows if r.get('response_quality_1_to_5','').strip()]
    result={
      'scored_responses':len(pairs),
      'average_bleu_4':sum(bleu(r['reference_response'],r['chatbot_response']) for r in pairs)/len(pairs) if pairs else None,
      'average_rouge_l':sum(rouge_l(r['reference_response'],r['chatbot_response']) for r in pairs)/len(pairs) if pairs else None,
      'manual_quality_ratings':len(ratings),
      'average_response_quality_1_to_5':sum(ratings)/len(ratings) if ratings else None,
    }
    OUT.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    if not pairs: print('\nNo BLEU/ROUGE calculated yet: fill reference_response and ensure chatbot_response exists.')
    if not ratings: print('No manual quality average yet: fill response_quality_1_to_5 with 1-5 ratings.')
if __name__=='__main__': main()
