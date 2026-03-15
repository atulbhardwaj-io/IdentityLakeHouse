import os

from pyspark.sql import SparkSession


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


def write_delta(df, table_name: str) -> None:
    output_path = f"{BRONZE_BASE_PATH}/{table_name}"

    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .save(output_path)
    )

    row_count = df.count()
    print(f"[OK] {table_name} Delta table created | rows={row_count} | path={output_path}")
    print(f"[SCHEMA] {table_name}: {df.columns}")


def register_bronze_table(spark: SparkSession, table_name: str) -> None:
    output_path = f"{BRONZE_BASE_PATH}/{table_name}"
    spark.sql("CREATE DATABASE IF NOT EXISTS bronze")
    spark.sql(
        f"CREATE TABLE IF NOT EXISTS bronze.{table_name} "
        f"USING DELTA LOCATION '{output_path}'"
    )
    print(f"[REGISTERED] bronze.{table_name}")


spark = build_spark()
print("Spark Session Created")


print("Processing Synthetic Data...")
for file_name in os.listdir(SYNTHETIC_FOLDER):
    if not file_name.endswith(".csv"):
        continue
    if file_name.lower() in SKIP_FILES:
        continue

    file_path = f"{SYNTHETIC_FOLDER}/{file_name}"
    table_name = file_name.replace(".csv", "").lower()
    df = load_csv(spark, file_path)
    write_delta(df, table_name)
    register_bronze_table(spark, table_name)


print("Processing Demographic Data...")
demographic_df = load_csv(spark, DEMOGRAPHIC_CSV)
write_delta(demographic_df, "demographic")
register_bronze_table(spark, "demographic")


print("Processing Enrolment Data...")
enrolment_df = load_csv(spark, ENROLMENT_CSV)
write_delta(enrolment_df, "enrolment")
register_bronze_table(spark, "enrolment")


print("Processing Biometric Data...")
biometric_df = load_csv(spark, BIOMETRIC_CSV)
write_delta(biometric_df, "biometric")
register_bronze_table(spark, "biometric")


spark.stop()
print("ALL DELTA TABLES CREATED SUCCESSFULLY")
