from __future__ import annotations

import argparse
import uuid
from dataclasses import dataclass
from pathlib import Path

from delta import configure_spark_with_delta_pip
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


SPARK_WAREHOUSE_DIR = "/app/spark-warehouse"
HIVE_METASTORE_URL = "jdbc:derby:;databaseName=/app/metastore_db;create=true"


@dataclass(frozen=True)
class TableConfig:
    name: str
    file_name: str
    schema: StructType
    partition_cols: list[str]


TABLE_CONFIGS: dict[str, TableConfig] = {
    "population_raw": TableConfig(
        name="population_raw",
        file_name="population_raw.csv",
        schema=StructType(
            [
                StructField("date", StringType(), True),
                StructField("state", StringType(), True),
                StructField("district", StringType(), True),
                StructField("pincode", StringType(), True),
                StructField("population_total", IntegerType(), True),
                StructField("male", IntegerType(), True),
                StructField("female", IntegerType(), True),
                StructField("age_0_5", IntegerType(), True),
                StructField("age_6_17", IntegerType(), True),
                StructField("age_18_plus", IntegerType(), True),
            ]
        ),
        partition_cols=["date"],
    ),
    "scheme_master_raw": TableConfig(
        name="scheme_master_raw",
        file_name="scheme_master_raw.csv",
        schema=StructType(
            [
                StructField("scheme_id", StringType(), True),
                StructField("scheme_name", StringType(), True),
                StructField("scheme_type", StringType(), True),
                StructField("target_group", StringType(), True),
                StructField("start_date", StringType(), True),
                StructField("end_date", StringType(), True),
                StructField("eligibility_rule", StringType(), True),
                StructField("active_flag", IntegerType(), True),
            ]
        ),
        partition_cols=["active_flag"],
    ),
    "scheme_beneficiary_raw": TableConfig(
        name="scheme_beneficiary_raw",
        file_name="scheme_beneficiary_raw.csv",
        schema=StructType(
            [
                StructField("date", StringType(), True),
                StructField("start_date", StringType(), True),
                StructField("end_date", StringType(), True),
                StructField("state", StringType(), True),
                StructField("district", StringType(), True),
                StructField("pincode", StringType(), True),
                StructField("scheme_id", StringType(), True),
                StructField("applications_received", IntegerType(), True),
                StructField("beneficiaries_approved", IntegerType(), True),
                StructField("beneficiaries_rejected", IntegerType(), True),
                StructField("beneficiaries_disbursed", IntegerType(), True),
                StructField("disbursed_amount", DoubleType(), True),
                StructField("data_source", StringType(), True),
                StructField("ingest_ts", StringType(), True),
            ]
        ),
        partition_cols=["date"],
    ),
    "voter_registry_raw": TableConfig(
        name="voter_registry_raw",
        file_name="voter_registry_raw.csv",
        schema=StructType(
            [
                StructField("date", StringType(), True),
                StructField("state", StringType(), True),
                StructField("district", StringType(), True),
                StructField("pincode", StringType(), True),
                StructField("voter_total", IntegerType(), True),
                StructField("male_voters", IntegerType(), True),
                StructField("female_voters", IntegerType(), True),
                StructField("other_voters", IntegerType(), True),
                StructField("new_registrations", IntegerType(), True),
                StructField("deletions", IntegerType(), True),
                StructField("net_change", IntegerType(), True),
                StructField("turnout_pct_est", DoubleType(), True),
                StructField("data_source", StringType(), True),
                StructField("ingest_ts", StringType(), True),
            ]
        ),
        partition_cols=["date"],
    ),
    "aadhaar_voter_link_raw": TableConfig(
        name="aadhaar_voter_link_raw",
        file_name="aadhaar_voter_link_raw.csv",
        schema=StructType(
            [
                StructField("date", StringType(), True),
                StructField("state", StringType(), True),
                StructField("district", StringType(), True),
                StructField("pincode", StringType(), True),
                StructField("voter_total", IntegerType(), True),
                StructField("aadhaar_available", IntegerType(), True),
                StructField("aadhaar_voter_linked", IntegerType(), True),
                StructField("linkage_pending", IntegerType(), True),
                StructField("linkage_rejected", IntegerType(), True),
                StructField("linkage_pct", DoubleType(), True),
                StructField("kyc_pending", IntegerType(), True),
                StructField("duplicate_suspected", IntegerType(), True),
                StructField("data_source", StringType(), True),
                StructField("ingest_ts", StringType(), True),
            ]
        ),
        partition_cols=["date"],
    ),
    "district_scheme_payment_raw": TableConfig(
        name="district_scheme_payment_raw",
        file_name="district_scheme_payment_raw.csv",
        schema=StructType(
            [
                StructField("date", StringType(), True),
                StructField("state", StringType(), True),
                StructField("district", StringType(), True),
                StructField("pincode", StringType(), True),
                StructField("scheme_id", StringType(), True),
                StructField("beneficiaries_paid", IntegerType(), True),
                StructField("failed_payments", IntegerType(), True),
                StructField("pending_payments", IntegerType(), True),
                StructField("avg_amount_per_beneficiary", DoubleType(), True),
                StructField("amount_paid", DoubleType(), True),
                StructField("amount_failed", DoubleType(), True),
                StructField("amount_pending", DoubleType(), True),
                StructField("utilization_pct", DoubleType(), True),
                StructField("data_source", StringType(), True),
                StructField("ingest_ts", StringType(), True),
            ]
        ),
        partition_cols=["date"],
    ),
}


