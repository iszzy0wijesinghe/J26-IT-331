from pathlib import Path

targets = {
    "components/c4_trust/features.py": (249, 430),
    "scripts/prepare_c4_behavioral_dataset.py": (1, 220),
}

for filename, (start, end) in targets.items():
    path = Path(filename)
    if not path.exists():
        print(f"\nNOT FOUND: {filename}")
        continue

    lines = path.read_text(encoding="utf-8").splitlines()
    print(f"\n{'=' * 16} {filename} {'=' * 16}")

    for number in range(start, min(end, len(lines)) + 1):
        print(f"{number:4}: {lines[number - 1]}")
