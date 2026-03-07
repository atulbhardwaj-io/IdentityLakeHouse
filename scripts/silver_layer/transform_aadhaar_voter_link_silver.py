from __future__ import annotations

import argparse

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql import Window


def build_spark(master: str) -> SparkSession:
    return (
        SparkSession.builder.appName("silver-aadhaar-voter-link-transform")
        .master(master)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply Silver transformations for aadhaar_voter_link table."
    )
    parser.add_argument(
        "--master",
        default="spark://spark-master:7077",
        help="Spark master URL.",
    )
    parser.add_argument(
        "--input-path",
        default="/app/scripts/silver_layer/aadhaar_voter_link_raw_valid_test",
        help="Input Delta path (usually the _test table).",
    )
    parser.add_argument(
        "--output-path",
        default="/app/scripts/silver_layer/aadhaar_voter_link_raw_valid_test",
        help="Output Delta path for transformed result.",
    )
    parser.add_argument(
        "--main-path",
        default="/app/scripts/silver_layer/aadhaar_voter_link_raw_valid",
        help="Main Silver Delta path for optional promotion.",
    )
    parser.add_argument(
        "--run-id",
        default="manual_transform",
        help="Run id stamped into transformed rows.",
    )
    parser.add_argument(
        "--promote",
        action="store_true",
        help="If set, overwrite main-path with transformed output after validation.",
    )
    return parser.parse_args()


def apply_transformations(df: DataFrame, run_id: str) -> DataFrame:
    # Canonical date parsing from known formats.
    parsed_date = F.coalesce(
        F.to_date("date", "dd-MM-yyyy"),
        F.to_date("date", "yyyy-MM-dd"),
    )

    cleaned = (
        df.withColumn("event_date", parsed_date)
        .withColumn("pincode_str", F.lpad(F.col("pincode").cast("string"), 6, "0"))
        .filter(F.col("event_date").isNotNull())
        .filter(F.col("pincode_str").rlike(r"^[0-9]{6}$"))
    )

    numeric_cols = [
        "voter_total",
        "aadhaar_available",
        "aadhaar_voter_linked",
        "linkage_pending",
        "linkage_rejected",
        "kyc_pending",
        "duplicate_suspected",
    ]
    for col_name in numeric_cols:
        if col_name in cleaned.columns:
            cleaned = cleaned.filter(F.col(col_name).isNull() | (F.col(col_name) >= 0))

    # Deterministic dedup by business key; keep most recent ingest row when available.
    order_cols = []
    if "ingest_ts" in cleaned.columns:
        order_cols.append(F.col("ingest_ts").desc_nulls_last())
    if "silver_processed_ts" in cleaned.columns:
        order_cols.append(F.col("silver_processed_ts").desc_nulls_last())
    if not order_cols:
        order_cols.append(F.monotonically_increasing_id().desc())

    w = Window.partitionBy("event_date", "state", "district", "pincode_str").orderBy(*order_cols)
    deduped = (
        cleaned.withColumn("rn", F.row_number().over(w))
        .filter(F.col("rn") == 1)
        .drop("rn")
    )

    out = (
        deduped.drop("date", "pincode")
        .withColumnRenamed("event_date", "date")
        .withColumnRenamed("pincode_str", "pincode")
        .withColumn("silver_processed_ts", F.current_timestamp())
        .withColumn("silver_run_id", F.lit(run_id))
        .select(
            "date",
            "state",
            "district",
            "pincode",
            "voter_total",
            "aadhaar_available",
            "aadhaar_voter_linked",
            "linkage_pending",
            "linkage_rejected",
            "linkage_pct",
            "kyc_pending",
            "duplicate_suspected",
            "data_source",
            "ingest_ts",
            "silver_processed_ts",
            "silver_run_id",
        )
    )
    return out


def main() -> None:
    args = parse_args()
    spark = build_spark(args.master)
    try:
        base = spark.read.format("delta").load(args.input_path)
        before_count = base.count()

        transformed = apply_transformations(base, run_id=args.run_id)
        transformed.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(args.output_path)

        final_df = spark.read.format("delta").load(args.output_path)
        after_count = final_df.count()
        print(f"[OK] transformed: {args.input_path} -> {args.output_path}")
        print(f"[INFO] rows before={before_count}, after={after_count}")

        if args.promote:
            final_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(args.main_path)
            print(f"[PROMOTED] {args.output_path} -> {args.main_path}")
        else:
            print("[TEST_ONLY] Main table not changed. Use --promote to update main.")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
