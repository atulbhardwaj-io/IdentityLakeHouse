from __future__ import annotations

import argparse
import re
from typing import Iterable

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


SPARK_WAREHOUSE_DIR = "/app/spark-warehouse"
HIVE_METASTORE_URL = "jdbc:derby:;databaseName=/app/metastore_db;create=true"

DEFAULT_SOURCE_TABLE = "silver_copy.biometric_valid_test"
DEFAULT_OUTPUT_TABLE = "silver_copy.biometric_standard_schema_test"

EXPECTED_COLUMNS = [
    "date",
    "state",
    "district",
    "pincode",
    "bio_age_5_17",
    "bio_age_17_plus",
    "source_system",
    "ingest_ts",
    "batch_id",
    "bronze_ingest_ts",
    "bronze_source_file",
    "bronze_batch_id",
    "partition_year",
    "partition_month",
    "silver_processed_ts",
    "silver_run_id",
]

EXPECTED_TYPES = {
    "date": "date",
    "state": "string",
    "district": "string",
    "pincode": "int",
    "bio_age_5_17": "int",
    "bio_age_17_plus": "int",
    "source_system": "string",
    "ingest_ts": "timestamp",
    "batch_id": "string",
    "bronze_ingest_ts": "timestamp",
    "bronze_source_file": "string",
    "bronze_batch_id": "string",
    "partition_year": "int",
    "partition_month": "int",
    "silver_processed_ts": "timestamp",
    "silver_run_id": "string",
}

COLUMN_ALIASES = {
    "date": ["date", "dt", "record_date"],
    "state": ["state", "state_name"],
    "district": ["district", "district_name"],
    "pincode": ["pincode", "pin_code", "pin", "postal_code"],
    "bio_age_5_17": ["bio_age_5_17", "biometric_age_5_17", "bio_5_17"],
    "bio_age_17_plus": [
        "bio_age_17_plus",
        "bio_age_17_",
        "bio_age_17",
        "bio_age_17+",
        "bio_age_18_plus",
        "biometric_age_17_plus",
        "biometric_age_17+",
    ],
    "source_system": ["source_system", "source"],
    "ingest_ts": ["ingest_ts", "ingestion_ts", "ingested_at"],
    "batch_id": ["batch_id", "batch"],
    "bronze_ingest_ts": ["bronze_ingest_ts"],
    "bronze_source_file": ["bronze_source_file", "source_file"],
    "bronze_batch_id": ["bronze_batch_id"],
    "partition_year": ["partition_year"],
    "partition_month": ["partition_month"],
    "silver_processed_ts": ["silver_processed_ts"],
    "silver_run_id": ["silver_run_id"],
}


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
        description="Standardize messy biometric schema into the expected Silver schema."
    )
    parser.add_argument(
        "--master",
        default="spark://spark-master:7077",
        help="Spark master URL.",
    )
    parser.add_argument(
        "--source-table",
        default=DEFAULT_SOURCE_TABLE,
        help="Input Spark table, for example silver_copy.biometric_valid_test.",
    )
    parser.add_argument(
        "--output-table",
        default=DEFAULT_OUTPUT_TABLE,
        help="Output Spark table for standardized schema.",
    )
    parser.add_argument(
        "--mode",
        choices=["overwrite", "append"],
        default="overwrite",
        help="Write mode for the output table.",
    )
    parser.add_argument(
        "--run-id",
        default="manual_schema_run",
        help="Silver run id to stamp when silver_run_id is missing.",
    )
    return parser.parse_args()


def normalize_name(name: str) -> str:
    normalized = name.strip().lower()
    normalized = normalized.replace("+", "_plus")
    normalized = normalized.replace(">=", "_greater_equal_")
    normalized = normalized.replace(">", "_greater_")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def find_source_column(df_columns: Iterable[str], canonical_col: str) -> str | None:
    original_by_normalized = {normalize_name(col_name): col_name for col_name in df_columns}

    for alias in COLUMN_ALIASES.get(canonical_col, [canonical_col]):
        normalized_alias = normalize_name(alias)
        if normalized_alias in original_by_normalized:
            return original_by_normalized[normalized_alias]

    return None


def standardize_biometric_schema(df: DataFrame, run_id: str) -> DataFrame:
    selected_columns = []
    missing_columns = []

    for canonical_col in EXPECTED_COLUMNS:
        source_col = find_source_column(df.columns, canonical_col)

        if source_col:
            selected_columns.append(F.col(f"`{source_col}`").alias(canonical_col))
        elif canonical_col == "silver_processed_ts":
            selected_columns.append(F.current_timestamp().alias(canonical_col))
        elif canonical_col == "silver_run_id":
            selected_columns.append(F.lit(run_id).alias(canonical_col))
        elif canonical_col in ("partition_year", "partition_month"):
            continue
        else:
            missing_columns.append(canonical_col)

    if missing_columns:
        raise ValueError(f"Missing required columns after schema mapping: {missing_columns}")

    standardized_df = df.select(*selected_columns)

    standardized_df = standardized_df.withColumn(
        "date",
        F.coalesce(
            F.to_date(F.col("date"), "dd-MM-yyyy"),
            F.to_date(F.col("date"), "yyyy-MM-dd"),
            F.col("date").cast("date"),
        ),
    )

    for col_name, data_type in EXPECTED_TYPES.items():
        if col_name != "date":
            standardized_df = standardized_df.withColumn(col_name, F.col(col_name).cast(data_type))

    standardized_df = standardized_df.withColumn("partition_year", F.year(F.col("date")))
    standardized_df = standardized_df.withColumn("partition_month", F.month(F.col("date")))

    return standardized_df.select(*EXPECTED_COLUMNS)


def print_schema_report(source_df: DataFrame, output_df: DataFrame) -> None:
    print("Source columns:")
    print(source_df.columns)
    print("Standardized columns:")
    print(output_df.columns)

    actual_types = {field.name: field.dataType.simpleString() for field in output_df.schema.fields}
    type_mismatches = {
        col_name: {"expected": expected_type, "actual": actual_types.get(col_name)}
        for col_name, expected_type in EXPECTED_TYPES.items()
        if actual_types.get(col_name) != expected_type
    }

    if type_mismatches:
        raise ValueError(f"Data type mismatches after standardization: {type_mismatches}")

    print("Schema validation passed: columns, order, and data types match expected schema.")


def main() -> None:
    args = parse_args()
    spark = build_spark("biometric-standard-schema", args.master)

    try:
        source_df = spark.table(args.source_table)
        standardized_df = standardize_biometric_schema(source_df, args.run_id)
        print_schema_report(source_df, standardized_df)

        output_db = args.output_table.split(".", 1)[0]
        spark.sql(f"CREATE DATABASE IF NOT EXISTS {output_db}")

        (
            standardized_df.write.format("delta")
            .mode(args.mode)
            .option("overwriteSchema", "true")
            .partitionBy("partition_year", "partition_month")
            .saveAsTable(args.output_table)
        )

        output_count = spark.table(args.output_table).count()
        print(f"[OK] {args.source_table} -> {args.output_table} | rows={output_count}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
