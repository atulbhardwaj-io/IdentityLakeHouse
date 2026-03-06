from __future__ import annotations

import argparse
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession

DEFAULT_TABLES = ["enrolment", "demographic", "biometric"]


def build_spark(app_name: str, spark_mode: str, master: str | None) -> SparkSession:
    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    )
    if master:
        builder = builder.master(master)

    if spark_mode == "pip":
        # Local mode: resolve Delta package via python delta-spark helper.
        from delta import configure_spark_with_delta_pip

        ivy_cache = str(Path(".ivy2_local").resolve())
        builder = (
            builder.config("spark.driver.memory", "4g")
            .config("spark.hadoop.io.native.lib.available", "false")
            .config("spark.jars.ivy", ivy_cache)
        )
        return configure_spark_with_delta_pip(builder).getOrCreate()

    # Submit mode: rely on spark-submit --packages and --conf flags.
    return builder.getOrCreate()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Silver Phase 1: Load Bronze Delta tables as Spark DataFrames."
    )
    parser.add_argument(
        "--spark-mode",
        choices=["submit", "pip"],
        default="submit",
        help="submit: use Spark session from spark-submit config; pip: local delta-spark helper.",
    )
    parser.add_argument(
        "--master",
        default=None,
        help="Optional Spark master override (for example local[*] or spark://spark-master:7077).",
    )
    parser.add_argument(
        "--bronze-root",
        default="scripts/bronze_layer",
        help="Root folder that contains Bronze Delta table directories.",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        default=DEFAULT_TABLES,
        help="Bronze table directory names to load.",
    )
    parser.add_argument(
        "--preview-rows",
        type=int,
        default=5,
        help="Rows to preview per table after loading.",
    )
    return parser.parse_args()


def assert_delta_path(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Bronze path not found: {path}")
    if not (path / "_delta_log").exists():
        raise FileNotFoundError(f"Not a Delta table (missing _delta_log): {path}")


def load_bronze_table(spark: SparkSession, bronze_root: Path, table: str) -> DataFrame:
    table_path = bronze_root / table
    assert_delta_path(table_path)
    return spark.read.format("delta").load(str(table_path))


def main() -> None:
    args = parse_args()
    bronze_root = Path(args.bronze_root)

    spark = build_spark(
        app_name="silver-phase1-bronze-loader",
        spark_mode=args.spark_mode,
        master=args.master,
    )
    try:
        bronze_dfs: dict[str, DataFrame] = {}

        for table in args.tables:
            df = load_bronze_table(spark=spark, bronze_root=bronze_root, table=table)
            bronze_dfs[table] = df

            temp_view = f"bronze_{table}"
            df.createOrReplaceTempView(temp_view)

            print(f"\n[LOADED] {table}")
            print(f"Path: {(bronze_root / table).resolve()}")
            print(f"Rows: {df.count()}")
            print(f"Temp view: {temp_view}")
            print("Schema:")
            df.printSchema()

            if args.preview_rows > 0:
                print(f"Top {args.preview_rows} rows:")
                df.show(args.preview_rows, truncate=False)

        print(f"\n[OK] Loaded {len(bronze_dfs)} Bronze table(s) into DataFrames.")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
