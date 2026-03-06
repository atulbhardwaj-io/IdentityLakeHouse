from __future__ import annotations

import argparse

from pyspark.sql import SparkSession, functions as F


def build_spark(master: str | None) -> SparkSession:
    builder = (
        SparkSession.builder.appName("EnrollmentBronzeEDA")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    )
    if master:
        builder = builder.master(master)
    return builder.getOrCreate()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EDA for Bronze enrollment Delta table.")
    parser.add_argument(
        "--path",
        default="scripts/bronze_layer/enrolment",
        help="Delta table path for enrollment Bronze data.",
    )
    parser.add_argument(
        "--master",
        default=None,
        help="Optional Spark master (example: local[*] or spark://spark-master:7077).",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=10,
        help="Number of rows to show in sample output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spark = build_spark(args.master)

    try:
        df = spark.read.format("delta").load(args.path)

        print("\n=== ENROLLMENT BRONZE EDA ===")
        print(f"Path: {args.path}")
        print(f"Total rows: {df.count()}")
        print(f"Total columns: {len(df.columns)}")

        print("\n=== SCHEMA ===")
        df.printSchema()

        print(f"\n=== SAMPLE ({args.sample_rows} ROWS) ===")
        df.show(args.sample_rows, truncate=False)

        critical_cols = [c for c in ["date", "state", "district", "pincode"] if c in df.columns]
        if critical_cols:
            print("\n=== NULL CHECK (CRITICAL COLUMNS) ===")
            null_exprs = [
                F.sum(F.when(F.col(c).isNull() | (F.trim(F.col(c)) == ""), 1).otherwise(0)).alias(f"{c}_null_or_empty")
                for c in critical_cols
            ]
            df.select(*null_exprs).show(truncate=False)

        if all(c in df.columns for c in ["date", "state", "district", "pincode"]):
            print("\n=== DUPLICATE KEY CHECK: (date, state, district, pincode) ===")
            dup_df = (
                df.groupBy("date", "state", "district", "pincode")
                .count()
                .filter(F.col("count") > 1)
                .orderBy(F.desc("count"))
            )
            dup_count = dup_df.count()
            print(f"Duplicate key groups: {dup_count}")
            if dup_count > 0:
                dup_df.show(20, truncate=False)

        if "pincode" in df.columns:
            print("\n=== PINCODE FORMAT CHECK (6 digits) ===")
            bad_pincode_df = df.filter(
                F.col("pincode").isNull() | (~F.col("pincode").cast("string").rlike(r"^[0-9]{6}$"))
            )
            print(f"Invalid pincode rows: {bad_pincode_df.count()}")
            bad_pincode_df.select("pincode").show(10, truncate=False)

        if "date" in df.columns:
            print("\n=== DATE PARSE CHECK (dd-MM-yyyy or yyyy-MM-dd) ===")
            date_ok = F.coalesce(
                F.to_date(F.col("date"), "dd-MM-yyyy"),
                F.to_date(F.col("date"), "yyyy-MM-dd"),
            )
            bad_date_df = df.filter(F.col("date").isNotNull() & date_ok.isNull())
            print(f"Invalid date rows: {bad_date_df.count()}")
            bad_date_df.select("date").show(10, truncate=False)

        print("\n=== DISTINCT COUNTS ===")
        for col_name in ["state", "district", "pincode"]:
            if col_name in df.columns:
                distinct_count = df.select(col_name).distinct().count()
                print(f"{col_name}_distinct: {distinct_count}")

        print("\n=== TOP STATES BY RECORDS ===")
        if "state" in df.columns:
            (
                df.groupBy("state")
                .count()
                .orderBy(F.desc("count"))
                .show(20, truncate=False)
            )

        print("\n=== EDA COMPLETE ===")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
