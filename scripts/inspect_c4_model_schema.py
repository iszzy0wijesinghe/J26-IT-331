from pathlib import Path

from components.c4_trust.features import FeatureExtractor
from components.c4_trust.models import TrainedModel

path = Path("experiments/c4/models/random_forest.joblib")
model = TrainedModel.load(path)

print("Artifact:", path)
print("Model type:", model.model_type)
print("Feature count:", len(model.feature_names))
print("Artifact feature order:")
for index, name in enumerate(model.feature_names, start=1):
    print(f"{index:02d}. {name}")

print("\nCurrent declared training feature order:")
for index, name in enumerate(FeatureExtractor.TRAINING_FEATURE_FIELDS, start=1):
    print(f"{index:02d}. {name}")

print(
    "\nExact schema match:", model.feature_names == list(FeatureExtractor.TRAINING_FEATURE_FIELDS)
)
