import argparse
import os
import sys
from typing import List, Tuple

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


SYNTHETIC_FOLDER = "/app/synthetic_data/synthetic"
BRONZE_BASE_PATH = "/app/scripts/bronze_layer"
SKIP_FILES = {"district_masters.csv"}
SPARK_WAREHOUSE_DIR = "/app/spark-warehouse"
HIVE_METASTORE_URL = "jdbc:derby:;databaseName=/app/metastore_db;create=true"

DEMOGRAPHIC_CSV = (
    "/app/data/api_data_aadhar_demographic/api_data_aadhar_demographic/"
    "api_data_aadhar_demographic_combined.csv"
)
ENROLMENT_CSV = (
    "/app/data/api_data_aadhar_enrolment/api_data_aadhar_enrolment/"
    "api_data_aadhar_enrolment_combined.csv"
)
BIOMETRIC_CSV = (
    "/app/data/api_data_aadhar_biometric/api_data_aadhar_biometric/"
    "api_data_aadhar_biometric_combined.csv"
)

PARTITION_COLS_BY_TABLE = {
    "aadhaar_voter_link_raw": ["date"],
    "biometric": ["date"],
    "demographic": ["date"],
    "district_scheme_payment_raw": ["date"],
    "enrolment": ["date"],
    "population_raw": ["date"],
    "scheme_beneficiary_raw": ["date"],
    "scheme_master_raw": ["active_flag"],
    "voter_registry_raw": ["date"],
}


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("IdentityLakehouse")
        .master("spark://spark-master:7077")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.warehouse.dir", SPARK_WAREHOUSE_DIR)
        .config("javax.jdo.option.ConnectionURL", HIVE_METASTORE_URL)
        .enableHiveSupport()
        .getOrCreate()
    )


def load_csv(spark: SparkSession, file_path: str):
    return (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(file_path)
    )


def apply_bronze_metadata(df, run_id: str):
    return (
        df.withColumn("bronze_ingest_ts", F.current_timestamp())
        .withColumn("bronze_source_file", F.input_file_name())
        .withColumn("bronze_batch_id", F.lit(run_id))
    )


def normalize_partition_cols(df, partition_cols: List[str]) -> Tuple[object, List[str]]:
    normalized_df = df
    usable_partition_cols: List[str] = []

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

        usable_partition_cols.append(col_name)

    return normalized_df, usable_partition_cols


def write_delta(df, table_name: str, mode: str) -> None:
    output_path = f"{BRONZE_BASE_PATH}/{table_name}"
    requested_partition_cols = PARTITION_COLS_BY_TABLE.get(table_name, [])
    df, partition_cols = normalize_partition_cols(df, requested_partition_cols)

    writer = df.write.format("delta").mode(mode)

    if mode == "overwrite":
        writer = writer.option("overwriteSchema", "true")

    if partition_cols:
        writer = writer.partitionBy(*partition_cols)

    writer.save(output_path)

    row_count = df.count()
    print(f"[OK] {table_name} Delta table created | rows={row_count} | mode={mode} | path={output_path}")
    if partition_cols:
        print(f"[PARTITIONED BY] {table_name}: {partition_cols}")
    else:
        print(f"[PARTITIONED BY] {table_name}: none")
    print(f"[SCHEMA] {table_name}: {df.columns}")


def register_bronze_table(spark: SparkSession, table_name: str) -> None:
    output_path = f"{BRONZE_BASE_PATH}/{table_name}"
    spark.sql("CREATE DATABASE IF NOT EXISTS bronze")
    spark.sql(
        f"CREATE TABLE IF NOT EXISTS bronze.{table_name} "
        f"USING DELTA LOCATION '{output_path}'"
    )
    print(f"[REGISTERED] bronze.{table_name}")


def discover_table_sources() -> dict:
    table_sources = {}

    for file_name in sorted(os.listdir(SYNTHETIC_FOLDER)):
        if not file_name.endswith(".csv"):
            continue
        if file_name.lower() in SKIP_FILES:
            continue

        table_name = file_name.replace(".csv", "").lower()
        file_path = f"{SYNTHETIC_FOLDER}/{file_name}"
        table_sources[table_name] = file_path

    table_sources["demographic"] = DEMOGRAPHIC_CSV
    table_sources["enrolment"] = ENROLMENT_CSV
    table_sources["biometric"] = BIOMETRIC_CSV

    return table_sources


def parse_args():
    parser = argparse.ArgumentParser(description="Build Bronze Delta tables from raw CSV files.")
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["all"],
        help="Table names to process, or 'all'.",
    )
    parser.add_argument(
        "--mode",
        choices=["overwrite", "append"],
        default="overwrite",
        help="Write mode for Bronze Delta tables.",
    )
    parser.add_argument(
        "--run-id",
        default="manual_run",
        help="Logical run id for logging and replay tracking.",
    )
    parser.add_argument(
        "--allow-append-all",
        action="store_true",
        help="Allow append mode with --tables all. Use carefully to avoid replaying the same snapshot twice.",
    )
    return parser.parse_args()


def resolve_tables(requested_tables: List[str], available_tables: List[str]) -> List[str]:
    if "all" in requested_tables:
        return sorted(available_tables)

    unknown_tables = sorted(set(requested_tables) - set(available_tables))
    if unknown_tables:
        raise ValueError(f"Unknown table(s): {', '.join(unknown_tables)}")

    return requested_tables


def main() -> None:
    args = parse_args()
    table_sources = discover_table_sources()
    selected_tables = resolve_tables(args.tables, list(table_sources.keys()))

    if args.mode == "append" and "all" in args.tables and not args.allow_append_all:
        raise ValueError(
            "Append mode with --tables all is blocked by default. "
            "Use explicit table names for controlled replay, or pass --allow-append-all if you really intend a full append."
        )

    spark = build_spark()
    print("Spark Session Created")
    print(f"[RUN_ID] {args.run_id}")
    print(f"[MODE] {args.mode}")
    print(f"[TABLES] {', '.join(selected_tables)}")

    try:
        for table_name in selected_tables:
            print(f"Processing {table_name}...")
            df = load_csv(spark, table_sources[table_name])
            df = apply_bronze_metadata(df, args.run_id)
            write_delta(df, table_name, args.mode)
            register_bronze_table(spark, table_name)
    finally:
        spark.stop()
        print("ALL DELTA TABLES CREATED SUCCESSFULLY")

if __name__ == "__main__":
    main()
