from __future__ import annotations

import argparse
from pathlib import Path

from pyspark.sql import SparkSession


def build_spark(app_name: str, master: str) -> SparkSession:
    return (
        SparkSession.builder.appName(app_name)
        .master(master)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy Silver *_valid Delta tables to *_valid_test tables."
    )
    parser.add_argument(
        "--master",
        default="spark://spark-master:7077",
        help="Spark master URL.",
    )
    parser.add_argument(
        "--silver-root",
        default="/app/scripts/silver_layer",
        help="Silver Delta root folder.",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["all"],
        help="Silver source table names without suffix (example: enrolment demographic) or 'all'.",
    )
    parser.add_argument(
        "--mode",
        choices=["overwrite", "append"],
        default="overwrite",
        help="Write mode for *_valid_test tables.",
    )
    return parser.parse_args()


def discover_valid_tables(silver_root: Path) -> list[str]:
    names: list[str] = []
    if not silver_root.exists():
        return names
    for child in silver_root.iterdir():
        if not child.is_dir():
            continue
        if not child.name.endswith("_valid"):
            continue
        if not (child / "_delta_log").exists():
            continue
        base = child.name[: -len("_valid")]
        names.append(base)
    return sorted(names)


def resolve_tables(requested: list[str], silver_root: Path) -> list[str]:
    if "all" in requested:
        return discover_valid_tables(silver_root)
    return requested


def main() -> None:
    args = parse_args()
    silver_root = Path(args.silver_root)
    tables = resolve_tables(args.tables, silver_root)
    if not tables:
        raise ValueError(
            f"No Silver tables selected. Check --silver-root and --tables. silver_root={silver_root}"
        )

    spark = build_spark("silver-to-test-copy", args.master)
    try:
        for table in tables:
            src = silver_root / f"{table}_valid"
            dst = silver_root / f"{table}_valid_test"

            if not (src / "_delta_log").exists():
                print(f"[SKIP] Source not found or not Delta: {src}")
                continue

            df = spark.read.format("delta").load(str(src))
            (
                df.write.format("delta")
                .mode(args.mode)
                .option("overwriteSchema", "true")
                .save(str(dst))
            )

            out_count = spark.read.format("delta").load(str(dst)).count()
            print(f"[OK] {src.name} -> {dst.name} | rows={out_count}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
