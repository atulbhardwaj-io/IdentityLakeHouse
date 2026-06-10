from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Set

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import LongType, StringType, StructField, StructType, TimestampType

from silver_framework import (
    DEFAULT_QUARANTINE_ROOT,
    DEFAULT_SCHEMA_CONFIG_ROOT,
    RECONCILIATION_LOG_PATH,
    append_reconciliation_log,
    load_schema_config,
    normalize_schema,
    validate_types,
    write_quarantine,
)


DEFAULT_TABLES = ["enrolment", "demographic", "biometric"]
SPARK_WAREHOUSE_DIR = "/app/spark-warehouse"
HIVE_METASTORE_URL = "jdbc:derby:;databaseName=/app/metastore_db;create=true"
SILVER_CONTROL_PATH = "/app/scripts/silver_layer/_control/processed_bronze_batches"
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

SILVER_CONTROL_SCHEMA = StructType(
    [
        StructField("table_name", StringType(), False),
        StructField("bronze_batch_id", StringType(), False),
        StructField("processed_ts", TimestampType(), False),
        StructField("silver_run_id", StringType(), False),
        StructField("input_rows", LongType(), False),
        StructField("output_rows", LongType(), False),
        StructField("status", StringType(), False),
    ]
)


def build_spark(app_name: str, master: str) -> SparkSession:
    return (
        SparkSession.builder.appName(app_name)
        .master(master)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.catalogImplementation", "hive")
        .config("spark.sql.warehouse.dir", SPARK_WAREHOUSE_DIR)
        .config("javax.jdo.option.ConnectionURL", HIVE_METASTORE_URL)
        .enableHiveSupport()
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
        default="append",
        help="Write mode for Silver Delta output.",
    )
    parser.add_argument(
        "--load-type",
        choices=["incremental", "full"],
        default="incremental",
        help="incremental processes only new bronze_batch_id values; full copies the selected Bronze table.",
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
    parser.add_argument(
        "--schema-config-root",
        default=DEFAULT_SCHEMA_CONFIG_ROOT,
        help="Folder containing <table_name>_schema.json Silver schema configs.",
    )
    parser.add_argument(
        "--quarantine-root",
        default=DEFAULT_QUARANTINE_ROOT,
        help="Root folder for invalid Silver quarantine Delta tables.",
    )
    parser.add_argument(
        "--reconciliation-path",
        default=RECONCILIATION_LOG_PATH,
        help="Delta path for silver_control.reconciliation_log.",
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


def delta_path_exists(path: str) -> bool:
    return (Path(path) / "_delta_log").exists()


def register_control_table(spark: SparkSession) -> None:
    spark.sql("CREATE DATABASE IF NOT EXISTS silver_control")
    spark.sql(
        "CREATE TABLE IF NOT EXISTS silver_control.processed_bronze_batches "
        f"USING DELTA LOCATION '{SILVER_CONTROL_PATH}'"
    )
    print("[REGISTERED] silver_control.processed_bronze_batches")


def ensure_control_table(spark: SparkSession) -> None:
    if not delta_path_exists(SILVER_CONTROL_PATH):
        empty_control_df = spark.createDataFrame([], SILVER_CONTROL_SCHEMA)
        empty_control_df.write.format("delta").mode("overwrite").save(SILVER_CONTROL_PATH)

    register_control_table(spark)


def get_processed_batch_ids(spark: SparkSession, table_name: str) -> Set[str]:
    ensure_control_table(spark)
    rows = (
        spark.read.format("delta")
        .load(SILVER_CONTROL_PATH)
        .filter((F.col("table_name") == table_name) & (F.col("status") == "SUCCESS"))
        .select("bronze_batch_id")
        .distinct()
        .collect()
    )
    return {row["bronze_batch_id"] for row in rows}


def filter_incremental_rows(spark: SparkSession, df, table_name: str):
    if "bronze_batch_id" not in df.columns:
        raise ValueError(
            f"Incremental Silver load requires bronze_batch_id in Bronze table: {table_name}"
        )

    processed_batch_ids = get_processed_batch_ids(spark, table_name)
    if not processed_batch_ids:
        return df

    return df.filter(~F.col("bronze_batch_id").isin(sorted(processed_batch_ids)))


def append_control_rows(spark: SparkSession, input_df, valid_df, table_name: str, run_id: str) -> None:
    ensure_control_table(spark)

    input_counts = (
        input_df.groupBy("bronze_batch_id")
        .count()
        .select(
            F.col("bronze_batch_id").cast("string").alias("bronze_batch_id"),
            F.col("count").cast("long").alias("input_rows"),
        )
    )
    output_counts = (
        valid_df.groupBy("bronze_batch_id")
        .count()
        .select(
            F.col("bronze_batch_id").cast("string").alias("bronze_batch_id"),
            F.col("count").cast("long").alias("output_rows"),
        )
    )

    control_df = (
        input_counts.join(output_counts, on="bronze_batch_id", how="left")
        .fillna({"output_rows": 0})
        .withColumn("table_name", F.lit(table_name))
        .withColumn("processed_ts", F.current_timestamp())
        .withColumn("silver_run_id", F.lit(run_id))
        .withColumn("status", F.lit("SUCCESS"))
        .select(
            "table_name",
            "bronze_batch_id",
            "processed_ts",
            "silver_run_id",
            "input_rows",
            "output_rows",
            "status",
        )
    )

    control_df.write.format("delta").mode("append").save(SILVER_CONTROL_PATH)
    print(f"[CONTROL] Recorded processed Bronze batches for {table_name}")


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

    if args.load_type == "incremental" and args.mode != "append":
        raise ValueError("Incremental Silver load requires --mode append.")

    tables = resolve_tables(args.tables, bronze_root)
    if not tables:
        raise ValueError(
            f"No tables selected. Check Bronze root and --tables. bronze_root={bronze_root}"
        )

    spark = build_spark("bronze-to-silver-delta-copy", args.master)
    try:
        if args.register:
            spark.sql("CREATE DATABASE IF NOT EXISTS silver")
            ensure_control_table(spark)

        for table in tables:
            bronze_path = bronze_root / table
            if not (bronze_path / "_delta_log").exists():
                print(f"[SKIP] Not a Delta table: {bronze_path}")
                continue

            silver_table_name = f"{table}_valid"
            silver_path = silver_root / silver_table_name

            df = spark.read.format("delta").load(str(bronze_path))
            if args.load_type == "incremental":
                df = filter_incremental_rows(spark, df, table)

            input_count = df.count()
            if input_count == 0:
                print(f"[SKIP] No new Bronze batches for {table}")
                continue

            df = df.withColumn("silver_processed_ts", F.current_timestamp()).withColumn(
                "silver_run_id", F.lit(args.run_id)
            )

            schema_config = load_schema_config(table, args.schema_config_root)
            if schema_config:
                df, schema_report = normalize_schema(df, schema_config, args.run_id)
                print(f"[SCHEMA] {table}: {json.dumps(schema_report, sort_keys=True)}")
                valid_df, invalid_df = validate_types(df, schema_config)
            else:
                print(f"[WARN] No schema config found for {table}; using legacy Silver copy behavior.")
                partition_cols = resolve_partition_cols(table, df.columns)
                valid_df = normalize_partition_cols(df, partition_cols)
                invalid_df = df.limit(0)

            valid_df = valid_df.cache()
            invalid_df = invalid_df.cache()
            valid_count = valid_df.count()
            invalid_count = invalid_df.count()

            if invalid_count > 0:
                write_quarantine(
                    spark=spark,
                    invalid_df=invalid_df,
                    table_name=table,
                    quarantine_root=args.quarantine_root,
                    run_id=args.run_id,
                )
                print(f"[QUARANTINE] {table}: invalid_rows={invalid_count}")

            reconciliation_status = append_reconciliation_log(
                spark=spark,
                run_id=args.run_id,
                dataset_name=table,
                bronze_count=input_count,
                silver_valid_count=valid_count,
                silver_quarantine_count=invalid_count,
                reconciliation_path=args.reconciliation_path,
            )
            print(
                f"[RECONCILIATION] {table}: bronze={input_count} | silver_valid={valid_count} | "
                f"quarantine={invalid_count} | status={reconciliation_status}"
            )
            if reconciliation_status != "PASS":
                raise ValueError(f"Silver reconciliation failed for {table}")

            partition_cols = resolve_partition_cols(table, valid_df.columns)
            writer = (
                valid_df.write.format("delta")
                .mode(args.mode)
                .option("mergeSchema", "true")
            )
            if args.mode == "overwrite":
                writer = writer.option("overwriteSchema", "true")

            if partition_cols:
                writer = writer.partitionBy(*partition_cols)

            writer.save(str(silver_path))
            if args.load_type == "incremental":
                append_control_rows(spark, df, valid_df, table, args.run_id)

            out_count = spark.read.format("delta").load(str(silver_path)).count()
            print(
                f"[OK] {table} -> {silver_table_name} | input_rows={input_count} | "
                f"valid_rows={valid_count} | quarantined_rows={invalid_count} | "
                f"silver_total_rows={out_count} | load_type={args.load_type} | path={silver_path}"
            )
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

            valid_df.unpersist()
            invalid_df.unpersist()
    finally:
        spark.stop()


if __name__ == "__main__":
    main()


# chnage add 
