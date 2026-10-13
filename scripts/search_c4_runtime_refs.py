import re
from pathlib import Path

roots = ["components", "shared", "tests", "scripts"]
patterns = {
    "TelemetryPacket constructors": r"TelemetryPacket\s*\(",
    "C4 integration references": (
        r"generate_baseline_packets|C4BehavioralModelRunner|FeatureExtractor"
    ),
    "Behavioral feature fields": r"battery_pct|rssi_deviation_db|packet_size_bytes|tx_interval_s",
}

excluded_dirs = {".git", ".venv", "venv", "__pycache__", ".pytest_cache"}

files = []
for root in roots:
    base = Path(root)
    if base.exists():
        files.extend(
            path
            for path in base.rglob("*.py")
            if not any(part in excluded_dirs for part in path.parts)
        )

for title, pattern in patterns.items():
    print(f"\n=== {title} ===")
    regex = re.compile(pattern)
    count = 0

    for path in sorted(set(files)):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue

        for line_number, line in enumerate(lines, start=1):
            if regex.search(line):
                print(f"{path}:{line_number}: {line.strip()}")
                count += 1

    print(f"Matches: {count}")
