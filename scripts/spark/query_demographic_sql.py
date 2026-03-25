from pyspark.sql import SparkSession

SPARK_WAREHOUSE_DIR = "/app/spark-warehouse"
HIVE_METASTORE_URL = "jdbc:derby:;databaseName=/app/metastore_db;create=true"

# Create Spark session with Delta support
spark = (
    SparkSession.builder
    .appName("DemographicSQLQuery")
    .config("spark.sql.catalogImplementation", "hive")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .config("spark.sql.warehouse.dir", SPARK_WAREHOUSE_DIR)
    .config("javax.jdo.option.ConnectionURL", HIVE_METASTORE_URL)
    .enableHiveSupport()
    .getOrCreate()
)

# Read Delta table
df = spark.read.format("delta").load("/app/scripts/bronze_layer/demographic")

# Register table for SQL
df.createOrReplaceTempView("demographic")

print("\n=== Total records per state ===")

# Spark SQL Query
result = spark.sql("""
SELECT state, COUNT(*) as total_records
FROM demographic
GROUP BY state
ORDER BY total_records DESC
""")

# Show result
result.show()

spark.stop()
