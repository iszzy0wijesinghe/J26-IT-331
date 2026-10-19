# labels.py must stay independent of the feature side, otherwise labels could
# end up depending on the same signals the model sees
import ast
from pathlib import Path

# repo root = tests/unit/<this file> -> two levels up
REPO_ROOT = Path(__file__).resolve().parents[2]
DATASETS_DIR = REPO_ROOT / "components" / "c1_credibility" / "datasets"
LABELS_FILE = DATASETS_DIR / "labels.py"

# labels.py may only use schemas from the dataset package
ALLOWED_SIBLINGS = {"schemas", "labels"}


def _imported_names(tree: ast.AST) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            names.add(base)
            # "from . import features" style
            names |= {f"{base}.{a.name}".strip(".") for a in node.names}
    return names


def test_labels_only_imports_schemas_locally():
    assert LABELS_FILE.exists(), f"labels.py not found at {LABELS_FILE}"
    tree = ast.parse(LABELS_FILE.read_text(encoding="utf-8"))

    siblings = {p.stem for p in DATASETS_DIR.glob("*.py")} - {"__init__"}
    bad = sorted(
        name for name in _imported_names(tree)
        if (set(name.split(".")) & siblings) - ALLOWED_SIBLINGS
    )
    assert not bad, f"labels.py imports other dataset modules: {bad}"