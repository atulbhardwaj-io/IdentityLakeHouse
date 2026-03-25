import argparse

from pyspark.sql import SparkSession


SPARK_WAREHOUSE_DIR = "/app/spark-warehouse"
HIVE_METASTORE_URL = "jdbc:derby:;databaseName=/app/metastore_db;create=true"


def build_spark(app_name: str, master: str, file_format: str) -> SparkSession:
    builder = (
        SparkSession.builder.appName(app_name)
        .master(master)
        .config("spark.sql.catalogImplementation", "hive")
        .config("spark.sql.warehouse.dir", SPARK_WAREHOUSE_DIR)
        .config("javax.jdo.option.ConnectionURL", HIVE_METASTORE_URL)
    )

    if file_format == "delta":
        builder = (
            builder.config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        )

    return builder.enableHiveSupport().getOrCreate()


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview a Delta/Parquet dataset from path.")
    parser.add_argument("--path", required=True, help="Path to Delta table folder or Parquet folder")
    parser.add_argument("--format", choices=["delta", "parquet"], default="delta", help="Input dataset format")
    parser.add_argument("--master", default="local[*]", help="Spark master URL")
    parser.add_argument("--rows", type=int, default=20, help="Number of rows to show")
    args = parser.parse_args()

    spark = build_spark("ViewData", args.master, args.format)
    try:
        df = spark.read.format(args.format).load(args.path)
        print(f"\nPath: {args.path}")
        print(f"Format: {args.format}")
        print(f"Total rows: {df.count()}")
        print("\nSchema:")
        df.printSchema()
        print(f"\nTop {args.rows} rows:")
        df.show(args.rows, truncate=False)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
