from pyspark.sql import SparkSession
from pyspark.sql.functions import col
import time

def create_spark_session():
    spark = (
        SparkSession.builder
        .appName("IdentityLakehouse Bronze Layer")
        .master("spark://spark-master:7077")
        # Enable History Server Logging
        .config("spark.eventLog.enabled", "true")
        .config("spark.eventLog.dir", "/opt/spark/events")
        # Delta Lake Config
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )
    return spark


def main():
    spark = create_spark_session()

    print("🚀 Spark Cluster Connected Successfully")

    # Example Bronze Data
    df = spark.range(0, 1000000) \
              .withColumn("double_id", col("id") * 2)

    print("🔥 Running distributed count...")
    print("Total Records:", df.count())

    # Write Bronze Delta Table
    output_path = "/app/data/bronze_table"

    df.write \
      .format("delta") \
      .mode("overwrite") \
      .save(output_path)

    print("✅ Bronze Delta table written successfully.")

    # Keep UI alive for a few seconds (optional)
    time.sleep(10)

    spark.stop()
    print("🛑 Spark Session Stopped Cleanly")


if __name__ == "__main__":
    main()