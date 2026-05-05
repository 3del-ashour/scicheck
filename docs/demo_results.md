# SciCheck — Live Pipeline Results

> **For Ecem (M7):** drop these tables straight into the report's *Evaluation* and *Demo* sections. All numbers are from a real end-to-end run, not estimates.
>
> **Run date:** 2026-05-05
> **Provider:** Groq (Llama 3.3 70B Versatile)
> **Knowledge base:** SciFact corpus, 5,183 abstracts, ChromaDB HNSW + cosine
> **Pipeline:** claim_extractor (M3) → retriever (M4) → credibility (M3) → verdict (M4) → safety (M5)

---

## 1. Demo claim shortlist

| # | Claim | Verdict | Confidence | Top similarity | # citations | Safety |
|---|-------|---------|-----------:|---------------:|------------:|--------|
| 1 | Statins reduce cardiovascular mortality. | **Supported** | 0.90 | 0.75 | 3 | ✅ passed |
| 2 | Smoking causes lung cancer. | **Supported** | 0.85 | 0.67 | 5 | ✅ passed |
| 3 | Beta-blockers reduce mortality after myocardial infarction. | **Supported** | 0.85 | 0.60 | 2 | ✅ passed |
| 4 | Antibiotics are effective against viral infections. | Refuted | 0.00 ⚠️ | 0.51 | 4 | ❌ flagged: `invalid_confidence` |
| 5 | Aspirin reduces the risk of heart attack. | Insufficient Evidence | 0.50 | 0.59 | 5 | ✅ passed |
| 6 | Vitamin C prevents the common cold. | Insufficient Evidence | 0.50 | 0.50 | 5 | ✅ passed |

**Recommended live-demo sequence:** claim 1 (Supported), claim 4 (safety flag — risk-management story), claim 6 (Insufficient Evidence — honesty story). Three claims in three minutes.

---

## 2. Detailed credibility breakdown — claim 3 (beta-blockers)

This is the cleanest example of Bilal's M3 credibility analyzer working as designed: high-quality evidence (RCTs and meta-analyses) properly weighted.

| source_id | Credibility | Flags |
|----------:|------------:|-------|
| 34139429 | **0.90** | rct, peer_reviewed |
| 24586989 | 0.85 | meta_analysis, peer_reviewed |
| 29526125 | 0.80 | rct, peer_reviewed |
| 7873737 | 0.80 | meta_analysis, peer_reviewed |
| 14121786 | 0.70 | peer_reviewed |

**Average credibility:** 0.81. Verdict reasoning explicitly cited the meta-analysis and RCT sources.

---

## 3. Verdict reasoning excerpts (for the report)

### Claim 1 — Statins reduce cardiovascular mortality
> *"Multiple high-credibility sources, including [5698494] and [1287809], support the claim that statins reduce cardiovascular mortality, with [5698494] providing a meta-analysis of randomised controlled trials and [1287809] estimating the cost-effectiveness of statin therapy for primary prevention of cardiovascular disease."*

### Claim 3 — Beta-blockers
> *"The claim is supported by [24586989] and [34139429], which suggest that beta-blockers improve survival in left ventricular systolic dysfunction and reduce mortality in heart failure patients, respectively."*

### Claim 4 — Antibiotics vs viruses (the safety-flag story)
> *"The provided evidence does not support the claim that antibiotics are effective against viral infections. Instead, the sources discuss antiviral treatments, such as Truvada [708425], emtricitabine and tenofovir [14260013], and interferons [3308636], which are used to prevent or treat viral infections, not antibiotics."*

The verdict label and reasoning are correct — but the LLM returned `confidence=0.00`, which Ahmet's safety monitor caught as `invalid_confidence` (Refuted/Supported labels must have confidence ≥ 0.5). This is the project's risk-management requirement working as designed.

---

## 4. Pipeline performance (single-claim latency)

| Stage | Latency (Groq, Llama 3.3 70B) |
|-------|------------------------------:|
| Claim extraction | ~0.4s |
| Query expansion + 3× ChromaDB search | ~0.6s |
| Credibility scoring | ~0.5s |
| Verdict synthesis | ~0.5s |
| Safety monitor (deterministic + LLM judge) | ~0.4s |
| **Total per claim** | **~2.4s** |

(Excludes one-time embedding-model warmup of ~3s on the very first call.)

---

## 5. How to reproduce

```bash
cd ~/scicheck
.venv/bin/python scripts/ingest.py            # populates ChromaDB (~45s)
.venv/bin/python scripts/smoke_run.py "Statins reduce cardiovascular mortality."
```

Or run the full demo set in one shot:

```bash
.venv/bin/python scripts/smoke_run.py \
  "Statins reduce cardiovascular mortality." \
  "Smoking causes lung cancer." \
  "Beta-blockers reduce mortality after myocardial infarction." \
  "Antibiotics are effective against viral infections." \
  "Aspirin reduces the risk of heart attack." \
  "Vitamin C prevents the common cold."
```

---

## 6. What's still pending for the report

- **SciFact-200 evaluation results** — Ahmet to run `python scripts/run_eval.py 200`, will populate `eval/results.json` with accuracy, macro F1, per-class F1, and citation precision.
- **Citation precision** — currently a `0.85` placeholder in `src/eval/scifact.py`; tracked in [issue #11](https://github.com/3del-ashour/scicheck/issues/11) for Talib to wire to real SciFact gold doc IDs.
