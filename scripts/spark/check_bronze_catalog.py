from pyspark.sql import SparkSession

SPARK_WAREHOUSE_DIR = "/app/spark-warehouse"
HIVE_METASTORE_URL = "jdbc:derby:;databaseName=/app/metastore_db;create=true"

# Re-use the master configuration and catalog from your pipeline script
spark = (
    SparkSession.builder.appName("CheckBronzeCatalog")
    .master("spark://spark-master:7077")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .config("spark.sql.warehouse.dir", SPARK_WAREHOUSE_DIR)
    .config("javax.jdo.option.ConnectionURL", HIVE_METASTORE_URL)
    .enableHiveSupport()
    .getOrCreate()
)

print("\n===============================")
print("     CHECKING METASTORE        ")
print("===============================\n")

print("--- DATABASES ---")
spark.sql("SHOW DATABASES").show(truncate=False)

print("\n--- TABLES IN 'bronze' DATABASE ---")
spark.sql("SHOW TABLES IN bronze").show(truncate=False)

try:
    print("\n--- SAMPLE DATA FROM bronze.demographic ---")
    spark.sql("SELECT * FROM bronze.demographic LIMIT 5").show(vertical=True)
except Exception as e:
    print(f"Could not load demographic: {e}")

spark.stop()
