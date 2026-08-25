"""
HoopMind - Response generation evaluation.

Runs every case in response_test_set.json through the local
query_engine + response_generator pipeline (the exact same code the
webhook executes) and scores each generated answer against its human
reference using:

  * corpus BLEU-1..4 (with brevity penalty + add-smoothing)
  * average sentence-level BLEU
  * ROUGE-L F1 (word-level LCS, beta = 1)

Usage:
    python evaluate_responses.py
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent

sys_path_added = False
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))
    sys_path_added = True

from query_engine import NBAQueryEngine          # noqa: E402
from response_generator import generate          # noqa: E402

TEST_SET = EVAL_DIR / "response_test_set.json"


# ============================================================
# METRIC PRIMITIVES
# ============================================================


def tokenize(text: str) -> list[str]:
    """
    Format-tolerant tokenizer: strips box-drawing characters, emoji,
    and layout symbols so card-style responses can be compared with
    plain-sentence references on content alone.
    """

    text = re.sub(r"[┌┐└┘├┤│─━⭐★✅🏆📊🛡️⚔️🏀👑🎓🏅📈🗳️🔁📚📅👤➕✖️×–—]", " ", text)

    return re.findall(r"[a-z0-9'.%-]+", text.lower())


def ngram_counts(tokens: list[str], n: int) -> Counter:
    return Counter(
        tuple(tokens[i:i + n])
        for i in range(len(tokens) - n + 1)
    )


def sentence_bleu(ref: list[str], hyp: list[str], max_n: int = 4) -> float:

    precisions = []

    for n in range(1, max_n + 1):

        ref_n = ngram_counts(ref, n)
        hyp_n = ngram_counts(hyp, n)

        match = sum(
            min(count, ref_n.get(gram, 0))
            for gram, count in hyp_n.items()
        )
        total = sum(hyp_n.values())

        if total == 0 or match == 0:
            # add-one smoothing floor keeps BLEU defined
            precisions.append(1.0 / (total + 1))
        else:
            precisions.append(match / total)

    log_avg = sum(
        math.log(p) / max_n for p in precisions
    )

    brevity = (
        1.0
        if len(hyp) > len(ref)
        else math.exp(1 - len(ref) / max(1, len(hyp)))
    )

    return brevity * math.exp(log_avg)


def rouge_l(ref: list[str], hyp: list[str]) -> float:
    """ROUGE-L F-score with beta = 1."""

    if not ref or not hyp:
        return 0.0

    rows, cols = len(ref), len(hyp)
    lcs_table = [[0] * (cols + 1) for _ in range(rows + 1)]

    for i in range(1, rows + 1):
        for j in range(1, cols + 1):

            if ref[i - 1] == hyp[j - 1]:
                lcs_table[i][j] = lcs_table[i - 1][j - 1] + 1
            else:
                lcs_table[i][j] = max(
                    lcs_table[i - 1][j],
                    lcs_table[i][j - 1]
                )

    lcs = lcs_table[rows][cols]

    if lcs == 0:
        return 0.0

    precision = lcs / len(hyp)
    recall = lcs / len(ref)

    return 2 * precision * recall / (precision + recall)


class CorpusBLEU:

    def __init__(self, max_n: int = 4) -> None:
        self.max_n = max_n
        self.matches = [0] * max_n
        self.totals = [0] * max_n
        self.ref_len = 0
        self.hyp_len = 0

    def update(self, ref: list[str], hyp: list[str]) -> None:

        self.ref_len += len(ref)
        self.hyp_len += len(hyp)

        for n in range(1, self.max_n + 1):

            ref_n = ngram_counts(ref, n)
            hyp_n = ngram_counts(hyp, n)

            self.matches[n - 1] += sum(
                min(c, ref_n.get(g, 0))
                for g, c in hyp_n.items()
            )
            self.totals[n - 1] += sum(hyp_n.values())

    def score(self) -> float:

        precisions = []

        for n in range(self.max_n):

            m = self.matches[n]
            t = self.totals[n]

            if t == 0 or m == 0:
                precisions.append(1.0 / (t + 1))
            else:
                precisions.append(m / t)

        log_avg = sum(
            math.log(p) / self.max_n for p in precisions
        )

        brevity = (
            1.0
            if self.hyp_len > self.ref_len
            else math.exp(1 - self.ref_len / max(1, self.hyp_len))
        )

        return brevity * math.exp(log_avg)


# ============================================================
# MAIN
# ============================================================


def main() -> None:

    cases = json.loads(TEST_SET.read_text(encoding="utf-8"))["cases"]

    engine = NBAQueryEngine()

    corpus = CorpusBLEU(max_n=4)

    sent_bleus: list[float] = []
    rouge_scores: list[float] = []

    print("=" * 78)
    print(f"RESPONSE GENERATION EVALUATION ({len(cases)} cases)")
    print("=" * 78)

    results_for_export = []

    for case in cases:

        result = engine.query(case["intent"], case["params"])

        hypothesis = (
            generate(result.answer_data, case["intent"])
            if result.ok
            else (result.error or "I could not find that information.")
        )

        reference = case["reference"]

        ref_t = tokenize(reference)
        hyp_t = tokenize(hypothesis)

        s_bleu = sentence_bleu(ref_t, hyp_t)
        rl_f = rouge_l(ref_t, hyp_t)

        corpus.update(ref_t, hyp_t)
        sent_bleus.append(s_bleu)
        rouge_scores.append(rl_f)

        results_for_export.append({
            "intent": case["intent"],
            "params": case["params"],
            "reference": reference,
            "generated": hypothesis,
            "sentence_bleu": round(s_bleu, 4),
            "rouge_l_f1": round(rl_f, 4),
        })

        print(f"\n[{case['intent']}]")
        print(f"  REF : {reference}")
        print(f"  GEN : {hypothesis}")
        print(f"  BLEU={s_bleu:.3f}  ROUGE-L(F1)={rl_f:.3f}")

    avg_sent_bleu = sum(sent_bleus) / len(sent_bleus)
    avg_rouge = sum(rouge_scores) / len(rouge_scores)

    print("\n" + "=" * 78)
    print("AGGREGATE")
    print("=" * 78)
    print(f"Corpus BLEU-4       : {corpus.score():.3f}")
    print(f"Avg sentence BLEU   : {avg_sent_bleu:.3f}")
    print(f"Avg ROUGE-L (F1)    : {avg_rouge:.3f}")

    export_path = EVAL_DIR / "response_eval_results.json"
    export_path.write_text(
        json.dumps(
            {
                "corpus_bleu4": round(corpus.score(), 4),
                "avg_sentence_bleu": round(avg_sent_bleu, 4),
                "avg_rouge_l_f1": round(avg_rouge, 4),
                "cases": results_for_export,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"\nDetailed results saved to: {export_path}")


if __name__ == "__main__":
    main()