def build_spark(app_name: str) -> SparkSession:
    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.driver.memory", "4g")
        .config("spark.hadoop.io.native.lib.available", "false")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.catalogImplementation", "hive")
        .config("spark.sql.warehouse.dir", SPARK_WAREHOUSE_DIR)
        .config("javax.jdo.option.ConnectionURL", HIVE_METASTORE_URL)
    )
    return configure_spark_with_delta_pip(builder).enableHiveSupport().getOrCreate()


def parse_date_col(df: DataFrame, col_name: str) -> DataFrame:
    return df.withColumn(
        col_name,
        F.coalesce(
            F.to_date(F.col(col_name), "dd-MM-yyyy"),
            F.to_date(F.col(col_name), "yyyy-MM-dd"),
        ),
    )


def apply_standard_transforms(df: DataFrame) -> DataFrame:
    for c in ["date", "start_date", "end_date"]:
        if c in df.columns:
            df = parse_date_col(df, c)

    if "ingest_ts" in df.columns:
        df = df.withColumn("ingest_ts", F.to_timestamp("ingest_ts"))
    else:
        df = df.withColumn("ingest_ts", F.lit(None).cast(TimestampType()))

    return (
        df.withColumn("bronze_ingest_ts", F.current_timestamp())
        .withColumn("bronze_source_file", F.input_file_name())
        .withColumn("bronze_batch_id", F.lit(str(uuid.uuid4())))
    )


def load_one_table(
    spark: SparkSession,
    config: TableConfig,
    input_root: Path,
    output_root: Path,
    mode: str,
) -> None:
    input_path = input_root / config.file_name
    if not input_path.exists():
        raise FileNotFoundError(f"Missing input file: {input_path}")

    output_path = output_root / config.name

    df = (
        spark.read.option("header", True)
        .schema(config.schema)
        .csv(str(input_path))
    )

    df = apply_standard_transforms(df)

    (
        df.write.format("delta")
        .mode(mode)
        .partitionBy(*config.partition_cols)
        .save(str(output_path))
    )

    spark.sql("CREATE DATABASE IF NOT EXISTS bronze")
    spark.sql(
        f"CREATE TABLE IF NOT EXISTS bronze.{config.name} USING DELTA LOCATION '{str(output_path).replace(chr(92), '/')}'"
    )

    row_count = spark.read.format("delta").load(str(output_path)).count()
    print(f"[OK] bronze.{config.name} -> rows: {row_count}, path: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Bronze Delta tables from synthetic raw CSV files.")
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["all"],
        help="Table names to process (or 'all').",
    )
    parser.add_argument(
        "--input-root",
        default="synthetic_data/synthetic",
        help="Input CSV folder path.",
    )
    parser.add_argument(
        "--output-root",
        default="data/bronze/synthetic",
        help="Bronze Delta output folder path.",
    )
    parser.add_argument(
        "--mode",
        choices=["overwrite", "append"],
        default="overwrite",
        help="Write mode for Bronze Delta tables.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    requested = set(args.tables)
    if "all" in requested:
        selected = list(TABLE_CONFIGS.keys())
    else:
        unknown = sorted([t for t in requested if t not in TABLE_CONFIGS])
        if unknown:
            raise ValueError(f"Unknown table(s): {', '.join(unknown)}")
        selected = list(requested)

    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    spark = build_spark("bronze-synthetic-loader")
    try:
        for table_name in selected:
            load_one_table(
                spark=spark,
                config=TABLE_CONFIGS[table_name],
                input_root=input_root,
                output_root=output_root,
                mode=args.mode,
            )
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
