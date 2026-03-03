# IdentityLakehouse - Day 1: CSV to Delta (Bronze Layer Setup)

## Overview

Today we successfully built a local Lakehouse ingestion pipeline using:

- Docker (Spark cluster: master + workers)
- Apache Spark (3.5.1)
- Delta Lake
- Synthetic + Aadhaar API datasets
- Bronze Layer architecture

We converted multiple CSV files into Delta tables running on a Spark cluster inside Docker.

This is production-style data engineering architecture.

---

## What We Accomplished Today

### 1. Understood Container vs Local File System

We learned:

- Windows path is different from Docker container path
- `/app` exists inside Docker
- Volume mapping connects local project to container

This is a very important infrastructure concept.

---

### 2. Setup Spark Cluster in Docker

We verified:

- `spark-master` running
- `spark-worker` running
- cluster connected successfully
- Spark UI accessible

We executed Spark jobs using:

```bash
/opt/spark/bin/spark-submit
```

---

### 3. Integrated Delta Lake Properly

Instead of installing Delta via pip, we used the industry-standard method:

```bash
--packages io.delta:delta-spark_2.12:3.0.0
--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension
--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog
```

This mirrors real production clusters like:

- Databricks
- EMR
- Standalone Spark clusters

---

### 4. Built Bronze Layer

#### Data Sources

#### Synthetic Data

- `aadhaar_voter_link_raw.csv`
- `district_scheme_payment_raw.csv`
- `population_raw.csv`
- `scheme_beneficiary_raw.csv`
- `scheme_master_raw.csv`
- `voter_registry_raw.csv`

Excluded `District_Masters` intentionally.

#### Aadhaar API Data

- Demographic (combined)
- Enrolment (combined)
- Biometric (combined)

---

### 5. Converted CSV to Delta Tables

Each dataset was written using:

```python
df.write \
    .format("delta") \
    .mode("overwrite") \
    .save("/app/scripts/bronze_layer/<table_name>")
```

Result:

```text
bronze_layer/
|-- demographic/
|-- enrolment/
|-- biometric/
|-- aadhaar_voter_link_raw/
|-- district_scheme_payment_raw/
|-- population_raw/
|-- scheme_beneficiary_raw/
|-- scheme_master_raw/
`-- voter_registry_raw/
```

Each folder contains:

```text
_delta_log/
part-00000.parquet
```

That means they are true Delta tables.

---

## What We Learned Today

### Infrastructure Concepts

- Docker container file systems
- Volume mapping
- Spark cluster submission
- Worker execution
- Ivy dependency management

### Spark Concepts

- `spark-submit`
- cluster mode
- wildcard file reading
- combined vs chunked file handling
- DataFrame read/write

### Delta Lake Concepts

- Delta tables
- `_delta_log` importance
- why Delta is better than plain Parquet
- dependency integration via `--packages`

### Debugging Skills

We solved:

- PATH issues
- nested folder structure
- Ivy cache permission errors
- module import errors
- Delta column restrictions
- file not found errors

This is real-world data engineering troubleshooting.

---

## Architecture Built Today

```text
Raw CSV Files
      |
      v
Spark Cluster (Docker)
      |
      v
Delta Lake Bronze Layer
```

You built a real Lakehouse ingestion pipeline.

---

## If You Want To Repeat This In Future Projects

Follow this structured checklist:

### Step 1 - Setup Environment

- Install Docker
- Pull Spark image
- Configure master + worker
- Map project folder to `/app`

### Step 2 - Organize Project Structure

```text
project/
|-- data/
|-- synthetic_data/
|-- scripts/
|   |-- spark/
|   |-- bronze_layer/
|   `-- silver_layer/
```

Good folder structure equals a professional project.

### Step 3 - Create Spark Ingestion Script

- Create `SparkSession`
- Read CSV files
- Handle nested directories
- Skip unwanted files
- Write as Delta format

### Step 4 - Run Using `spark-submit`

Use:

```bash
docker exec -it spark-master /opt/spark/bin/spark-submit \
--master spark://spark-master:7077 \
--packages io.delta:delta-spark_2.12:3.0.0 \
--conf spark.jars.ivy=/tmp/.ivy2 \
--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
/app/scripts/spark/your_script.py
```

### Step 5 - Validate Output

- Check `bronze_layer` folder
- Confirm `_delta_log` exists
- Verify no duplicate data
- Check schema

### Step 6 - Move To Silver Layer

After Bronze:

- clean column names
- remove nulls
- join datasets
- add business logic
- partition by state/district
- optimize storage

---

## What Level You Reached Today

You moved from:

"Learning Spark basics"

To:

"Building Lakehouse ingestion on distributed cluster"

This is a huge jump.

---

## Key Takeaways

- Always verify folder structure inside container
- Use wildcard for scalable ingestion
- Use `--packages` for Delta integration
- Bronze layer should store raw standardized data
- Debugging is 50% of real data engineering

---

## Next Recommended Steps

1. Add column cleaning logic
2. Register Delta tables in Spark SQL
3. Create Silver transformations
4. Add partitioning by state
5. Implement incremental loading
6. Try same project on Databricks

---

## Final Status

- Spark cluster working
- Delta integrated
- Bronze ingestion complete
- Synthetic + API datasets converted
- Debugging skills improved
- Ready for Silver layer

---

You officially built a working Lakehouse ingestion system locally.

That is serious progress.

---

**Day 1 Complete**

Ready for Silver Layer tomorrow.
