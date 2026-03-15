from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = Path(
    "data/api_data_aadhar_biometric/api_data_aadhar_biometric/api_data_aadhar_biometric_combined.csv"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add audit metadata columns to the biometric combined CSV."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to the biometric CSV file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output path. If omitted, the input file is overwritten.",
    )
    parser.add_argument(
        "--source-system",
        default="government_website",
        help="Source system label to stamp into the file.",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Optional batch id. If omitted, a UTC timestamp-based batch id is generated.",
    )
    return parser.parse_args()


def build_batch_id(batch_id: str | None) -> str:
    if batch_id:
        return batch_id
    return datetime.now(timezone.utc).strftime("biometric_%Y%m%dT%H%M%SZ")


def main() -> None:
    args = parse_args()
    input_path = args.input
    output_path = args.output or input_path

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    ingest_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    batch_id = build_batch_id(args.batch_id)

    df = pd.read_csv(input_path)
    df["source_system"] = args.source_system
    df["ingest_ts"] = ingest_ts
    df["batch_id"] = batch_id

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"Input rows: {len(df)}")
    print(f"Output file: {output_path}")
    print("Added columns: source_system, ingest_ts, batch_id")
    print(f"source_system={args.source_system}")
    print(f"ingest_ts={ingest_ts}")
    print(f"batch_id={batch_id}")


if __name__ == "__main__":
    main()
