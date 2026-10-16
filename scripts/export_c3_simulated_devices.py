"""Export hardware-aligned SIMULATED GeoNex device packets without overwriting.

Usage:
  python -m scripts.export_c3_simulated_devices \
    --scenario rapid_wetting_tilt --output-dir data/synthetic/c3_v1_demo_01
"""

import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

from components.c3_forecasting.simulated_devices import (
    DEVICE_IDS,
    GATEWAY_ID,
    DemoNetworkConfig,
    generate_one_zone_demo,
)


def export_demo(output_dir: Path, *, scenario: str, seed: int) -> dict[str, object]:
    """Export one reproducible scenario. Existing output is never modified."""
    if output_dir.exists():
        raise FileExistsError(f"Output already exists; choose a new directory: {output_dir}")

    config = DemoNetworkConfig(seed=seed, scenario=scenario)
    records = generate_one_zone_demo(config)
    output_dir.mkdir(parents=True, exist_ok=False)

    packet_path = output_dir / "telemetry.jsonl"
    with packet_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in records:
            handle.write(json.dumps({
                "packet": row.packet.model_dump(mode="json"),
                "operating_mode": row.operating_mode.value,
                "delta_t_seconds": row.delta_t_seconds,
            }, sort_keys=True, allow_nan=False) + "\n")

    manifest = {
        "schema_version": "c3-hardware-aligned-simulation-v1",
        "source_origin": "SIMULATED",
        "real_hardware_captured": False,
        "validated_landslide_labels": False,
        "scenario": scenario,
        "seed": seed,
        "zone_id": config.zone_id,
        "devices": list(DEVICE_IDS),
        "gateway_id": GATEWAY_ID,
        "packet_count": len(records),
        "packet_counts_by_device": dict(sorted(Counter(
            record.packet.device_id for record in records
        ).items())),
        "telemetry_file": packet_path.name,
        "telemetry_sha256": sha256(packet_path.read_bytes()).hexdigest(),
        "notes": [
            "Engineering simulation of proposed prototype channels; not physical firmware data",
            "All sensor values are synthetic; raw rain mechanism and FSR signals are uncalibrated",
            "Operating modes follow a predefined schedule, independent of predicted risk",
            "Scenario identity is provenance only and must never be fed to the C3 model",
            "No landslide event or risk probability ground truth is asserted",
        ],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("stable", "gradual_wetting", "rapid_wetting_tilt"),
                        default="gradual_wetting")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = export_demo(args.output_dir, scenario=args.scenario, seed=args.seed)
    print(f"SIMULATED GeoNex demo exported: {args.output_dir}")
    print(f"Scenario: {manifest['scenario']} | Packets: {manifest['packet_count']}")
    print("No real sensor readings or verified landslide labels are included.")


if __name__ == "__main__":
    main()
