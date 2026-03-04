from pyspark.sql import SparkSession

# Create Spark session with Delta support
spark = (
    SparkSession.builder
    .appName("DemographicSQLQuery")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
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