from __future__ import annotations

import argparse
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


DEFAULT_TABLES = ["enrolment", "demographic", "biometric"]
PARTITION_COLS_BY_TABLE = {
    "aadhaar_voter_link_raw": ["partition_year", "partition_month"],
    "biometric": ["partition_year", "partition_month"],
    "demographic": ["partition_year", "partition_month"],
    "district_scheme_payment_raw": ["partition_year", "partition_month"],
    "enrolment": ["partition_year", "partition_month"],
    "population_raw": ["partition_year", "partition_month"],
    "scheme_beneficiary_raw": ["partition_year", "partition_month"],
    "scheme_master_raw": ["active_flag"],
    "voter_registry_raw": ["partition_year", "partition_month"],
}


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


def resolve_partition_cols(table_name: str, columns: list[str]) -> list[str]:
    requested_partition_cols = PARTITION_COLS_BY_TABLE.get(table_name, [])
    return [col_name for col_name in requested_partition_cols if col_name in columns]


def normalize_partition_cols(df, partition_cols: list[str]):
    normalized_df = df

    if "partition_year" in partition_cols or "partition_month" in partition_cols:
        if "date" in normalized_df.columns:
            normalized_df = normalized_df.withColumn(
                "date",
                F.coalesce(
                    F.to_date(F.col("date"), "dd-MM-yyyy"),
                    F.to_date(F.col("date"), "yyyy-MM-dd"),
                    F.col("date").cast("date"),
                ),
            )

            if "partition_year" in partition_cols:
                normalized_df = normalized_df.withColumn("partition_year", F.year(F.col("date")))

            if "partition_month" in partition_cols:
                normalized_df = normalized_df.withColumn("partition_month", F.month(F.col("date")))

    for col_name in partition_cols:
        if col_name not in normalized_df.columns:
            continue

        if col_name.endswith("date") or col_name == "date":
            normalized_df = normalized_df.withColumn(
                col_name,
                F.coalesce(
                    F.to_date(F.col(col_name), "dd-MM-yyyy"),
                    F.to_date(F.col(col_name), "yyyy-MM-dd"),
                    F.col(col_name).cast("date"),
                ),
            )

    return normalized_df


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

            partition_cols = resolve_partition_cols(table, df.columns)
            df = normalize_partition_cols(df, partition_cols)
            writer = (
                df.write.format("delta")
                .mode(args.mode)
                .option("overwriteSchema", "true")
            )

            if partition_cols:
                writer = writer.partitionBy(*partition_cols)

            writer.save(str(silver_path))

            out_count = spark.read.format("delta").load(str(silver_path)).count()
            print(f"[OK] {table} -> {silver_table_name} | rows={out_count} | path={silver_path}")
            if partition_cols:
                print(f"[PARTITIONED BY] {silver_table_name}: {partition_cols}")
            else:
                print(f"[PARTITIONED BY] {silver_table_name}: none")

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
