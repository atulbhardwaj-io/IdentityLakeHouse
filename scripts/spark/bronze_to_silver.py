from __future__ import annotations

import argparse
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


DEFAULT_TABLES = ["enrolment", "demographic", "biometric"]


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
        description="Copy Bronze Delta tables into Silver Delta tables."
    )
    parser.add_argument(
        "--master",
        default="spark://spark-master:7077",
        help="Spark master URL.",
    )
    parser.add_argument(
        "--bronze-root",
        default="/app/scripts/bronze_layer",
        help="Bronze Delta root folder.",
    )
    parser.add_argument(
        "--silver-root",
        default="/app/scripts/silver_layer",
        help="Silver Delta root folder.",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        default=DEFAULT_TABLES,
        help="Bronze table names to copy, or 'all'.",
    )
    parser.add_argument(
        "--mode",
        choices=["overwrite", "append"],
        default="overwrite",
        help="Write mode for Silver Delta output.",
    )
    parser.add_argument(
        "--register",
        action="store_true",
        help="Register output tables in Spark catalog as silver.<table>_valid.",
    )
    parser.add_argument(
        "--run-id",
        default="manual_run",
        help="Pipeline run id to stamp into Silver data.",
    )
    return parser.parse_args()


def list_delta_dirs(path: Path) -> list[str]:
    if not path.exists():
        return []
    names: list[str] = []
    for child in path.iterdir():
        if child.is_dir() and (child / "_delta_log").exists():
            names.append(child.name)
    return sorted(names)


def resolve_tables(requested: list[str], bronze_root: Path) -> list[str]:
    if "all" in requested:
        return list_delta_dirs(bronze_root)
    return requested


def main() -> None:
    args = parse_args()
    bronze_root = Path(args.bronze_root)
    silver_root = Path(args.silver_root)

    tables = resolve_tables(args.tables, bronze_root)
    if not tables:
        raise ValueError(
            f"No tables selected. Check Bronze root and --tables. bronze_root={bronze_root}"
        )

    spark = build_spark("bronze-to-silver-delta-copy", args.master)
    try:
        if args.register:
            spark.sql("CREATE DATABASE IF NOT EXISTS silver")

        for table in tables:
            bronze_path = bronze_root / table
            if not (bronze_path / "_delta_log").exists():
                print(f"[SKIP] Not a Delta table: {bronze_path}")
                continue

            silver_table_name = f"{table}_valid"
            silver_path = silver_root / silver_table_name

            df = (
                spark.read.format("delta").load(str(bronze_path))
                .withColumn("silver_processed_ts", F.current_timestamp())
                .withColumn("silver_run_id", F.lit(args.run_id))
            )

            (
                df.write.format("delta")
                .mode(args.mode)
                .save(str(silver_path))
            )

            out_count = spark.read.format("delta").load(str(silver_path)).count()
            print(f"[OK] {table} -> {silver_table_name} | rows={out_count} | path={silver_path}")

            if args.register:
                spark.sql(
                    f"CREATE TABLE IF NOT EXISTS silver.{silver_table_name} "
                    f"USING DELTA LOCATION '{str(silver_path).replace(chr(92), '/')}'"
                )
                print(f"[REGISTERED] silver.{silver_table_name}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
