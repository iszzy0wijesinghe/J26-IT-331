
"""SHAP explainability for C4 behavioral models."""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    import shap
except ImportError:
    print("SHAP is not installed. Install it with: pip install shap")
    sys.exit(1)

from components.c4_trust.data_split import ScenarioAwareSplitter  # noqa: E402
from components.c4_trust.features import FeatureExtractor  # noqa: E402
from components.c4_trust.models import TrainedModel  # noqa: E402


def load_splits(
    data_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_df = pd.read_csv(data_dir / "C4_train.csv")
    val_df = pd.read_csv(data_dir / "C4_val.csv")
    test_df = pd.read_csv(data_dir / "C4_test.csv")

    ScenarioAwareSplitter.validate_splits(
        {"train": train_df, "val": val_df, "test": test_df},
        device_id_col="device_id",
    )

    return train_df, val_df, test_df


def prepare_features_labels(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    return FeatureExtractor().extract_for_training(df)


def scale_features(
    X: pd.DataFrame,
    model: TrainedModel,
) -> np.ndarray:
    if list(X.columns) != model.feature_names:
        raise ValueError(
            "Feature schema mismatch. The extracted feature names "
            "do not match the saved model."
        )

    if model.scaler is not None:
        return model.scaler.transform(X)

    return X.to_numpy()


def get_class_shap_values(
    raw_values,
    n_samples: int,
    n_features: int,
) -> list[np.ndarray]:
    if isinstance(raw_values, list):
        values_by_class = [np.asarray(values) for values in raw_values]
    else:
        values = np.asarray(raw_values)

        if values.ndim == 2:
            if values.shape != (n_samples, n_features):
                raise ValueError(
                    f"Unexpected SHAP shape: {values.shape}"
                )
            values_by_class = [values]

        elif values.ndim == 3:
            if values.shape[0] == n_samples and values.shape[1] == n_features:
                values_by_class = [
                    values[:, :, class_index]
                    for class_index in range(values.shape[2])
                ]
            elif values.shape[0] == n_samples and values.shape[2] == n_features:
                values_by_class = [
                    values[:, class_index, :]
                    for class_index in range(values.shape[1])
                ]
            else:
                raise ValueError(
                    f"Unexpected multi-class SHAP shape: {values.shape}"
                )
        else:
            raise ValueError(
                f"Unsupported SHAP output dimensions: {values.shape}"
            )

    for values in values_by_class:
        if values.shape != (n_samples, n_features):
            raise ValueError(
                f"Expected SHAP shape {(n_samples, n_features)}, "
                f"received {values.shape}"
            )

    return values_by_class


def get_class_names(model: TrainedModel) -> list:
    if hasattr(model.model, "classes_"):
        return list(model.model.classes_)

    return list(range(len(model.model.predict_proba(
        np.zeros((1, len(model.feature_names)))
    )[0])))


def get_expected_value(
    explainer: shap.Explainer,
    class_index: int,
) -> float:
    expected = np.asarray(explainer.expected_value)

    if expected.ndim == 0:
        return float(expected)

    return float(expected.reshape(-1)[class_index])


def generate_shap_explainer(
    model: TrainedModel,
    X_background: pd.DataFrame,
    n_background: int = 100,
) -> shap.Explainer:
    X_background_scaled = scale_features(X_background, model)

    if len(X_background_scaled) > n_background:
        rng = np.random.default_rng(42)
        indices = rng.choice(
            len(X_background_scaled),
            size=n_background,
            replace=False,
        )
        X_background_scaled = X_background_scaled[indices]


    return shap.TreeExplainer(
        model.model,
        data=X_background_scaled,
    )


def explain_feature_importance(
    explainer: shap.Explainer,
    X_test: pd.DataFrame,
    model: TrainedModel,
    plots_dir: Path,
    max_display: int = 20,
) -> list[np.ndarray]:
    X_test_scaled = scale_features(X_test, model)

    print("\nCalculating SHAP values...")
    raw_values = explainer.shap_values(X_test_scaled)

    values_by_class = get_class_shap_values(
        raw_values,
        n_samples=len(X_test_scaled),
        n_features=len(model.feature_names),
    )

    class_names = get_class_names(model)

    summary_class_index = 0
    summary_values = values_by_class[summary_class_index]

    summary_class_name = (
        class_names[summary_class_index]
        if summary_class_index < len(class_names)
        else summary_class_index
    )

    print(
        f"Generating SHAP summary plot for class: {summary_class_name}"
    )

    shap.summary_plot(
        summary_values,
        X_test_scaled,
        feature_names=model.feature_names,
        max_display=max_display,
        show=False,
    )

    plt.savefig(
        plots_dir / "shap_summary.png",
        bbox_inches="tight",
        dpi=150,
    )
    plt.close()
    print(f"Saved SHAP summary plot to {plots_dir / 'shap_summary.png'}")

    print("\nGenerating global feature importance bar plot...")

    mean_absolute_shap = np.mean(
        np.stack([np.abs(values) for values in values_by_class], axis=0),
        axis=(0, 1),
    )

    bar_explanation = shap.Explanation(
        values=mean_absolute_shap,
        feature_names=model.feature_names,
    )

    shap.plots.bar(
        bar_explanation,
        max_display=max_display,
        show=False,
    )

    plt.savefig(
        plots_dir / "shap_bar.png",
        bbox_inches="tight",
        dpi=150,
    )
    plt.close()
    print(f"Saved SHAP bar plot to {plots_dir / 'shap_bar.png'}")

    print("\nMean absolute SHAP values across classes:")

    feature_importance = sorted(
        zip(model.feature_names, mean_absolute_shap, strict=True),
        key=lambda item: -item[1],
    )

    for rank, (feature, importance) in enumerate(
        feature_importance[:max_display],
        start=1,
    ):
        print(f"{rank:2d}. {feature:<35} {importance:.6f}")

    return values_by_class


def explain_individual_predictions(
    explainer: shap.Explainer,
    X_test: pd.DataFrame,
    model: TrainedModel,
    plots_dir: Path,
    n_examples: int = 3,
) -> None:
    if X_test.empty:
        print("No test samples available for individual explanations.")
        return

    rng = np.random.default_rng(42)
    indices = rng.choice(
        len(X_test),
        size=min(n_examples, len(X_test)),
        replace=False,
    )

    X_examples = X_test.iloc[indices]
    X_examples_scaled = scale_features(X_examples, model)

    print(f"\nCalculating SHAP values for {len(indices)} examples...")

    raw_values = explainer.shap_values(X_examples_scaled)
    values_by_class = get_class_shap_values(
        raw_values,
        n_samples=len(indices),
        n_features=len(model.feature_names),
    )

    predictions = model.model.predict(X_examples_scaled)
    class_names = get_class_names(model)

    for example_number, original_index in enumerate(indices, start=1):
        prediction = predictions[example_number - 1]

        try:
            class_index = class_names.index(prediction)
        except ValueError:
            class_index = 0

        class_index = min(class_index, len(values_by_class) - 1)
        shap_values = values_by_class[class_index][example_number - 1]
        base_value = get_expected_value(explainer, class_index)

        print(
            f"Example {example_number}: row {original_index}, "
            f"predicted class = {prediction}"
        )

        shap.force_plot(
            base_value,
            shap_values,
            X_examples_scaled[example_number - 1],
            feature_names=model.feature_names,
            matplotlib=True,
            show=False,
        )

        output_path = plots_dir / f"shap_force_example_{example_number}.png"

        plt.savefig(
            output_path,
            bbox_inches="tight",
            dpi=150,
        )
        plt.close()

        print(f"Saved individual explanation to {output_path}")


def main() -> None:
    data_dir = project_root / "experiments" / "c4" / "data"
    models_dir = project_root / "experiments" / "c4" / "models"
    plots_dir = project_root / "experiments" / "c4" / "plots"

    plots_dir.mkdir(parents=True, exist_ok=True)

    print("Loading splits...")
    train_df, val_df, test_df = load_splits(data_dir)

    print("Preparing features and labels...")
    X_train, _ = prepare_features_labels(train_df)
    X_val, _ = prepare_features_labels(val_df)
    X_test, _ = prepare_features_labels(test_df)

    print(f"Train: {X_train.shape}")
    print(f"Val:   {X_val.shape}")
    print(f"Test:  {X_test.shape}")

    model_path = models_dir / "random_forest.joblib"

    if not model_path.exists():
        print(f"Model not found: {model_path}")
        print("Run scripts/train_c4_baselines.py first.")
        return

    print("\nLoading trained Random Forest model...")
    model = TrainedModel.load(model_path)

    print(f"Loaded model: {getattr(model.model_type, 'value', model.model_type)}")
    print(f"Saved feature count: {len(model.feature_names)}")

    if list(X_test.columns) != model.feature_names:
        raise ValueError(
            "Test features do not match the trained model's feature schema."
        )

    print("\nGenerating SHAP explainer...")
    explainer = generate_shap_explainer(
        model,
        X_train,
        n_background=100,
    )

    explain_feature_importance(
        explainer,
        X_test,
        model,
        plots_dir,
        max_display=20,
    )

    explain_individual_predictions(
        explainer,
        X_test,
        model,
        plots_dir,
        n_examples=3,
    )

    print("\n" + "=" * 60)
    print("SHAP Explainability Complete!")
    print("=" * 60)
    print(f"Plots saved to: {plots_dir}")
    print("- shap_summary.png: SHAP summary for the first class")
    print("- shap_bar.png: Global mean absolute SHAP importance")
    print("- shap_force_example_*.png: Individual predicted-class explanations")


if __name__ == "__main__":
    main()