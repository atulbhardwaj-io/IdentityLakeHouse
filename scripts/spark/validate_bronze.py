from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


SYNTHETIC_FOLDER = "/app/synthetic_data/synthetic"
BRONZE_BASE_PATH = "/app/scripts/bronze_layer"
SKIP_FILES = {"district_masters.csv"}
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
REQUIRED_METADATA_COLS = ["bronze_ingest_ts", "bronze_source_file", "bronze_batch_id"]


def build_spark(master: str) -> SparkSession:
    return (
        SparkSession.builder.appName("BronzeValidation")
        .master(master)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )


def discover_table_sources() -> Dict[str, str]:
    table_sources: Dict[str, str] = {}

    for file_name in sorted(os.listdir(SYNTHETIC_FOLDER)):
        if not file_name.endswith(".csv"):
            continue
        if file_name.lower() in SKIP_FILES:
            continue

        table_name = file_name.replace(".csv", "").lower()
        table_sources[table_name] = f"{SYNTHETIC_FOLDER}/{file_name}"

    table_sources["demographic"] = DEMOGRAPHIC_CSV
    table_sources["enrolment"] = ENROLMENT_CSV
    table_sources["biometric"] = BIOMETRIC_CSV

    return table_sources


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Bronze Delta tables against source CSV files.")
    parser.add_argument(
        "--master",
        default="spark://spark-master:7077",
        help="Spark master URL.",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["all"],
        help="Table names to validate, or 'all'.",
    )
    return parser.parse_args()


def resolve_tables(requested_tables: List[str], available_tables: List[str]) -> List[str]:
    if "all" in requested_tables:
        return sorted(available_tables)

    unknown_tables = sorted(set(requested_tables) - set(available_tables))
    if unknown_tables:
        raise ValueError(f"Unknown table(s): {', '.join(unknown_tables)}")

    return requested_tables


def validate_table(spark: SparkSession, table_name: str, source_path: str) -> bool:
    bronze_path = f"{BRONZE_BASE_PATH}/{table_name}"
    print(f"\n=== VALIDATING {table_name} ===")
    print(f"Source: {source_path}")
    print(f"Bronze: {bronze_path}")

    source_df = (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(source_path)
    )
    bronze_df = spark.read.format("delta").load(bronze_path)

    source_count = source_df.count()
    bronze_count = bronze_df.count()
    print(f"source_count={source_count}")
    print(f"bronze_count={bronze_count}")

    schema_ok = bronze_count > 0
    row_count_ok = source_count == bronze_count
    metadata_cols_present = all(col_name in bronze_df.columns for col_name in REQUIRED_METADATA_COLS)

    print("Schema:")
    bronze_df.printSchema()

    metadata_ok = False
    if metadata_cols_present:
        metadata_nulls = bronze_df.select(
            *[
                F.sum(F.when(F.col(col_name).isNull(), 1).otherwise(0)).alias(col_name)
                for col_name in REQUIRED_METADATA_COLS
            ]
        ).collect()[0].asDict()
        metadata_ok = all(value == 0 for value in metadata_nulls.values())
        print(f"metadata_nulls={metadata_nulls}")
    else:
        print(f"missing_metadata_cols={sorted(set(REQUIRED_METADATA_COLS) - set(bronze_df.columns))}")

    detail = (
        spark.sql(f"DESCRIBE DETAIL delta.`{bronze_path}`")
        .select("partitionColumns", "numFiles", "sizeInBytes")
        .collect()[0]
        .asDict()
    )
    print(f"delta_detail={detail}")

    table_ok = row_count_ok and schema_ok and metadata_cols_present and metadata_ok
    print(f"status={'PASS' if table_ok else 'FAIL'}")

    if not row_count_ok:
        print("[FAIL] Row count mismatch between source and Bronze.")
    if not metadata_cols_present:
        print("[FAIL] Required Bronze metadata columns are missing.")
    if metadata_cols_present and not metadata_ok:
        print("[FAIL] Required Bronze metadata columns contain null values.")

    return table_ok


def main() -> None:
    args = parse_args()
    table_sources = discover_table_sources()
    selected_tables = resolve_tables(args.tables, list(table_sources.keys()))
    spark = build_spark(args.master)

    try:
        results = []
        for table_name in selected_tables:
            results.append(validate_table(spark, table_name, table_sources[table_name]))
    finally:
        spark.stop()

    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
