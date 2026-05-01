# Member 6 — UI + Evaluation Engineer

> **Before starting:** read `README.md`, `ARCHITECTURE.md`, `CONTRACTS.md`, `ROLES.md`.
> Paste this file + `CONTRACTS.md` into Claude Code / ChatGPT for AI assistance.

## Your Mission

You make the project **demoable** and **measurable**. You build:

1. **Streamlit UI** — the live demo. Type a claim → see verdict, evidence, credibility, safety report.
2. **SciFact evaluation pipeline** — runs the orchestrator over a labeled benchmark, reports accuracy/F1.
3. **Metrics dashboard tab** — embedded in the UI, reads `eval/results.json` and `logs/safety_events.jsonl`.

You consume `FinalResponse` from the orchestrator. You don't touch the agents internally.

## Files You Own

```
src/ui/app.py                  # Streamlit app
src/ui/components.py           # reusable render helpers
src/eval/scifact.py            # eval entry point
src/eval/metrics.py            # metric calculations
scripts/run_eval.py            # CLI wrapper
eval/results.example.json      # committed example output
```

---

## Part 1 — Streamlit UI

### Goal

Three tabs: **Fact-Check**, **Metrics**, **Safety Log**.

### Step-by-Step

**Step 1 — App skeleton** (`src/ui/app.py`):

```python
import streamlit as st
from src.orchestrator import run
from src.ui.components import render_per_claim, render_metrics_tab, render_safety_tab

st.set_page_config(page_title="SciCheck", page_icon="🔬", layout="wide")
st.title("SciCheck — Science & Health Misinformation Detector")

tab_check, tab_metrics, tab_safety = st.tabs(["Fact-Check", "Metrics", "Safety Log"])

with tab_check:
    user_input = st.text_area(
        "Enter a science or health claim:",
        placeholder="e.g. Vaccines cause autism.",
        height=100,
    )
    if st.button("Fact-check", type="primary") and user_input.strip():
        with st.spinner("Running multi-agent pipeline…"):
            response = run(user_input)
        st.success(f"Trace ID: {response.trace_id}")
        for pcr in response.per_claim:
            render_per_claim(pcr)

with tab_metrics:
    render_metrics_tab()

with tab_safety:
    render_safety_tab()
```

**Step 2 — Render helpers** (`src/ui/components.py`):

```python
import json
from pathlib import Path
import streamlit as st
from src.contracts import PerClaimResult

LABEL_COLORS = {
    "Supported": "green",
    "Refuted": "red",
    "Insufficient Evidence": "orange",
}

def render_per_claim(pcr: PerClaimResult) -> None:
    color = LABEL_COLORS[pcr.verdict.label]
    st.markdown(f"### Claim: *{pcr.claim.text}*")
    st.markdown(
        f"**Verdict:** :{color}[{pcr.verdict.label}]  "
        f"(confidence {pcr.verdict.confidence:.2f})"
    )
    st.write(pcr.verdict.reasoning)

    with st.expander("Evidence"):
        cred_map = {s.source_id: s for s in pcr.credibility.scored_sources}
        for e in pcr.evidence:
            cred = cred_map.get(e.source_id)
            cited = "✓ cited" if e.source_id in pcr.verdict.citations else ""
            st.markdown(f"**[{e.source_id}] {e.title}** {cited}")
            if cred:
                st.caption(f"credibility {cred.score:.2f} — flags: {cred.flags}")
            st.write(e.text[:600] + ("…" if len(e.text) > 600 else ""))

    if pcr.safety.flags:
        st.warning(f"⚠️ Safety flags: {pcr.safety.flags}")
    else:
        st.info("✓ Safety checks passed")

def render_metrics_tab() -> None:
    p = Path("eval/results.json")
    if not p.exists():
        st.info("Run `python scripts/run_eval.py 200` to populate.")
        return
    data = json.loads(p.read_text())
    c1, c2, c3 = st.columns(3)
    c1.metric("Accuracy", f"{data['accuracy']:.2%}")
    c2.metric("Macro F1", f"{data['macro_f1']:.3f}")
    c3.metric("Citation precision", f"{data['citation_precision']:.2%}")
    st.json(data)

def render_safety_tab() -> None:
    p = Path("logs/safety_events.jsonl")
    if not p.exists():
        st.info("No safety events yet.")
        return
    events = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    st.metric("Total events", len(events))
    st.metric("Failed", sum(1 for e in events if not e["passed"]))
    st.dataframe(events[-50:])
```

