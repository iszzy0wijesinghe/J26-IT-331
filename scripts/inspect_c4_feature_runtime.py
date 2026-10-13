from pathlib import Path

sections = {
    "components/c4_trust/features.py": [(1, 300)],
    "components/c4_trust/models.py": [(1, 300)],
    "components/c4_trust/service.py": [(1, 300)],
    "components/c4_trust/trust_service.py": [(1, 300)],
}

for filename, ranges in sections.items():
    path = Path(filename)
    if not path.exists():
        continue

    lines = path.read_text(encoding="utf-8").splitlines()
    print(f"\n{'=' * 18} {filename} {'=' * 18}")

    for start, end in ranges:
        print(f"\n--- Lines {start}-{min(end, len(lines))} ---")
        for number in range(start, min(end, len(lines)) + 1):
            print(f"{number:4}: {lines[number - 1]}")
