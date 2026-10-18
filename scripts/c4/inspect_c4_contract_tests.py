from pathlib import Path

sections = {
    "shared/contracts/telemetry.py": [(1, 115)],
    "tests/unit/test_simulation_generator.py": [(1, 180)],
    "tests/contract/test_shared_baseline.py": [(1, 150)],
    "shared/contracts/common.py": [(1, 180)],
}

for filename, ranges in sections.items():
    path = Path(filename)
    print(f"\n{'=' * 20} {filename} {'=' * 20}")

    if not path.exists():
        print("FILE NOT FOUND")
        continue

    lines = path.read_text(encoding="utf-8").splitlines()

    for start, end in ranges:
        print(f"\n--- Lines {start}-{min(end, len(lines))} ---")
        for number in range(start, min(end, len(lines)) + 1):
            print(f"{number:4}: {lines[number - 1]}")
