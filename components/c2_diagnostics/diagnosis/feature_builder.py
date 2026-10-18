"""Dataset loading, validation, and feature preparation for C2."""

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "c2_diagnostics"
    / "landslide_silence_dataset_20000.csv"
)

TARGET_COLUMN = "Label"

EXPECTED_LABELS = {
    "normal",
    "communication_failure",
    "hardware_failure",
    "possible_zone_damage",
}

EXCLUDED_COLUMNS = {
    "Event_ID",
    "Timestamp",
}


def load_dataset(
    dataset_path: str | Path = DEFAULT_DATASET_PATH,
) -> pd.DataFrame:
    """Load the dataset and validate its target labels."""
    path = Path(dataset_path)

    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError("The dataset is empty.")

    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Missing target column: {TARGET_COLUMN}")

    if df[TARGET_COLUMN].isna().any():
        raise ValueError("The target column contains missing values.")

    actual_labels = set(df[TARGET_COLUMN].unique())

    if actual_labels != EXPECTED_LABELS:
        raise ValueError(
            f"Unexpected target labels. Found: {sorted(actual_labels)}"
        )

    return df


def build_features(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Separate numeric input features from the target."""
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Missing target column: {TARGET_COLUMN}")

    if df[TARGET_COLUMN].isna().any():
        raise ValueError("The target column contains missing values.")

    excluded = EXCLUDED_COLUMNS | {TARGET_COLUMN}

    X = df.drop(
        columns=[column for column in excluded if column in df.columns]
    ).copy()

    y = df[TARGET_COLUMN].copy()

    non_numeric = X.select_dtypes(exclude="number").columns.tolist()

    if non_numeric:
        raise ValueError(
            f"Non-numeric features require preprocessing: {non_numeric}"
        )

    if X.empty:
        raise ValueError("No features remain after excluding metadata.")

    if X.isin([float("inf"), float("-inf")]).any().any():
        raise ValueError("Features contain infinite values.")

    return X, y


def split_dataset(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Create stratified training and testing sets."""
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1.")

    if len(X) != len(y):
        raise ValueError("Features and target have different row counts.")

    return train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )