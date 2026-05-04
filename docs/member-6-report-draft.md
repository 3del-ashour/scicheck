# SciCheck — Member 6: UI & Evaluation Report Draft

**Owner:** Talib Yeşildal  
**Role:** UI + Evaluation Engineer  
**Date:** May 2026  

---

## 1. User Interface Design

### 1.1 Overview
The SciCheck interface is built using **Streamlit**, designed with a modern, premium aesthetic to facilitate a professional live demo. The UI adopts a **Glassmorphism** design language, featuring translucent cards, vibrant accent colors, and a clean typography system using the 'Inter' font family.

### 1.2 Layout and Navigation
The application is organized into three primary functional tabs:

1.  **Fact-Check:** The core interaction hub where users enter scientific claims and receive detailed agent-driven analysis.
2.  **Metrics:** A real-time dashboard displaying system performance metrics (Accuracy, F1-Score) based on SciFact benchmark evaluations.
3.  **Safety Log:** An observability tab that renders events from the `logs/safety_events.jsonl` file, showing flagged claims and safety check results.

### 1.3 Key UI Components
*   **Verdict Badges:** Color-coded status indicators (Supported: Green, Refuted: Red, Insufficient Evidence: Orange) for immediate visual feedback.
*   **Analysis Cards:** Premium containers for the "Verdict Reasoning" and "Confidence Scores," utilizing CSS backdrop-filters.
*   **Evidence Grid:** A responsive grid system that displays retrieved scientific sources, their credibility scores, and text snippets.
*   **Sidebar Examples:** A collection of pre-defined demo claims to ensure a smooth and rapid presentation flow.

---

## 2. Evaluation Pipeline & Results

### 2.1 Methodology
The evaluation system assesses the multi-agent pipeline's accuracy using the **SciFact** benchmark. Due to recent changes in the Hugging Face `datasets` library regarding legacy loading scripts, the pipeline implements a dual-loading strategy:
1.  **Primary:** Attempts to load the validation split of `allenai/scifact` directly from the HF Hub.
2.  **Fallback:** Utilizes a curated internal sample of 10 representative scientific claims (Supported/Refuted/Ambiguous) to ensure continuous testing and demo readiness even without an internet connection.

### 2.2 Performance Metrics
The system calculates metrics using `scikit-learn` across three classes. The following results represent a validation run using the **Mock Pipeline** (heuristic fallback) while the full Orchestrator is under development by Member 1.

| Metric | Value (Mock Fallback) | Target (Full System) |
|---|---|---|
| **Accuracy** | 60.0% | 82.0% |
| **Macro F1-Score** | 0.463 | 0.795 |
| **Citation Precision** | 85.0% | 90.0%+ |

*Note: These metrics are automatically updated in the UI when `scripts/run_eval.py` is executed.*

### 2.3 Evaluation Stack
*   **`src/eval/metrics.py`**: A dedicated module for computing classification metrics.
*   **`src/eval/scifact.py`**: The main evaluation entry point that iterates over the benchmark and aggregates results.
*   **`eval/results.json`**: The persistent storage for evaluation outputs, consumed by the UI dashboard.

---

## 3. Definition of Done Compliance
*   [x] Streamlit UI is fully functional and responsive.
*   [x] Evaluation pipeline is implemented with a robust fallback mechanism.
*   [x] Unit tests for metrics and evaluation logic are passing (`tests/test_eval.py`).
*   [x] All Turkish comments and strings have been translated to English for international consistency.
