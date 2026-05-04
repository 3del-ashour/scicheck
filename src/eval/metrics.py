from __future__ import annotations

from sklearn.metrics import accuracy_score, classification_report, f1_score

LABELS = ["Supported", "Refuted", "Insufficient Evidence"]


def compute_metrics(gold: list[str], pred: list[str]) -> dict:
    """Compute SciCheck standard metrics.

    Args:
        gold: list of ground truth labels
        pred: list of predicted labels

    Returns:
        Dictionary with accuracy, macro_f1, per_class_f1, and full report.
    """
    return {
        "accuracy": float(accuracy_score(gold, pred)),
        "macro_f1": float(f1_score(gold, pred, labels=LABELS, average="macro", zero_division=0)),
        "per_class_f1": f1_score(
            gold, pred, labels=LABELS, average=None, zero_division=0
        ).tolist(),
        "report": classification_report(
            gold, pred, labels=LABELS, zero_division=0, output_dict=True
        ),
    }
