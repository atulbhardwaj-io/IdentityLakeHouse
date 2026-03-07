import os
from pyspark.sql import SparkSession

# ==========================================
# CREATE SPARK SESSION
# ==========================================

spark = SparkSession.builder \
    .appName("IdentityLakehouse") \
    .master("spark://spark-master:7077") \
    .getOrCreate()

print(" Spark Session Created")


# ==========================================
# BRONZE OUTPUT BASE PATH
# ==========================================

bronze_base_path = "/app/scripts/bronze_layer"


# ==========================================
# FUNCTION TO WRITE DELTA TABLE
# ==========================================

def write_delta(df, table_name):
    output_path = f"{bronze_base_path}/{table_name}"

    df.write \
        .format("delta") \
        .mode("overwrite") \
        .save(output_path)

    print(f" {table_name} Delta Table Created")


# ==========================================
# 1️ LOAD SYNTHETIC DATA (SKIP District_Masters)
# ==========================================

synthetic_folder = "/app/synthetic_data/synthetic"
skip_files = ["district_masters.csv"]  # case-insensitive safe

print(" Processing Synthetic Data...")

for file in os.listdir(synthetic_folder):

    if file.endswith(".csv") and file.lower() not in skip_files:

        file_path = f"{synthetic_folder}/{file}"
        table_name = file.replace(".csv", "").lower()

        df = spark.read \
            .option("header", True) \
            .option("inferSchema", True) \
            .csv(file_path)

        write_delta(df, table_name)


# ==========================================
# 2️ LOAD DEMOGRAPHIC DATA (COMBINED FILE)
# ==========================================

print(" Processing Demographic Data...")

demographic_df = spark.read \
    .option("header", True) \
    .option("inferSchema", True) \
    .csv("/app/data/api_data_aadhar_demographic/api_data_aadhar_demographic/api_data_aadhar_demographic_combined.csv")

write_delta(demographic_df, "demographic")


# ==========================================
# 3️ LOAD ENROLMENT DATA (COMBINED FILE)
# ==========================================

print(" Processing Enrolment Data...")

enrolment_df = spark.read \
    .option("header", True) \
    .option("inferSchema", True) \
    .csv("/app/data/api_data_aadhar_enrolment/api_data_aadhar_enrolment/api_data_aadhar_enrolment_combined.csv")

write_delta(enrolment_df, "enrolment")


# ==========================================
# 4️ LOAD BIOMETRIC DATA (COMBINED FILE)
# ==========================================

print(" Processing Biometric Data...")

biometric_df = spark.read \
    .option("header", True) \
    .option("inferSchema", True) \
    .csv("/app/data/api_data_aadhar_biometric/api_data_aadhar_biometric/api_data_aadhar_biometric_combined.csv")

write_delta(biometric_df, "biometric")


spark.stop()

print(" ALL DELTA TABLES CREATED SUCCESSFULLY")