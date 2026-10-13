"""SHAP explainability for C4 behavioral models.

This script generates SHAP (SHapley Additive exPlanations) values
to understand feature importance and individual predictions.
"""

import sys
from pathlib import Path

import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("SHAP is not installed. Install it with: pip install shap")
    sys.exit(1)

from components.c4_trust.data_split import ScenarioAwareSplitter  # noqa: E402
from components.c4_trust.features import FeatureExtractor  # noqa: E402
from components.c4_trust.models import TrainedModel  # noqa: E402


def load_splits(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load train/val/test splits.

    Args:
        data_dir: Directory containing split files

    Returns:
        Tuple of (train, val, test) dataframes
    """
    train_df = pd.read_csv(data_dir / "C4_train.csv")
    val_df = pd.read_csv(data_dir / "C4_val.csv")
    test_df = pd.read_csv(data_dir / "C4_test.csv")

    ScenarioAwareSplitter.validate_splits(
        {"train": train_df, "val": val_df, "test": test_df}
    )
    return train_df, val_df, test_df


def prepare_features_labels(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Separate features and labels.

    Args:
        df: Input dataframe

    Returns:
        Tuple of (features, labels)
    """
    return FeatureExtractor().extract_for_training(df)


def generate_shap_explainer(
    model: TrainedModel,
    X_background: pd.DataFrame,
    n_background: int = 100,
) -> shap.Explainer:
    """Generate SHAP explainer for the model.

    Args:
        model: Trained model
        X_background: Background dataset for SHAP
        n_background: Number of background samples to use

    Returns:
        SHAP explainer
    """
    # Scale if needed
    if model.scaler is not None:
        X_background_scaled = model.scaler.transform(X_background)
    else:
        X_background_scaled = X_background.values

    # Sample background for efficiency
    if len(X_background) > n_background:
        import numpy as np

        indices = np.random.choice(len(X_background), n_background, replace=False)
        X_background_scaled = X_background_scaled[indices]

    # Create explainer based on model type
    if hasattr(model.model, "predict_proba"):
        # Tree-based model
        explainer = shap.TreeExplainer(model.model, X_background_scaled)
    else:
        # Kernel explainer for other models
        explainer = shap.KernelExplainer(
            model.model.predict_proba, X_background_scaled
        )

    return explainer


def explain_feature_importance(
    explainer: shap.Explainer,
    X_test: pd.DataFrame,
    model: TrainedModel,
    max_display: int = 20,
) -> None:
    """Explain and display feature importance.

    Args:
        explainer: SHAP explainer
        X_test: Test features
        model: Trained model
        max_display: Maximum number of features to display
    """
    # Scale if needed
    if model.scaler is not None:
        X_test_scaled = model.scaler.transform(X_test)
    else:
        X_test_scaled = X_test.values

    # Calculate SHAP values
    print("Calculating SHAP values...")
    shap_values = explainer.shap_values(X_test_scaled)

    # Handle multi-class output
    if isinstance(shap_values, list):
        # Multi-class: use the first class or mean across classes
        shap_values_mean = shap_values[0]  # Use first class for simplicity
    else:
        shap_values_mean = shap_values

    # Summary plot
    print("\nGenerating SHAP summary plot...")
    shap.summary_plot(
        shap_values_mean,
        X_test_scaled,
        feature_names=model.feature_names,
        max_display=max_display,
        show=False,
    )

    # Save plot
    import matplotlib.pyplot as plt

    plt.savefig("experiments/c4/plots/shap_summary.png", bbox_inches="tight", dpi=150)
    print("Saved SHAP summary plot to experiments/c4/plots/shap_summary.png")

    # Feature importance bar plot
    print("\nGenerating feature importance bar plot...")
    shap.plots.bar(shap_values_mean, show=False)
    plt.savefig(
        "experiments/c4/plots/shap_bar.png", bbox_inches="tight", dpi=150
    )
    print("Saved SHAP bar plot to experiments/c4/plots/shap_bar.png")

    # Print mean absolute SHAP values
    print("\nMean Absolute SHAP Values (Feature Importance):")
    mean_shap = abs(shap_values_mean).mean(axis=0)
    feature_importance = dict(zip(model.feature_names, mean_shap, strict=True))
    sorted_importance = sorted(feature_importance.items(), key=lambda x: -x[1])

    for i, (feat, imp) in enumerate(sorted_importance[:max_display]):
        print(f"  {i+1:2d}. {feat:<40} {imp:.4f}")


def explain_individual_predictions(
    explainer: shap.Explainer,
    X_test: pd.DataFrame,
    model: TrainedModel,
    n_examples: int = 5,
) -> None:
    """Explain individual predictions.

    Args:
        explainer: SHAP explainer
        X_test: Test features
        model: Trained model
        n_examples: Number of examples to explain
    """
    # Scale if needed
    if model.scaler is not None:
        X_test_scaled = model.scaler.transform(X_test)
    else:
        X_test_scaled = X_test.values

    # Calculate SHAP values
    shap_values = explainer.shap_values(X_test_scaled)

    # Handle multi-class output
    if isinstance(shap_values, list):
        shap_values_mean = shap_values[0]
    else:
        shap_values_mean = shap_values

    # Sample examples
    import numpy as np

    indices = np.random.choice(len(X_test), min(n_examples, len(X_test)), replace=False)

    print(f"\nExplaining {len(indices)} individual predictions...")

    for i, idx in enumerate(indices):
        print(f"\nExample {i+1} (Index {idx}):")

        # Generate force plot
        expected_value = (
            explainer.expected_value[0]
            if isinstance(explainer.expected_value, list)
            else explainer.expected_value
        )
        shap.force_plot(
            expected_value,
            shap_values_mean[idx],
            X_test_scaled[idx],
            feature_names=model.feature_names,
            matplotlib=True,
            show=False,
        )

        import matplotlib.pyplot as plt

        plt.savefig(
            f"experiments/c4/plots/shap_force_example_{i+1}.png",
            bbox_inches="tight",
            dpi=150,
        )
        print(f"  Saved force plot to experiments/c4/plots/shap_force_example_{i+1}.png")


def main() -> None:
    # Paths
    data_dir = Path(r"C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331\experiments\c4\data")
    models_dir = Path(r"C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331\experiments\c4\models")
    plots_dir = Path(r"C:\Users\User\Desktop\FInal_GeoNex_Repo\J26-IT-331\experiments\c4\plots")
    plots_dir.mkdir(parents=True, exist_ok=True)

    # Load splits
    print("Loading splits...")
    train_df, val_df, test_df = load_splits(data_dir)

    # Prepare features and labels
    print("Preparing features and labels...")
    X_train, y_train = prepare_features_labels(train_df)
    X_val, y_val = prepare_features_labels(val_df)
    X_test, y_test = prepare_features_labels(test_df)

    print(f"Train: {X_train.shape}")
    print(f"Val: {X_val.shape}")
    print(f"Test: {X_test.shape}")

    # Load trained model
    print("\nLoading trained Random Forest model...")
    model_path = models_dir / "random_forest.joblib"
    if not model_path.exists():
        print(f"Model not found at {model_path}")
        print("Please train the model first using scripts/train_c4_baselines.py")
        return

    model = TrainedModel.load(model_path)
    print(f"Loaded model: {model.model_type.value}")
    print(f"Features: {len(model.feature_names)}")

    # Generate SHAP explainer
    print("\nGenerating SHAP explainer...")
    explainer = generate_shap_explainer(model, X_train, n_background=100)

    # Explain feature importance
    explain_feature_importance(explainer, X_test, model, max_display=20)

    # Explain individual predictions
    explain_individual_predictions(explainer, X_test, model, n_examples=3)

    print("\n" + "=" * 60)
    print("SHAP Explainability Complete!")
    print("=" * 60)
    print("\nPlots saved to experiments/c4/plots/")
    print("- shap_summary.png: Overall feature importance")
    print("- shap_bar.png: Feature importance bar chart")
    print("- shap_force_example_*.png: Individual prediction explanations")


if __name__ == "__main__":
    main()
