"""Evaluation utilities for the C2 diagnostic classification model."""

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)


def evaluate_model(model, X_test, y_test) -> dict:
    """Evaluate a fitted model on a held-out test set."""

    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    report = classification_report(
        y_test,
        predictions,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=list(model.classes_),
    )

    results = {
        "accuracy": float(accuracy),
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
        "class_labels": list(model.classes_),
    }

    return results