# Silver Data Transformation Methods

This file explains the 2 main ways to transform Silver data in this project:

1. Spark SQL script method
2. PySpark script method
3. Quick check / quick change in `pyspark`

Use `silver_copy` or `*_valid_test` tables when you want to test safely without changing the main Silver tables.

## Method 1: Spark SQL Script

Use this when:
- your logic is mostly SQL
- you want easy tracking of query changes
- you want to version `.sql` files in Git

Recommended folder for SQL files:
- `scripts/silver_layer/sql_work`

Example SQL file:
- `scripts/silver_layer/sql_work/001_transform_silver_copy.sql`

Example content:

```sql
USE silver_copy;

SELECT COUNT(*) FROM demographic_valid_test;

DELETE FROM demographic_valid_test
WHERE state IS NULL;
```

Run it from PowerShell:

```powershell
docker exec spark-master /bin/bash -lc "/opt/spark/bin/spark-sql --master spark://spark-master:7077 --packages io.delta:delta-spark_2.12:3.0.0 --conf spark.jars.ivy=/tmp/.ivy2 --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog --conf spark.sql.warehouse.dir=/app/spark-warehouse --conf 'javax.jdo.option.ConnectionURL=jdbc:derby:;databaseName=/app/metastore_db;create=true' -f /app/scripts/silver_layer/sql_work/001_transform_silver_copy.sql"
```

Why use this:
- simple for SQL-based transformation
- easy to read and review
- easy to track in Git

How to track changes:
- Git tracks the `.sql` file
- Delta tracks data change history

Check Delta history in `pyspark`:

```python
spark.sql("DESCRIBE HISTORY silver_copy.demographic_valid_test").show(truncate=False)
```

## Method 2: PySpark Script

Use this when:
- transformation logic is complex
- you need DataFrame API
- you need conditional logic, loops, reusable functions, or custom processing

Recommended structure for PySpark files:
- keep reusable Spark utility scripts in `scripts/spark`
- keep table-specific Silver transformation work in a separate folder per dataset

Recommended per-table folder pattern:

```text
scripts/
  silver_layer/
    demographic_transform/
      transform_demographic.py
      README.md
    enrolment_transform/
      transform_enrolment.py
      README.md
    population_transform/
      transform_population.py
      README.md
```

Why this structure is useful:
- each table gets its own transformation space
- logic stays isolated and easier to understand
- population transformation, demographic transformation, and other table logic do not get mixed
- future validation SQL, notes, and helper files can live beside that table's script
- it becomes easier to maintain one folder per business dataset

Best practice in this project:
- one Silver table or subject area = one folder
- keep the Delta data itself in `scripts/silver_layer/<table>_valid`
- keep the transformation code in a separate transformation folder
- do not mix the code file inside the Delta table folder

Example layout:

```text
scripts/
  silver_layer/
    population_raw_valid/                  <- Delta data
    population_raw_valid_test/             <- Delta test copy
    population_transform/                  <- code and notes
      transform_population.py
      population_rules.sql
      README.md
```

Example PySpark file:
- `scripts/silver_layer/population_transform/transform_population.py`

Example content:

```python
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("MySilverTransform")
    .master("spark://spark-master:7077")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .config("spark.sql.warehouse.dir", "/app/spark-warehouse")
    .config("javax.jdo.option.ConnectionURL", "jdbc:derby:;databaseName=/app/metastore_db;create=true")
    .enableHiveSupport()
    .getOrCreate()
)

df = spark.read.format("delta").load("/app/scripts/silver_layer/demographic_valid_test")

df.createOrReplaceTempView("demo")

result = spark.sql("""
SELECT state, COUNT(*) AS total_rows
FROM demo
GROUP BY state
ORDER BY total_rows DESC
""")

result.show()

spark.stop()
```

Run it from PowerShell:

```powershell
docker exec spark-master /bin/bash -lc "/opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages io.delta:delta-spark_2.12:3.0.0 --conf spark.jars.ivy=/tmp/.ivy2 --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog --conf spark.sql.warehouse.dir=/app/spark-warehouse --conf 'javax.jdo.option.ConnectionURL=jdbc:derby:;databaseName=/app/metastore_db;create=true' /app/scripts/silver_layer/population_transform/transform_population.py"
```

Why use this:
- better for reusable logic
- better for complex transformations
- better when SQL alone is not enough
- better when every table needs its own transformation folder and history

How to track changes:
- Git tracks the `.py` file
- Delta tracks data changes through table history

Check Delta history in `pyspark`:

```python
spark.sql("DESCRIBE HISTORY silver_copy.demographic_valid_test").show(truncate=False)
```

## Which Method Should You Use?

Use Spark SQL when:
- the work is query-heavy
- the transformation is straightforward
- you want simple script-based tracking

Use PySpark when:
- the transformation is complex
- you need DataFrame operations
- you need programmatic control
- you want a separate folder for each dataset transformation, such as population, demographic, enrolment, and others

## Method 3: Quick Check or Quick Change in `pyspark`

Use this when:
- you want to inspect data quickly
- you want to test one small SQL statement
- you want to verify a table before writing a full script

Start Spark shell:

```powershell
.\run_pyspark.ps1
```

Example quick checks:

```python
spark.sql("SHOW DATABASES").show(truncate=False)
spark.sql("SHOW TABLES IN silver_copy").show(truncate=False)
spark.sql("SELECT COUNT(*) FROM silver_copy.demographic_valid_test").show()
spark.sql("SELECT * FROM silver_copy.demographic_valid_test LIMIT 10").show(truncate=False)
```

Example quick change:

```python
spark.sql("""
DELETE FROM silver_copy.demographic_valid_test
WHERE state IS NULL
""")
```

Check what changed:

```python
spark.sql("DESCRIBE HISTORY silver_copy.demographic_valid_test").show(truncate=False)
```

Important:
- this method is best for quick testing
- it is not the best method for long-term tracking
- for reusable work, move the final logic into a `.sql` or `.py` file

## Best Practice In This Project

- never test directly on main `silver.*` tables first
- use `silver_copy` or `*_valid_test` tables for experiments
- keep SQL scripts in `scripts/silver_layer/sql_work`
- keep reusable PySpark helpers in `scripts/spark`
- keep table-specific Silver transform scripts in separate folders under `scripts/silver_layer`
- use `pyspark` only for quick checks, debugging, and temporary trial changes
- track code changes with Git
- track data changes with `DESCRIBE HISTORY`
