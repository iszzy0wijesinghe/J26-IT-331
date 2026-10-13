from pathlib import Path

sections = {
    "shared/contracts/telemetry.py": [(1, 150)],
    "shared/simulation/generator.py": [(1, 150)],
    "components/c4_trust/features.py": [(1, 180), (180, 390), (390, 490)],
    "components/c4_trust/models.py": [(1, 260)],
    "components/c4_trust/pipeline.py": [(1, 180)],
}

for filename, ranges in sections.items():
    path = Path(filename)
    print(f"\n{'=' * 24} {filename} {'=' * 24}")

    if not path.exists():
        print("FILE NOT FOUND")
        continue

    lines = path.read_text(encoding="utf-8").splitlines()

    for start, end in ranges:
        print(f"\n--- Lines {start}-{min(end, len(lines))} ---")
        for number in range(start, min(end, len(lines)) + 1):
            print(f"{number:4}: {lines[number - 1]}")
