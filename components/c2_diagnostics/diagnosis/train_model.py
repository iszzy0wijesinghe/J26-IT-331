"""Train and evaluate the C2 diagnostic classification model."""

from pathlib import Path

import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.pipeline import Pipeline

from components.c2_diagnostics.diagnosis.feature_builder import (
    load_dataset,
    build_features,
    split_dataset,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

MODEL_DIR = PROJECT_ROOT / "models" / "c2_diagnostics"
MODEL_PATH = MODEL_DIR / "random_forest.joblib"


def train_model() -> None:
    """Train the Random Forest model and evaluate its test performance."""

    # 1. Load dataset
    df = load_dataset()

    # 2. Prepare features and labels
    X, y = build_features(df)

    # 3. Split dataset before fitting preprocessing
    X_train, X_test, y_train, y_test = split_dataset(X, y)

    # 4. Build preprocessing + model pipeline
    model = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                    add_indicator=True,
                ),
            ),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=200,
                    random_state=42,
                    class_weight="balanced",
                    n_jobs=-1,
                ),
            ),
        ]
    )

    # 5. Train
    model.fit(X_train, y_train)

    # 6. Evaluate on held-out test data
    predictions = model.predict(X_test)

    print("\n========== C2 MODEL EVALUATION ==========")
    print(f"Dataset size: {len(df)}")
    print(f"Training samples: {len(X_train)}")
    print(f"Testing samples: {len(X_test)}")
    print(f"Number of features: {X.shape[1]}")
    print(f"Accuracy: {accuracy_score(y_test, predictions):.4f}")

    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0,
        )
    )

    print("Confusion Matrix:")
    print(confusion_matrix(y_test, predictions))

    # 7. Save trained pipeline
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    print(f"\nModel saved to: {MODEL_PATH}")


if __name__ == "__main__":
    train_model()