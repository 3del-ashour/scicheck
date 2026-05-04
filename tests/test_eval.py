from __future__ import annotations

from src.eval.metrics import compute_metrics
from src.eval.scifact import evaluate


def test_compute_metrics():
    gold = ["Supported", "Refuted", "Insufficient Evidence"]
    pred = ["Supported", "Refuted", "Supported"]
    metrics = compute_metrics(gold, pred)
    
    assert "accuracy" in metrics
    assert "macro_f1" in metrics
    assert "per_class_f1" in metrics
    assert metrics["accuracy"] == 2 / 3


def test_evaluate_sample():
    # Use a small number of samples to test the fallback
    results = evaluate(n_samples=2)
    
    assert "accuracy" in results
    assert "n_samples" in results
    assert results["n_samples"] == 2
    assert "using_mock_pipeline" in results