**Step 3 — Demo claims to seed UI**

Add a sidebar with example claims for the live demo (saves typing during the 10-min presentation):

```python
with st.sidebar:
    st.header("Demo claims")
    examples = [
        "Vaccines cause autism.",
        "Drinking bleach cures COVID-19.",
        "The earth is round.",
        "Vitamin C prevents the common cold.",
    ]
    for ex in examples:
        if st.button(ex, key=ex):
            st.session_state["seed"] = ex
```

---

## Part 2 — SciFact Evaluation

### Goal

Load SciFact claims with gold labels, run the orchestrator, report metrics.

SciFact labels: `SUPPORT`, `CONTRADICT`, `NEI` (not enough info). Map to ours:
- `SUPPORT` → `Supported`
- `CONTRADICT` → `Refuted`
- `NEI` → `Insufficient Evidence`

### Step-by-Step

**Step 1 — Load** (`src/eval/scifact.py`):

```python
from datasets import load_dataset
from src.orchestrator import run
from src.eval.metrics import compute_metrics

LABEL_MAP = {"SUPPORT": "Supported", "CONTRADICT": "Refuted", "NEI": "Insufficient Evidence"}

def evaluate(n_samples: int = 200) -> dict:
    ds = load_dataset("allenai/scifact", "claims", split="validation")
    sample = ds.select(range(min(n_samples, len(ds))))
    preds: list[str] = []
    golds: list[str] = []
    citation_correct = 0
    citation_total = 0
    for row in sample:
        gold_label = LABEL_MAP[row["evidence_label"]] if row.get("evidence_label") else "Insufficient Evidence"
        gold_doc_ids = {str(d) for d in row.get("evidence_doc_id", [])}
        response = run(row["claim"])
        if not response.per_claim:
            preds.append("Insufficient Evidence")
            golds.append(gold_label)
            continue
        v = response.per_claim[0].verdict
        preds.append(v.label)
        golds.append(gold_label)
        if v.citations and gold_doc_ids:
            citation_total += len(v.citations)
            citation_correct += sum(1 for c in v.citations if c in gold_doc_ids)
    metrics = compute_metrics(golds, preds)
    metrics["citation_precision"] = (citation_correct / citation_total) if citation_total else 0.0
    metrics["n"] = len(sample)
    return metrics
```

**Step 2 — Metrics** (`src/eval/metrics.py`):

```python
from sklearn.metrics import f1_score, accuracy_score, classification_report

LABELS = ["Supported", "Refuted", "Insufficient Evidence"]

def compute_metrics(gold: list[str], pred: list[str]) -> dict:
    return {
        "accuracy": accuracy_score(gold, pred),
        "macro_f1": f1_score(gold, pred, labels=LABELS, average="macro", zero_division=0),
        "per_class_f1": f1_score(gold, pred, labels=LABELS, average=None, zero_division=0).tolist(),
        "report": classification_report(gold, pred, labels=LABELS, zero_division=0, output_dict=True),
    }
```

**Step 3 — Run script** already scaffolded in `scripts/run_eval.py`.

```bash
python scripts/run_eval.py 200   # writes eval/results.json
```

---

## Best Practices for You

- **Cache the orchestrator output for demo claims.** Streamlit's `@st.cache_data` works on the FinalResponse JSON. Keeps the demo snappy.
- **Mobile-friendly columns.** Don't go above 3 columns — projector resolutions vary.
- **Pre-record the eval run.** It can take 10–30 minutes for 200 claims. Run it the night before, commit `eval/results.json`. Only re-run if behavior changes.
- **Color-coded verdicts.** Green/red/orange is the visual money shot of the demo.
- **Show the citations.** Audience needs to see this isn't just an LLM hallucinating answers.

## Definition of Done for Member 6

- [ ] `streamlit run src/ui/app.py` opens a working demo.
- [ ] Three tabs render correctly (Fact-Check, Metrics, Safety Log).
- [ ] `scripts/run_eval.py 50` writes valid JSON.
- [ ] Demo with 4 example claims works end-to-end on at least one teammate's machine.
- [ ] `eval/results.json` committed with N=200 SciFact validation results.

## Report Sections You Write

- UI design (screenshots, user flows, component breakdown)
- Evaluation pipeline (datasets, metrics, results, error analysis)
