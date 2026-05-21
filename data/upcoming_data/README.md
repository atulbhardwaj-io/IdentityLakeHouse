# Upcoming Incremental CSV Data

Put new incoming CSV files in the folder for the target Bronze table.

The first folder under `upcoming_data` decides the Delta table:

```text
data/upcoming_data/demographic/                 -> bronze.demographic
data/upcoming_data/enrolment/                   -> bronze.enrolment
data/upcoming_data/biometric/                   -> bronze.biometric
data/upcoming_data/aadhaar_voter_link_raw/      -> bronze.aadhaar_voter_link_raw
data/upcoming_data/district_scheme_payment_raw/ -> bronze.district_scheme_payment_raw
data/upcoming_data/population_raw/              -> bronze.population_raw
data/upcoming_data/scheme_beneficiary_raw/      -> bronze.scheme_beneficiary_raw
data/upcoming_data/scheme_master_raw/           -> bronze.scheme_master_raw
data/upcoming_data/voter_registry_raw/          -> bronze.voter_registry_raw
```

Recommended daily layout inside each table folder:

```text
data/upcoming_data/<table_name>/year=YYYY/month=MM/day=DD/<table_name>_YYYY_MM_DD.csv
```

Example:

```text
data/upcoming_data/population_raw/year=2026/month=05/day=21/population_raw_2026_05_21.csv
```

Run Bronze ingestion:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables population_raw
```

Run all upcoming CSV files for all 9 Bronze tables together:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables all
```

Run upcoming CSV files into Bronze and then incrementally load Silver in the same run:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -BronzeTables all -SilverTables all
```

Run only Bronze-to-Silver incremental load after Bronze is already loaded:

```powershell
.\run_pipeline.ps1 -SilverTables all
```

The loader reads only files not already recorded in `bronze_control.ingested_files`.

The Silver loader reads only Bronze batches not already recorded in
`silver_control.processed_bronze_batches`.

## Load Commands

Run only Bronze incremental load for all tables:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables all
```

Run Bronze incremental load and Silver incremental load together:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -BronzeTables all -SilverTables all
```

Run only Silver incremental load after Bronze is already loaded:

```powershell
.\run_pipeline.ps1 -SilverTables all
```

Run one table from CSV to Bronze and then Bronze to Silver:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -BronzeTables demographic -SilverTables demographic
```

Run only one table from Bronze to Silver:

```powershell
.\run_pipeline.ps1 -SilverTables demographic
```

To reload all files again, use `-ForceBronzeReprocess` carefully:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables all -ForceBronzeReprocess
```

Reload one table's incoming CSV files into Bronze:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables demographic -ForceBronzeReprocess
```

For a full Silver rebuild instead of incremental append, use:

```powershell
.\run_pipeline.ps1 -SilverTables all -SilverLoadType full -SilverMode overwrite
```

## Load Indicators

Bronze load indicator columns:

```text
bronze_ingest_ts
bronze_source_file
bronze_batch_id
```

Bronze file manifest table:

```text
bronze_control.ingested_files
```

Silver load indicator columns:

```text
silver_processed_ts
silver_run_id
bronze_batch_id
```

Silver processed-batch control table:

```text
silver_control.processed_bronze_batches
```

## Verification Queries

Check which files were loaded into Bronze:

```python
spark.sql("""
SELECT table_name, source_file_name, bronze_batch_id, row_count, status, bronze_ingest_ts
FROM bronze_control.ingested_files
ORDER BY bronze_ingest_ts DESC
""").show(truncate=False)
```

Check rows loaded into one Bronze table by run:

```python
spark.sql("""
SELECT bronze_batch_id, COUNT(*) AS rows
FROM bronze.demographic
GROUP BY bronze_batch_id
ORDER BY bronze_batch_id DESC
""").show(truncate=False)
```

Check which Bronze batches reached Silver:

```python
spark.sql("""
SELECT table_name, bronze_batch_id, silver_run_id, input_rows, output_rows, status, processed_ts
FROM silver_control.processed_bronze_batches
ORDER BY processed_ts DESC
""").show(truncate=False)
```

Check rows loaded into one Silver table by run:

```python
spark.sql("""
SELECT silver_run_id, bronze_batch_id, COUNT(*) AS rows
FROM silver.demographic_valid
GROUP BY silver_run_id, bronze_batch_id
ORDER BY silver_run_id DESC
""").show(truncate=False)
```

Run the same incremental command twice. On the second run, Bronze should print:

```text
[SKIP] No new CSV files for <table>
```

Silver should print:

```text
[SKIP] No new Bronze batches for <table>
```
