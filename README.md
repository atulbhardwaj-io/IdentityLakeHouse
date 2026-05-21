# IdentityLakeHouse

## Need - Data-Driven Government
In today's digital era, governments generate massive amounts of data across departments such as welfare schemes, agriculture, health, education, and public distribution systems. However, this data is often stored in silos, inconsistent in format, incomplete, and difficult to analyze at scale. Without a unified and structured architecture, it becomes challenging to monitor scheme performance, detect inefficiencies, prevent fund leakage, and make evidence-based policy decisions. A data-driven government requires a scalable system that can ingest raw departmental data, ensure quality and transparency, and transform it into reliable insights for better governance, accountability, and citizen-centric decision-making.

## Project - Lakehouse for Government Data
To simulate this real-world governance challenge, I am building an end-to-end Lakehouse project using Medallion Architecture (Bronze, Silver, and Gold layers) with Apache Spark and PySpark. The system processes more than 10 lakh rows of raw scheme and beneficiary data through a scalable ETL pipeline. The Bronze layer ingests raw datasets from multiple sources, the Silver layer performs data cleaning, validation, schema enforcement, and transformation, and the Gold layer generates analytics-ready datasets that can support policy evaluation, fund tracking, and performance monitoring. This project strengthens my understanding of distributed data processing, scalable public data systems, and how modern data engineering can empower transparent, efficient, and data-driven governance.

## Government Identity Lakehouse Platform - Stage-wise Build Plan

### Project Vision
Build a government-grade platform with:
- Data Entry Application (official users submit/update records)
- ACID-compliant Data Platform (high-volume batch + streaming)
- Analytics Dashboard (state/district/national KPIs)
- Governance + Audit (security, lineage, traceability)

Architecture style:
- Medallion: Bronze -> Silver -> Gold
- Kappa: Stream-first processing, same logic for replay/backfill

## Stage 0: Problem Definition and Scope
### Objectives
- Unified trusted view of Enrollment, Demographic, Biometric data
- Real-time + historical analytics
- Production-quality data reliability
- Enable government data-driven scheme planning and policy decisions
- Build population-focused analytics for district/state-level planning
- Keep architecture extensible so new tables/domains can be added in future as needed

### Done (Current Progress)
- Project started with clear domain focus
- Grain and key understanding established

## Stage 1: EDA Foundation (Completed)
### Objectives
- Validate structure, grain, quality, consistency before pipeline design

### Done (Current Progress)
- Built and applied 14-step EDA framework
- Completed EDA flow for:
  - Enrollment
  - Demographic
  - Biometric
- Implemented checks for:
  - schema profiling
  - duplicates (full + key-level)
  - null/empty checks
  - date/pincode/type checks
  - domain checks
  - cardinality and cross-column consistency
  - outlier and trend checks
  - risk summary and documentation
- Created/recreated detailed README artifacts for cellwise learning and revision

## Stage 2: Data Contracts and Quality Rulebook (In Progress)
### Objectives
Define enforceable quality contracts for production.

### Rules
- Key: `(date, state, district, pincode)`
- Valid date parsing
- Pincode format (6 digits)
- Non-negative numeric measures
- Key duplicates = 0 in Silver

### Output
- Rulebook with severity (`high/medium/low`)
- Reject/quarantine policy
- Run-level quality score

## Stage 3: Bronze Layer (Raw Ingestion)
### Objectives
Ingest raw data safely with lineage and replay support.

### Build
- Batch ingest from source files
- Streaming ingest via Kafka/Event Hubs
- Store raw immutable records in Delta Bronze
- Add metadata: `source`, `event_ts`, `ingest_ts`, `topic`, `offset`, `batch_id`

### Output
- Append-only Bronze tables
- Ingestion audit table

## Bronze Layer Detailed Plan (Spark + Delta Only)

This section is the execution blueprint for Bronze implementation.
Focus is only Bronze, with Apache Spark + Delta Lake.

### Phase 1: Environment Setup
#### Concepts Used
- SparkSession
- Spark configuration
- Delta extensions
- Dependency management

#### Why This Matters
- Spark must be configured to run distributed jobs.
- Delta support must be enabled for ACID transactions.
- If setup is wrong, all downstream Bronze steps fail.

#### Outcome
- Spark starts successfully.
- Delta engine is active.
- You can create Delta tables.

### Phase 2: Project Structure
#### Concepts Used
- Data lake architecture
- Separation of concerns
- Layered storage design

#### Why This Matters
- Raw files, Bronze data, and checkpoints must stay isolated.
- Clean structure reduces data corruption and debugging effort.
- This is required for production-grade maintenance.

#### Outcome
- Clear folder hierarchy.
- Easy debugging and pipeline operations.
- Production-ready organization model.

### Phase 3: Reading Raw Data
#### Concepts Used
- DataFrame API
- File-based ingestion
- Explicit schema application
- Lazy evaluation

#### Why This Matters
- Spark reads raw CSV into distributed DataFrames.
- Lazy execution builds optimized plans before actual computation.
- Explicit schemas prevent drift and unexpected type errors.

#### Outcome
- Raw files converted to distributed DataFrames.
- Data is ready for Bronze transformations.
- Ingestion process is deterministic and scalable.

### Phase 4: Adding Metadata Columns
#### Concepts Used
- Column transformations
- Spark SQL functions
- Metadata enrichment
- Data lineage tracking

#### Why This Matters
- Bronze must capture ingestion context for auditing and replay.
- Required lineage fields: source file, ingest timestamp, batch id.
- Metadata enables root-cause analysis for bad loads.

#### Outcome
- Data becomes traceable.
- Bronze gets governance-ready metadata.
- Auditability is built into every load.

### Phase 5: Writing as Delta
#### Concepts Used
- Delta transaction log
- ACID guarantees
- Append/overwrite modes
- Distributed writes

#### Why This Matters
- Delta protects data from corruption and partial writes.
- ACID is mandatory for government-scale trust.
- Write mode discipline controls safe reruns.

#### Outcome
- Bronze Delta tables are physically created.
- ACID protection is active.
- Storage is scalable and replay-friendly.

### Phase 6: Register as SQL Table
#### Concepts Used
- Spark SQL
- Metastore/catalog registration
- Logical table abstraction

#### Why This Matters
- Consumers should query tables by name, not file paths.
- SQL access is essential for analysts and BI workflows.
- Catalog registration formalizes table governance.

#### Outcome
- Tables are queryable via SQL (`bronze.<table_name>`).
- Storage and query abstraction are decoupled.
- Lakehouse access is standardized.

### Phase 7: Partitioning
#### Concepts Used
- Physical partitioning
- Query pruning
- Performance optimization

#### Why This Matters
- Partitioning reduces scanned data for filtered queries.
- Better performance and lower compute cost at scale.
- Enables sustainable growth for high-volume pipelines.

#### Outcome
- Faster Bronze queries.
- Scalable storage layout.
- Better runtime efficiency.

#### Current Partition Strategy In This Repo
- Bronze/Silver fact-style tables partition by `partition_year`, `partition_month`
- `scheme_master_raw` and `scheme_master_raw_valid` partition by `active_flag`
- Keep partition count low enough to avoid many tiny files
- Keep `date` as the business filter column and derive partition columns from it

Example validation queries:

```python
spark.sql("DESCRIBE DETAIL bronze.demographic").select("partitionColumns", "numFiles", "sizeInBytes").show(truncate=False)
spark.sql("SELECT COUNT(*) FROM bronze.demographic WHERE date = DATE '2025-03-01'").show()
spark.sql("EXPLAIN SELECT * FROM bronze.demographic WHERE date = DATE '2025-03-01'").show(truncate=False)
```

### Phase 8: Re-runnability Design
#### Concepts Used
- Idempotent design patterns
- Replay-safe ingestion
- Controlled append strategy

#### Why This Matters
- Pipelines must recover from failures without manual cleanup.
- Reprocessing should not corrupt historical data.
- Reliable reruns are core production behavior.

#### Outcome
- Safe restart capability.
- Stable ingestion behavior under failures.
- Higher reliability in operations.

#### Phase 8 Completed In This Repo
- Bronze incremental CSV ingestion uses `append` by default
- Silver incremental Bronze-to-Silver processing uses `append` by default
- Pipeline supports targeted reruns by table for Bronze and Silver
- Each pipeline run prints and passes a `RunId`
- Bronze uses a file manifest to avoid loading the same incoming CSV file twice
- Silver uses a processed-batch control table to avoid processing the same Bronze batch twice

Example rerun commands:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables demographic
.\run_pipeline.ps1 -SilverTables demographic biometric
```

Validation signal:
- Running the same incremental command twice prints skip messages instead of duplicating data:
  - `[SKIP] No new CSV files for <table>`
  - `[SKIP] No new Bronze batches for <table>`

### Phase 9: Validation
#### Concepts Used
- Row-count verification
- Schema validation
- Metadata validation
- Delta read-back checks

#### Why This Matters
- Every load must be validated before promoting trust.
- Confirms data presence, schema correctness, and metadata completeness.
- Prevents silent failures entering Silver layer.

#### Outcome
- Verified Bronze correctness.
- Trusted ingestion layer.
- Ready handoff to Silver processing.

#### Phase 9 Implemented In This Repo
- Bronze validation is available as a runnable pipeline step
- Source CSV row counts are compared against Bronze Delta row counts
- Bronze schema is printed during validation
- Required metadata columns are validated:
  - `bronze_ingest_ts`
  - `bronze_source_file`
  - `bronze_batch_id`
- Delta read-back and `DESCRIBE DETAIL` are used to confirm table readability and metadata

Example validation command:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -RunBronzeValidation -SkipBronzeToSilver
```

Validate only selected Bronze tables:

```powershell
.\run_pipeline.ps1 -RunBronzeValidation -SkipBronzeToSilver -BronzeTables demographic enrolment
```

Validation passes when:
- source and Bronze row counts match
- Bronze metadata columns exist
- required Bronze metadata columns do not contain nulls
- Delta table can be read back successfully

### Bronze Final Deliverable
- Distributed raw storage in Delta format
- ACID-protected Bronze tables
- Metadata and lineage for every load
- Partitioned scalable design
- SQL-queryable Bronze catalog tables
- Replayable ingestion pattern

### Bronze Skills Learned
- Spark ingestion and DataFrame operations
- Schema management and transformations
- Delta Lake transactional storage
- Partition strategy and performance thinking
- SQL + catalog integration
- Governance and lineage foundations
- Production data engineering mindset

### Current Bronze Commands (This Repo)
Current incremental pipeline command:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables all
```

Run one Bronze table incrementally:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables demographic
```

Legacy synthetic loader is still available for older local tests:

```powershell
.\venv\Scripts\python.exe scripts/bronze_layer/sql_ingestion/build_bronze_synthetic.py --tables all --mode overwrite
```

## Current Incremental Loading Implementation

This repo now supports incremental CSV-to-Bronze and incremental Bronze-to-Silver processing.

### Raw Incoming CSV Area

Future CSV files are placed permanently under:

```text
data/upcoming_data/<table_name>/year=YYYY/month=MM/day=DD/<table_name>_YYYY_MM_DD.csv
```

The first folder under `data/upcoming_data` determines the Bronze table.

Example:

```text
data/upcoming_data/demographic/year=2026/month=05/day=21/demographic_2026_05_21.csv
```

This loads into:

```text
bronze.demographic
```

### Bronze Incremental Control

Bronze is append-only by default.

The Bronze loader reads only incoming CSV file paths that are not already present in:

```text
bronze_control.ingested_files
/app/scripts/bronze_layer/_control/ingested_files
```

Bronze row indicators:

```text
bronze_ingest_ts
bronze_source_file
bronze_batch_id
```

### Silver Incremental Control

Silver is append-only by default.

The Silver loader reads only Bronze rows whose `bronze_batch_id` is not already present in:

```text
silver_control.processed_bronze_batches
/app/scripts/silver_layer/_control/processed_bronze_batches
```

Silver row indicators:

```text
silver_processed_ts
silver_run_id
bronze_batch_id
```

### Main Incremental Commands

CSV to Bronze incremental only:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables all
```

CSV to Bronze incremental and Bronze to Silver incremental:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -BronzeTables all -SilverTables all
```

Bronze to Silver incremental only:

```powershell
.\run_pipeline.ps1 -SilverTables all
```

One table end-to-end:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -BronzeTables demographic -SilverTables demographic
```

Full Silver rebuild if needed:

```powershell
.\run_pipeline.ps1 -SilverTables all -SilverLoadType full -SilverMode overwrite
```

### Incremental Verification Queries

Check files loaded into Bronze:

```python
spark.sql("""
SELECT table_name, source_file_name, bronze_batch_id, row_count, status, bronze_ingest_ts
FROM bronze_control.ingested_files
ORDER BY bronze_ingest_ts DESC
""").show(truncate=False)
```

Check Bronze batches processed into Silver:

```python
spark.sql("""
SELECT table_name, bronze_batch_id, silver_run_id, input_rows, output_rows, status, processed_ts
FROM silver_control.processed_bronze_batches
ORDER BY processed_ts DESC
""").show(truncate=False)
```

The quick command reference is also available in:

```text
pipeline__button.txt
```

## Stage 4: Silver Layer (Clean, Trusted, Contract-Enforced Data)
### Purpose of the Silver Layer

The Silver layer transforms raw Bronze data into clean, standardized, and reliable datasets that can be safely used by downstream analytics systems.

This layer is responsible for data quality enforcement, schema normalization, deduplication, domain validation, metadata tracking, and operational reliability.

The goal is to ensure that all downstream consumers rely on trustworthy data.

### What the Silver Layer Must Achieve

The Silver layer must guarantee:

- Standardized schema
- Correct data types
- Valid domain values
- No duplicate keys
- No invalid records
- Traceable lineage
- Controlled incremental processing
- Late arriving data support
- Measurable data quality

### Silver Transformation Working Guide

For practical Silver transformation workflows in this repo, see:
- [SILVER_TRANSFORM_METHODS.md](/abs/path/c:/Users/Atul%20bhardwaj/Desktop/coding%202%20year/IdentityLakehouse/SILVER_TRANSFORM_METHODS.md)

This guide covers:
- Spark SQL script based Silver transforms
- PySpark script based Silver transforms
- quick `pyspark` checks and temporary changes
- recommended per-table transformation folders such as `population_transform`, `demographic_transform`, and similar dataset-specific workspaces
- how to use `silver_copy` and `*_valid_test` safely before touching trusted Silver outputs

### Current Silver Layer Focus

The active development focus is the Silver layer.

Current work is centered on schema normalization and repeatable PySpark-based standardization:

- Build a reusable SparkSession-based transformation flow.
- Read messy or inconsistent Bronze/Silver test inputs.
- Convert incoming schemas into expected Silver schemas.
- Standardize column names, column order, and data types.
- Fix naming issues such as raw symbols becoming unclear column names.
- Use `silver_copy` and `*_valid_test` tables for safe experimentation.
- Promote the logic to trusted `silver.*_valid` tables only after test validation passes.

Current Silver development examples:

- `silver_copy.enrolment_valid_test`
- `silver_copy.demographic_valid_test`
- `silver_copy.biometric_valid_test`
- `scripts/spark/biometric_transformation/standard_shema.py`

The goal is to avoid manual table edits and instead build one repeatable PySpark transformation step that can be rerun whenever new messy data arrives.

### Silver Layer Implementation Phases

Below are the phases you should implement, what you need to learn, and how to implement them conceptually.

### Phase 1: Bronze Data Loading
#### Concepts Used
- Spark DataFrame API
- Delta table reads
- Distributed dataset processing
- Lazy evaluation in Spark

#### Why This Matters
- Silver must always start from trusted Bronze snapshots, not from raw CSV files again.
- Reading Bronze Delta tables preserves lineage, metadata, and replay behavior already established in Bronze.
- This creates a clean layer boundary between ingestion and data quality transformation.

#### How to Implement
- Load Bronze tables from Delta paths or Bronze catalog tables.
- Treat Bronze as the only source of truth for Silver transformations.
- Read data at stable table grain before applying any quality or standardization logic.
- Keep a separate Silver test copy when you want to experiment without touching the main trusted Silver tables.
- In this repo, `scripts/spark/silver_to_test.py` copies `*_valid` tables into matching `*_valid_test` folders.
- The current test-copy design is an exact folder clone, not a Spark rewrite, so `_delta_log`, parquet files, and partition folders are preserved exactly.
- This means `demographic_valid` becomes `demographic_valid_test`, `enrolment_valid` becomes `enrolment_valid_test`, and so on.
- Use the main `*_valid` table as the source of truth and use `*_valid_test` only for safe testing or trial transforms.

#### Outcome
- Silver pipeline reads from consistent Bronze snapshots.
- The transformation layer starts from replay-safe Delta inputs.
- Layer separation is maintained properly.
- Test experimentation can happen on exact Silver copies without modifying production-style Silver outputs.

### Phase 2: Schema Normalization
#### Concepts Used
- Schema design principles
- Column selection and ordering
- Data modeling basics
- Schema drift handling

#### Why This Matters
- Bronze can preserve raw structure, but Silver must be predictable.
- A stable schema reduces downstream dashboard errors and broken joins.
- Normalization protects the project from source-side column drift and naming inconsistency.

#### How to Implement
- Define the expected Silver schema for each dataset.
- Standardize column names, order, and naming conventions.
- Remove unnecessary technical fields that do not belong in trusted analytical datasets.
- Keep only fields needed for quality control, joins, lineage, and downstream analytics.

#### Outcome
- Silver schemas become stable and predictable.
- Downstream consumers face fewer surprises.
- Join behavior and documentation become clearer.

#### Current Work In This Repo
- Expected Silver schemas are being checked for enrolment, demographic, and biometric datasets.
- Spark SQL `DESCRIBE` checks are being used to compare actual table schemas with expected Silver structure.
- Test tables in `silver_copy` are being used before changing trusted Silver outputs.
- Biometric schema normalization has identified a naming issue: `bio_age_17_` should be standardized to a clearer name such as `bio_age_17_plus` or `bio_age_18_plus`, depending on the source meaning.
- The next implementation step is to encode this schema mapping in PySpark so reruns automatically convert messy source columns into the expected Silver schema.

### Phase 3: Data Type Validation
#### Concepts Used
- Data type systems
- Schema enforcement
- Validation logic
- Bad-record detection

#### Why This Matters
- Analytics and joins fail when fields carry wrong data types.
- Type issues often appear silently in raw sources and can corrupt Silver metrics if unchecked.
- Validating before normalization makes bad records visible and auditable.

#### How to Implement
- Check whether dates can be parsed correctly.
- Validate numeric fields for numeric compatibility.
- Validate identifiers such as pincode and other key columns against expected formats.
- Separate invalid rows into quarantine instead of forcing them into trusted Silver datasets.

#### Outcome
- Invalid type records are identified explicitly.
- Silver valid datasets contain safer inputs for business logic.
- Type-related silent failures are reduced.

### Phase 4: Data Type Normalization
#### Concepts Used
- Schema casting
- Data transformation
- DataFrame column operations
- Canonical typing

#### Why This Matters
- Even valid values can remain inconsistent unless normalized into one canonical type.
- Gold and dashboards should not have to repeatedly interpret multiple date or number formats.
- Normalization improves join quality, partitioning, and metric consistency.

#### How to Implement
- Cast validated date fields to `date`.
- Cast numeric measures to `int` or `double` according to expected business meaning.
- Keep categorical attributes as standardized strings.
- Ensure the final Silver schema is the same on every rerun.

#### Outcome
- Silver datasets use consistent types across runs.
- Metrics and filters behave more reliably.
- Partitioning and downstream modeling become easier.

### Phase 5: Data Contract Enforcement
#### Concepts Used
- Data contracts
- Validation frameworks
- Business rule enforcement
- Trusted data publication

#### Why This Matters
- Silver is the first layer where data must be explicitly trusted.
- Contracts define what “good data” means for the project.
- Without contracts, Silver becomes only slightly cleaned Bronze instead of a reliable analytical layer.

#### How to Implement
- Define integrity rules for each dataset.
- Enforce key uniqueness expectations, non-negative measure rules, and identifier format rules.
- Treat contract violations as failed records and quarantine them with reasons.
- Keep the valid path and quarantine path clearly separated.

#### Outcome
- Silver validity becomes measurable.
- Business trust is tied to explicit rules, not assumptions.
- Promotion to Gold becomes easier to govern.

### Phase 6: Deduplication
#### Concepts Used
- Window functions
- Record prioritization strategies
- Dataset grain definition
- Deterministic record selection

#### Why This Matters
- Duplicate keys distort aggregations and create false KPI values.
- Silver must protect downstream layers from duplicate-grain records.
- Deduplication is only correct when the business grain is clearly defined first.

#### How to Implement
- Define the natural grain per dataset.
- Example grain for your core population-style datasets:
  - `(date, state, district, pincode)`
- Use deterministic selection logic, such as ordering by freshness or source priority.
- Keep only one surviving row per key and route duplicates into operational review if needed.

#### Outcome
- Silver valid tables are unique at intended grain.
- Downstream aggregations become more trustworthy.
- Duplicate-driven overcounting is reduced.

### Phase 7: Domain Validation
#### Concepts Used
- Domain constraints
- Categorical data validation
- Reference data validation
- Controlled vocabularies

#### Why This Matters
- Even correctly typed values can still be semantically wrong.
- Domain validation prevents polluted categories such as misspelled states or invalid districts.
- This is essential for consistent drill-down reporting.

#### How to Implement
- Validate categorical fields against expected domain values.
- Use reference mappings or approved value lists where available.
- Example checks:
  - valid state labels
  - valid district values
  - valid gender or type codes where relevant
- Send domain failures to quarantine for correction or mapping.

#### Outcome
- Silver dimensions and facts use cleaner business categories.
- Reporting consistency improves.
- Cross-table joins become more stable.

### Phase 8: Null Handling
#### Concepts Used
- Mandatory field rules
- Null handling strategies
- Completeness checks
- Data quality gating

#### Why This Matters
- Key columns with nulls break joins, deduplication, and KPI grouping.
- Silver should publish complete records for core analytical keys.
- Missing required values must be handled deliberately, not ignored.

#### How to Implement
- Define mandatory columns for each dataset.
- Example critical fields:
  - `date`
  - `state`
  - `district`
  - `pincode`
- Reject or quarantine rows missing mandatory values.
- Preserve nullability only where the business rules genuinely allow it.

#### Outcome
- Silver valid tables are more complete at business grain.
- Joins and aggregations fail less often.
- Data quality expectations become explicit.

### Phase 9: Derived Columns
#### Concepts Used
- Feature engineering basics
- Column transformations
- Derived attributes
- Analytical usability design

#### Why This Matters
- Downstream analytics repeatedly uses the same date and location breakdowns.
- Derived fields reduce repeated logic in Gold and BI tools.
- Silver should prepare trusted reusable attributes without turning into a business KPI layer.

#### How to Implement
- Add standardized derived attributes such as:
  - `year`
  - `month`
  - `month_start`
  - region grouping or state-level bucket fields if relevant
- Keep derivations reusable and broadly applicable.
- Avoid pushing final business KPI formulas into Silver.

#### Outcome
- Common analytical attributes are available early.
- Gold logic becomes simpler.
- Query usability improves.

### Phase 10: Late Arriving Data Handling
#### Concepts Used
- Event time vs processing time
- Watermarking
- Incremental reprocessing strategies
- Rolling correction windows

#### Why This Matters
- Source systems do not always deliver records in perfect event-time order.
- Late data can create missing days or incomplete trend results if Silver only processes the newest partition once.
- A controlled correction window increases trust without forcing full rebuilds every time.

#### How to Implement
- Distinguish event date from pipeline processing time.
- Use rolling reprocessing windows, such as last 7 days, for datasets subject to late arrival.
- Rebuild only affected partitions instead of full-table refresh where possible.
- Track which run updated each Silver record.

#### Outcome
- Late records are captured more reliably.
- Silver stays fresher without full reprocessing.
- Trend analysis becomes less fragile.

### Phase 11: Audit Columns and Data Freshness
#### Concepts Used
- Metadata tracking
- Operational monitoring
- Freshness measurement
- Run traceability

#### Why This Matters
- Trusted data still needs operational context.
- Freshness and run metadata help explain when and how a Silver record was produced.
- This is critical for debugging and handoff into Gold.

#### How to Implement
- Add audit columns such as:
  - Silver processed timestamp
  - pipeline run id
  - optional freshness indicator or source arrival metadata
- Ensure these fields are present on every valid Silver record.
- Use them for troubleshooting, reconciliation, and reporting freshness.

#### Outcome
- Silver becomes operationally traceable.
- Data freshness is measurable.
- Support and debugging become easier.

### Phase 12: Quarantine Dataset Management
#### Concepts Used
- Data governance
- Error classification
- Operational monitoring
- Invalid-record retention

#### Why This Matters
- Bad records should not disappear silently.
- Quarantine preserves the evidence needed for debugging, reporting, and correction.
- This creates accountability in data quality workflows.

#### How to Implement
- Store invalid rows in separate quarantine datasets.
- Include:
  - failure reason
  - failed rule name
  - source record context
  - pipeline run identifier
- Keep quarantine queryable for monitoring and remediation.

#### Outcome
- Data issues remain traceable.
- Valid Silver output stays clean.
- Quality operations become more manageable.

### Phase 13: Writing Silver Tables
#### Concepts Used
- Distributed write operations
- Partitioning strategies
- Delta Lake storage design
- Trusted output publishing

#### Why This Matters
- Silver outputs must be durable, queryable, and safe for repeated rebuilds.
- Write design affects downstream performance and operational stability.
- Delta is the right serving format for trusted intermediate analytics data.

#### How to Implement
- Write valid Silver datasets as Delta tables.
- Use partitioning aligned to common access patterns.
- Register Silver tables in the catalog where appropriate.
- Use write modes and schema controls that support safe reruns.

#### Outcome
- Silver valid tables are stored as reusable Delta assets.
- Storage is optimized for trusted intermediate consumption.
- Gold has clean, queryable inputs.

### Phase 14: Data Quality Metrics
#### Concepts Used
- Data observability
- Pipeline monitoring
- Quality scoring systems
- Operational reporting

#### Why This Matters
- Quality must be measured, not assumed.
- Metrics help you detect degradation early and explain pipeline behavior over time.
- This supports incident response and readiness for Gold promotion.

#### How to Implement
- Track metrics such as:
  - records processed
  - valid records
  - quarantined records
  - duplicates removed
  - failed rule counts
- Persist these metrics in a Silver quality summary dataset or run log.

#### Outcome
- Pipeline health becomes visible.
- Quality trends can be monitored over time.
- Promotion decisions become evidence-based.

### Phase 15: Incremental Processing
#### Concepts Used
- Incremental ingestion patterns
- Watermark tracking
- Batch processing strategies
- Controlled backfill logic

#### Why This Matters
- Reprocessing everything on every run becomes expensive as data grows.
- Silver should evolve toward incremental, operationally efficient behavior.
- Incremental logic reduces compute cost while preserving correctness.

#### How to Implement
- Use Bronze ingest metadata or event-time logic to isolate new or changed records.
- Reprocess only required windows or partitions.
- Combine incremental logic with late-arrival handling and rerun-safe write behavior.

#### Outcome
- Silver runs become more scalable.
- Compute efficiency improves.
- Operational runtime becomes more predictable.

### Phase 16: Validation and Reconciliation
#### Concepts Used
- Data reconciliation techniques
- Validation strategies
- Cross-layer verification
- End-to-end correctness checks

#### Why This Matters
- Silver should not silently lose records or misstate quality outcomes.
- Reconciliation is the proof that your transformation logic preserved control of every input row.
- This is the final trust checkpoint before Gold consumption.

#### How to Implement
- Reconcile Bronze input totals with Silver valid plus Silver quarantine totals.
- Validate key uniqueness, required metadata, and rule-level failure counts.
- Example concept:
  - `bronze_records = silver_valid_records + quarantined_records`
- Treat reconciliation mismatch as a failed pipeline condition.

#### Outcome
- Silver correctness becomes demonstrable.
- Trust handoff into Gold is stronger.
- Silent data loss is less likely.

### Skills You Will Develop in the Silver Layer

By completing this stage you will gain:

- Spark data transformation expertise
- Data quality engineering
- Schema enforcement practices
- Distributed data pipeline design
- Data governance and lineage tracking
- Incremental pipeline architecture
- Production-grade data engineering thinking

### Spark Concepts You Must Know

To successfully implement this layer you should understand:

- Core Concepts
- Spark DataFrame API
- Spark SQL
- Lazy evaluation
- Catalyst optimizer
- Transformation Concepts
- Filtering and transformation operations
- Column functions
- Aggregations
- Advanced Concepts
- Window functions
- Partitioning strategies
- Incremental processing
- Distributed writing

### Delta Lake Concepts to Learn

Important capabilities to understand:

- ACID transactions
- Delta transaction log
- Time travel
- Schema evolution
- Merge operations
- File optimization and compaction

### Final Result of the Silver Layer

The Silver layer produces:

Trusted datasets:

- silver.enrollment_valid
- silver.demographic_valid
- silver.biometric_valid

Error datasets:

- silver_quarantine.*

Operational metrics:

- silver_dq_summary

These datasets serve as the trusted foundation for the Gold layer analytics.

## Stage 5: Gold Layer (Business-ready Analytics)
### Objectives
Build decision-grade data models.

### Build
- Conformed dimensions: `dim_date`, `dim_location`
- Facts: enrollment/demographic/biometric facts
- Aggregates: district/state/month KPIs, trend/anomaly marts

### Output
- Dashboard-ready Gold tables/views

## Gold Layer Detailed Plan (Spark + Delta Only)

This section is the execution blueprint for Gold implementation.
Focus is only Gold, with Apache Spark + Delta Lake.

### Phase 1: Silver Data Loading
#### Concepts Used
- Spark DataFrame API
- Delta table reads
- Consistent snapshot access
- Lazy evaluation

#### Why This Matters
- Gold must consume only trusted Silver datasets.
- Reading directly from Silver preserves validated schema and quality controls.
- A stable Silver input is the foundation of reliable business metrics.

#### Outcome
- Gold pipeline reads standardized Silver tables.
- Gold logic starts from trusted data only.
- Input layer for analytics is stable.

### Phase 2: Business Grain Definition
#### Concepts Used
- Fact grain design
- Dimensional modeling
- Analytical data modeling
- Business metric scoping

#### Why This Matters
- Gold tables must represent clear business meaning.
- Without a fixed grain, KPI logic becomes inconsistent.
- Correct grain prevents double counting and broken dashboards.

#### Outcome
- Each Gold fact table has a defined grain.
- KPI calculations are consistent.
- Data models are dashboard-ready.

### Phase 3: Conformed Dimensions
#### Concepts Used
- Star schema modeling
- Conformed dimensions
- Surrogate key thinking
- Shared analytical dimensions

#### Why This Matters
- Multiple Gold facts should join to the same date and location dimensions.
- Conformed dimensions allow consistent slicing across all metrics.
- Shared dimensions reduce ambiguity in reporting.

#### Outcome
- `dim_date` can support day, month, quarter, year analysis.
- `dim_location` can support national, state, district, pincode drill-downs.
- All Gold facts use common dimensional logic.

### Phase 4: Fact Table Construction
#### Concepts Used
- Fact modeling
- Aggregation logic
- Metric engineering
- Joins across trusted datasets

#### Why This Matters
- Facts capture measurable business events and outcomes.
- They are the center of Gold analytics and KPI reporting.
- Well-built facts support trend analysis, comparisons, and dashboard performance.

#### Outcome
- Enrollment, demographic, and biometric Gold facts are built.
- Facts align with shared conformed dimensions.
- Business metrics become queryable at trusted grain.

### Phase 5: KPI Definition and Standardization
#### Concepts Used
- Business rules
- KPI semantics
- Derived metrics
- Standardized formulas

#### Why This Matters
- Dashboard trust depends on metric consistency.
- Different users must see the same KPI values for the same filters.
- Gold is where final business formulas should be standardized.

#### Outcome
- Reusable KPI formulas are defined once.
- Metrics such as totals, percentages, coverage, and trends are standardized.
- Dashboard logic is centralized in Gold instead of scattered across tools.

### Phase 6: Analytical Aggregates and Marts
#### Concepts Used
- Aggregation design
- Data marts
- Rollups
- Performance-oriented serving tables

#### Why This Matters
- Dashboards should not compute every aggregation from raw facts on demand.
- Gold marts improve response time and reduce repeated heavy computation.
- Pre-aggregated marts make district, state, and monthly reporting practical.

#### Outcome
- District-level KPI marts
- State-level summary marts
- Monthly trend marts
- Dashboard-ready aggregated datasets

### Phase 7: Business Rule Enrichment
#### Concepts Used
- Domain logic
- Derived classifications
- Analytical transformations
- Semantic enrichment

#### Why This Matters
- Gold should present business-friendly fields, not only technical columns.
- Enriched attributes make reporting easier for end users.
- This layer converts validated data into decision-grade information.

#### Outcome
- Derived labels, categories, and business segments are added.
- Analytical tables become easier to consume in BI tools.
- Domain semantics are embedded into Gold outputs.

### Phase 8: Time Intelligence and Trend Modeling
#### Concepts Used
- Time-series analysis
- Month-over-month logic
- Rolling windows
- Period comparison metrics

#### Why This Matters
- Most government analytics depend on change over time.
- Gold must support trend monitoring, performance comparisons, and anomaly tracking.
- Time intelligence improves strategic usefulness of the platform.

#### Outcome
- Month-over-month and period-based metrics are available.
- Trend marts support performance monitoring.
- Analytical history becomes easier to interpret.

### Phase 9: Data Quality Gating for Gold
#### Concepts Used
- Quality thresholds
- Promotion rules
- Trusted publishing controls
- Metric-level validation

#### Why This Matters
- Gold should publish only if Silver data is sufficiently trustworthy.
- Business dashboards should not consume broken or incomplete metrics.
- Quality gates prevent silent business reporting failures.

#### Outcome
- Gold publishing depends on validated Silver inputs.
- KPI tables are promoted only when checks pass.
- Business consumers receive more trustworthy data.

### Phase 10: Gold Metadata and Auditability
#### Concepts Used
- Audit columns
- Freshness tracking
- Lineage metadata
- Run traceability

#### Why This Matters
- Decision-grade analytics still need operational traceability.
- Gold outputs must show when they were generated and by which run.
- This helps debugging, trust, and stakeholder communication.

#### Outcome
- Gold tables include processing metadata.
- Data freshness and lineage remain visible.
- Gold publishing is auditable.

### Phase 11: Partitioning and Performance Design
#### Concepts Used
- Physical partitioning
- Query pruning
- Serving optimization
- Delta storage design

#### Why This Matters
- Gold tables serve dashboards and repeated filtered queries.
- Good partitioning improves dashboard latency and reduces scan cost.
- Performance design is necessary for scalable analytics serving.

#### Outcome
- Gold tables have serving-aware storage layout.
- Common filter paths are optimized.
- Dashboard queries become faster and more predictable.

### Phase 12: Re-runnability and Safe Rebuilds
#### Concepts Used
- Idempotent rebuild strategy
- Replay-safe Gold generation
- Controlled overwrite patterns
- Run-based traceability

#### Why This Matters
- Gold logic may need periodic full rebuilds from Silver.
- Rerunning Gold should not duplicate metrics or create conflicting KPI versions.
- Safe rebuild behavior is essential for production reliability.

#### Outcome
- Gold can be rebuilt safely from Silver.
- Repeated runs remain controlled and predictable.
- Historical trust is preserved during recovery and backfill.

### Phase 13: Validation and Reconciliation
#### Concepts Used
- Metric reconciliation
- Row-count sanity checks
- Business-rule validation
- Cross-layer consistency checks

#### Why This Matters
- Gold metrics must reconcile to Silver facts and aggregates.
- This prevents incorrect business reporting from going live.
- Reconciliation is the final trust checkpoint before dashboard consumption.

#### Outcome
- Gold metrics are validated against Silver-derived expectations.
- Aggregated outputs are trustworthy.
- Final publishing confidence is higher.

### Phase 14: Serving Layer Readiness
#### Concepts Used
- BI serving design
- Semantic readiness
- Consumer-friendly modeling
- Query interface design

#### Why This Matters
- Gold exists to serve dashboards, reports, and decision-making.
- Tables should be designed for business users, not only engineers.
- Good serving design reduces confusion in BI tools.

#### Outcome
- Gold tables and views are dashboard-ready.
- Business users can consume curated datasets with less transformation.
- Reporting layer integration becomes simpler.

### Skills You Will Develop in the Gold Layer

By completing this stage you will gain:

- Dimensional modeling expertise
- KPI engineering skills
- Business-rule-driven analytics design
- Aggregate and mart design thinking
- Gold-layer validation and reconciliation practices
- Dashboard-serving data modeling knowledge
- Decision-grade data engineering mindset

### Spark Concepts You Must Know

To successfully implement this layer you should understand:

- DataFrame joins
- aggregations and rollups
- window functions
- repartitioning and partition pruning
- writing optimized Delta datasets
- incremental rebuild strategies

### Delta Lake Concepts to Learn

Important capabilities to understand:

- ACID reliability for fact and aggregate tables
- overwrite vs append tradeoffs
- schema evolution
- partition-aware storage layout
- optimization and compaction concepts
- safe rerun and rebuild behavior

### Final Result of the Gold Layer

The Gold layer produces:

Conformed dimensions:

- gold.dim_date
- gold.dim_location

Business facts:

- gold.fact_enrollment
- gold.fact_demographic
- gold.fact_biometric

Analytical marts:

- gold.kpi_district_monthly
- gold.kpi_state_monthly
- gold.trend_anomaly_mart

Serving outputs:

- Dashboard-ready Gold tables/views
- Executive summary datasets
- State and district drill-down datasets
- Trusted inputs for Power BI and reporting tools

## Stage 6: Data Entry Platform (Operational System)
### Objectives
Allow secure government users to enter/update records.

### Build
- Role-based web app (operator, supervisor, admin)
- API + ACID operational DB (Azure SQL/Postgres)
- Server-side validations
- Workflow approvals

### Output
- Transaction-safe data capture platform

## Data Entry Platform Detailed Plan

This section is the execution blueprint for the operational data entry platform.
Focus is on secure transaction capture, validations, approvals, and controlled operational data updates.

### Phase 1: User Roles and Access Model
#### Concepts Used 
- Role-based access control
- Least privilege
- Operational workflow design
- Identity-aware application design

#### Why This Matters
- Government operational systems should not expose the same actions to every user.
- Role design protects data quality, approval flow, and auditability.
- The data entry layer must reflect real-world process ownership.

#### Outcome
- Clear role definitions such as operator, supervisor, and admin.
- Access boundaries are established before app development.
- Operational controls are aligned with platform trust requirements.

### Phase 2: Application Workflow Design
#### Concepts Used
- Process modeling
- Approval workflow
- State transitions
- User interaction flow

#### Why This Matters
- Data entry systems are not only forms; they are controlled business processes.
- Workflow design determines how submissions are reviewed, approved, rejected, and corrected.
- A weak workflow can create operational chaos even if storage is technically correct.

#### Outcome
- Submission lifecycle is clearly defined.
- Review and approval states are modeled explicitly.
- Platform behavior becomes predictable for users and operators.

### Phase 3: Transactional Database Design
#### Concepts Used
- OLTP modeling
- Normalized schema design
- Primary keys and foreign keys
- ACID transaction design

#### Why This Matters
- Operational data capture needs transaction safety, not just analytical storage.
- The application database must support inserts, updates, approvals, and status changes safely.
- A proper OLTP model protects correctness before data reaches Bronze.

#### Outcome
- Transaction-safe operational schema is defined.
- Core entities and relationships are normalized.
- Database supports reliable application behavior.

### Phase 4: API and Service Layer
#### Concepts Used
- REST or service-oriented design
- Input contracts
- Server-side validation
- Business service orchestration

#### Why This Matters
- Direct client-to-database writes are risky and hard to govern.
- APIs provide a control point for validation, auditing, and workflow logic.
- Service boundaries improve maintainability and testing.

#### Outcome
- Controlled API endpoints for data submission and review.
- Business validations execute server-side.
- Platform logic is centralized instead of being scattered across UI code.

### Phase 5: Frontend Data Entry Experience
#### Concepts Used
- Form design
- Validation UX
- Error handling
- Task-oriented interface design

#### Why This Matters
- Bad UI causes bad data, even with strong backend controls.
- Operators need clear forms, constraints, and error messages to work reliably.
- Good UX reduces training cost and operational mistakes.

#### Outcome
- Clean task-focused forms for users.
- Better validation feedback during entry.
- Lower error rate at source.

### Phase 6: Validation and Approval Rules
#### Concepts Used
- Rule enforcement
- Multi-step approvals
- Rejection handling
- Data quality prevention

#### Why This Matters
- It is better to prevent bad operational data than to clean it later.
- Approval controls provide governance before records enter analytical flows.
- Validation at this stage protects downstream Bronze and Silver quality.

#### Outcome
- Validation rules are enforced before data is accepted.
- Approval gates protect critical updates.
- Invalid or unapproved records are blocked or routed appropriately.

### Phase 7: Audit Logging and Traceability
#### Concepts Used
- Change tracking
- Audit logging
- Event history
- User action traceability

#### Why This Matters
- Government systems require accountability for who changed what and when.
- Operational corrections and disputes need historical evidence.
- Audit logs are essential for trust and compliance.

#### Outcome
- User actions are traceable.
- Change history is preserved.
- Support and compliance workflows become easier.

### Phase 8: Integration Into the Lakehouse
#### Concepts Used
- Operational-to-analytical data movement
- CDC thinking
- Bronze ingestion handoff
- Event-driven sync patterns

#### Why This Matters
- The entry platform should feed the analytical pipeline in a controlled way.
- Integration design determines how operational changes become Bronze events or snapshots.
- This is the bridge between OLTP and analytics.

#### Outcome
- Operational platform is connected to Bronze ingestion.
- Lakehouse and app boundaries remain clean.
- Future streaming or CDC integration becomes easier.

### Final Result of the Data Entry Platform

The platform produces:

- Secure role-based operational workflows
- Transaction-safe application database
- Controlled approvals and validations
- Audit-ready change history
- Clean handoff into Bronze ingestion


## Stage 7: Streaming (Kappa) Integration
### Objectives
Use one processing logic for real-time and replay.

### Build
- CDC/app events -> Kafka/Event Hubs
- Spark Structured Streaming -> Bronze -> Silver -> Gold
- Checkpointing, watermarking, idempotency

### Output
- Live data with replay capability

## Streaming Detailed Plan

This section is the execution blueprint for Kappa-style streaming integration.
Focus is on event flow, replay safety, checkpointing, and using the same processing logic for both live and historical data.

### Phase 1: Event Source Identification
#### Concepts Used
- Event-driven architecture
- CDC design
- Streaming source definition
- Domain event modeling

#### Why This Matters
- Streaming must begin with clear event producers and event meaning.
- If source semantics are unclear, replay and downstream trust will fail.
- Event design determines scalability and analytical usefulness.

#### Outcome
- Source systems for streaming are identified.
- Event meaning and ownership are defined.
- Input contracts for real-time ingestion are clearer.

### Phase 2: Topic and Schema Design
#### Concepts Used
- Topic modeling
- Event schema design
- Payload contracts
- Backward compatibility

#### Why This Matters
- Stable schemas are critical in streaming systems.
- Topic design affects scalability, replay, and downstream consumption patterns.
- A bad schema can break consumers continuously instead of only at batch time.

#### Outcome
- Events are organized into clean topic streams.
- Streaming payload structure is standardized.
- Producers and consumers can evolve more safely.

### Phase 3: Streaming Ingestion Into Bronze
#### Concepts Used
- Spark Structured Streaming
- Append mode ingestion
- Checkpointing
- Incremental writes

#### Why This Matters
- Bronze is the natural landing zone for raw event streams.
- Streaming writes must be durable and replay-safe.
- This phase creates the real-time entry point into the lakehouse.

#### Outcome
- Raw events land continuously in Bronze.
- Checkpoints preserve progress.
- Streaming and batch Bronze follow the same storage philosophy.

### Phase 4: Watermarking and Late Data Strategy
#### Concepts Used
- Event time
- Processing time
- Watermarks
- Late arrival handling

#### Why This Matters
- Real-world event systems do not deliver perfectly ordered data.
- Late events can corrupt aggregations if not handled explicitly.
- Watermarking provides a controlled balance between correctness and timeliness.

#### Outcome
- Late data rules are explicit.
- Streaming windows become more reliable.
- Event-time analytics become safer.

### Phase 5: Idempotency and Replay Safety
#### Concepts Used
- Exactly-once thinking
- Idempotent writes
- Replay-safe processing
- Deduplication by event identity

#### Why This Matters
- Streaming systems must survive restarts and replays without duplicating business events.
- Replay capability is one of the key reasons to choose a Kappa-style design.
- Trust in real-time analytics depends on deterministic recovery.

#### Outcome
- Duplicate event risk is reduced.
- Reprocessing becomes safer.
- Live and replay paths stay aligned.

### Phase 6: Streaming Silver and Gold Promotion
#### Concepts Used
- Incremental transformation
- Streaming-quality enforcement
- Stateful processing
- Near-real-time serving

#### Why This Matters
- Streaming Bronze alone is not enough; business value appears when trusted Silver and Gold outputs update continuously.
- Quality logic must remain consistent across batch and streaming paths.
- This is where real-time lakehouse value becomes visible.

#### Outcome
- Silver and Gold can evolve toward near-real-time behavior.
- Same business logic can support both live and historical processing.
- Dashboard freshness improves.

### Final Result of Streaming Integration

The streaming layer produces:

- Event ingestion into Bronze
- Replay-safe checkpointed processing
- Controlled late data handling
- Real-time path for Bronze -> Silver -> Gold


## Stage 8: Dashboard and Reporting Layer
### Objectives
Provide actionable government insights.

### Build
- Power BI dashboards:
  - national overview
  - state performance
  - district drill-down
  - data quality health
- Scheduled reports + filters + exports

### Output
- Executive and operational dashboards

## Dashboard and Reporting Detailed Plan

This section is the execution blueprint for the BI and reporting layer.
Focus is on turning Gold data into usable insight products for executive, analytical, and operational users.

### Phase 1: Audience and Use-case Definition
#### Concepts Used
- Stakeholder mapping
- Decision-support design
- Analytical personas
- Dashboard objective setting

#### Why This Matters
- Different users need different questions answered.
- A dashboard without a clear audience becomes cluttered and low-trust.
- Executive and operational reporting should not use the same layout blindly.

#### Outcome
- Dashboard user groups are clearly defined.
- Each dashboard has a decision purpose.
- Reporting design becomes more focused.

### Phase 2: KPI Selection and Semantic Alignment
#### Concepts Used
- KPI governance
- Semantic consistency
- Gold-to-BI mapping
- Metric catalog thinking

#### Why This Matters
- BI tools should not redefine business metrics independently.
- Dashboard trust depends on using the same KPI definitions as Gold.
- Metric ambiguity creates reporting conflict.

#### Outcome
- KPI list is standardized.
- Dashboard measures align with Gold logic.
- Report consumers see more consistent numbers.

### Phase 3: Semantic Model Design
#### Concepts Used
- Star schema consumption
- BI semantic modeling
- Relationships and measures
- Dimensional navigation

#### Why This Matters
- BI tools perform best when fed a clean semantic structure.
- Proper relationships between Gold facts and dimensions reduce dashboard confusion.
- A semantic model is the bridge between engineering outputs and user consumption.

#### Outcome
- Fact and dimension relationships are defined for BI.
- Measures and filters behave more predictably.
- Dashboard development becomes easier.

### Phase 4: Executive Dashboard Design
#### Concepts Used
- Summary KPI design
- High-level storytelling
- Strategic visualization
- Monitoring-first layout

#### Why This Matters
- Leaders need fast understanding, not raw data exploration.
- Executive dashboards should focus on trends, risks, and high-level performance.
- Clear strategic views improve decision speed.

#### Outcome
- National and state overview dashboards.
- High-level KPI cards and trend views.
- More actionable executive reporting.

### Phase 5: Operational Dashboard Design
#### Concepts Used
- Drill-down analytics
- Exception monitoring
- Operational reporting
- Detail-level slicing

#### Why This Matters
- Operational teams need to investigate issues, not just view summaries.
- District-level drill-down and anomaly views are critical for actionability.
- Detailed reporting turns analytics into operations.

#### Outcome
- District drill-down dashboards.
- Data quality health views.
- Investigation-ready reporting surfaces.

### Phase 6: Filters, Exports, and Scheduled Reports
#### Concepts Used
- Self-service reporting
- Report parameterization
- Export workflows
- Scheduling and subscriptions

#### Why This Matters
- Users often need filtered extracts and recurring reports, not only live dashboards.
- Scheduling supports regular decision cycles.
- Exports increase operational usefulness.

#### Outcome
- Filterable dashboards and reports.
- Export-ready analytical views.
- Scheduled report delivery.

### Final Result of the Dashboard Layer

The reporting layer produces:

- Executive dashboards
- Operational drill-down reports
- Data quality reporting views
- Scheduled and exportable insight products

## Stage 9: Security, Governance, Compliance
### Objectives
Government-grade trust and control.

### Build
- RBAC, managed identity, Key Vault
- Row/column access controls
- Lineage/catalog (Purview/Unity Catalog)
- Audit logs and retention

### Output
- Compliant and auditable platform

## Stage 10: Reliability, Scale, Performance
### Objectives
Handle high-volume loads reliably.

### Build
- Partitioning strategy and Delta optimization
- Autoscaling and job tuning
- Cost monitoring
- DR strategy (backup/failover)

### Output
- Production stability at scale

## Stage 11: CI/CD and Testing
### Objectives
Safe, repeatable delivery.

### Build
- Unit + integration + data tests
- CI/CD (`dev -> qa -> prod`)
- Automated quality gates

### Output
- Controlled release pipeline

## CI/CD and Testing Detailed Plan

This section is the execution blueprint for delivery automation and engineering quality control.
Focus is on keeping code, data logic, and deployment changes safe and repeatable.

### Phase 1: Repository Standards and Branch Strategy
#### Concepts Used
- Git workflow
- Branching strategy
- Pull request discipline
- Change review controls

#### Why This Matters
- Stable delivery starts with predictable source control behavior.
- Branch strategy affects release quality and team coordination.
- PR discipline reduces risky direct changes.

#### Outcome
- Clear branch flow such as dev -> qa -> prod.
- Review process is standardized.
- Release coordination becomes easier.

### Phase 2: Automated Code Quality Checks
#### Concepts Used
- Linting
- Static analysis
- Formatting
- Early failure detection

#### Why This Matters
- Quality issues are cheaper to catch before runtime.
- Code standards improve maintainability and reduce review overhead.
- Automated checks create consistent engineering hygiene.

#### Outcome
- Basic code quality is enforced automatically.
- Merge quality improves.
- Manual review can focus on higher-value issues.

### Phase 3: Unit and Integration Tests
#### Concepts Used
- Test design
- Dependency isolation
- Integration coverage
- Regression prevention

#### Why This Matters
- Data pipeline logic changes can silently break production behavior.
- Unit tests protect transformation functions.
- Integration tests protect end-to-end pipeline flow.

#### Outcome
- Pipeline logic has repeatable test coverage.
- Refactors become safer.
- Regression risk is reduced.

### Phase 4: Data Quality Tests in CI
#### Concepts Used
- Data assertions
- Contract checks
- Quality gates
- Pipeline validation automation

#### Why This Matters
- Data systems need data tests, not only code tests.
- CI should block releases that break key data assumptions.
- This extends Bronze/Silver/Gold trust into the delivery pipeline.

#### Outcome
- Data contracts are enforced automatically.
- Bad changes are caught before release.
- Release confidence increases.

### Phase 5: Deployment Automation
#### Concepts Used
- CI/CD workflows
- Environment promotion
- Release automation
- Infrastructure-aware delivery

#### Why This Matters
- Manual deployment is slow, inconsistent, and risky.
- Automation keeps environments aligned.
- Reliable delivery is essential for an evolving analytics platform.

#### Outcome
- Deployments become repeatable.
- Environment drift is reduced.
- Release speed and safety improve.

### Final Result of CI/CD and Testing

This stage produces:

- Repeatable release process
- Automated quality gates
- Safer code and data pipeline changes
- Controlled promotion from dev to qa to prod

## Stage 12: Go-Live and Operations
### Objectives
Run as a real production service.

### Build
- Pilot launch -> phased rollout
- SLA monitoring and alerts
- Incident runbook and support model

### Output
- Fully operational government analytics platform

## Go-Live and Operations Detailed Plan

This section is the execution blueprint for moving the platform from build mode to production operation.
Focus is on rollout control, support readiness, monitoring, and service reliability.

### Phase 1: Production Readiness Review
#### Concepts Used
- Readiness assessment
- Release gating
- Operational acceptance
- Risk review

#### Why This Matters
- Going live too early creates avoidable operational incidents.
- A readiness review ensures technical, security, and support foundations exist.
- Production trust must be earned before rollout.

#### Outcome
- Go-live criteria are explicit.
- Risks are reviewed before launch.
- Production release becomes more controlled.

### Phase 2: Pilot Launch
#### Concepts Used
- Limited rollout
- Change risk reduction
- Early production feedback
- Controlled adoption

#### Why This Matters
- Pilots reduce blast radius.
- Early usage reveals issues that testing may miss.
- Controlled rollout protects stakeholder trust.

#### Outcome
- Initial production usage begins safely.
- Feedback is collected early.
- Operational issues can be corrected before broad rollout.

### Phase 3: Monitoring, Alerts, and SLA Tracking
#### Concepts Used
- Service monitoring
- Alerting strategy
- SLA/SLO thinking
- Operational observability

#### Why This Matters
- A live analytics platform needs continuous visibility.
- Teams must know quickly when data freshness, jobs, or dashboards fail.
- Monitoring turns the platform into a managed service instead of a one-time project.

#### Outcome
- Alerts are configured for critical failures.
- Freshness and job health are monitored.
- Operational reliability becomes measurable.

### Phase 4: Incident Runbooks and Support Model
#### Concepts Used
- Incident response
- Operational runbooks
- Escalation paths
- Support ownership

#### Why This Matters
- Production systems need recovery procedures before incidents happen.
- Runbooks reduce downtime and confusion during failures.
- Support ownership is necessary for stable operations.

#### Outcome
- Common failure scenarios have documented response steps.
- Support responsibilities are assigned.
- Recovery becomes faster and more repeatable.

### Phase 5: Phased Rollout and Continuous Improvement
#### Concepts Used
- Controlled scaling
- Feedback loops
- Post-launch optimization
- Service maturity growth

#### Why This Matters
- Production maturity improves through iteration, not one launch event.
- Feedback from real users should guide platform hardening.
- Phased growth is safer than immediate full-scale exposure.

#### Outcome
- Rollout expands gradually and safely.
- Platform quality improves after launch.
- Service operations become more mature over time.

### Final Result of Go-Live and Operations

This stage produces:

- Production-ready launch criteria
- Controlled rollout plan
- Monitoring and alerting framework
- Incident response readiness
- A fully operational analytics service

## Stage 13: Cloud Migration and Productionization Plan
### Objectives
Move the locally validated Identity Lakehouse into a cloud-ready architecture after the core pipeline logic is stable.

The intent is to first prove the Spark, Delta Lake, Medallion, validation, and rerun logic locally, then migrate the tested design to cloud services for scale, orchestration, governance, monitoring, and dashboard consumption.

### Why Local First, Cloud Later
- Local development gives faster iteration while building the core PySpark transformation logic.
- It separates data pipeline correctness from cloud infrastructure complexity.
- It reduces cost while the Bronze, Silver, and Gold logic is still changing.
- Once the pipeline is stable, cloud migration becomes a controlled productionization step instead of experimental debugging.
- This approach helps demonstrate both skills: building a working data pipeline and migrating it toward a production cloud lakehouse.

Interview explanation:

```text
I intentionally followed a local-to-cloud approach. First, I validated the pipeline logic locally using PySpark and Delta Lake: ingestion, schema normalization, data quality rules, partitioning, and rerun safety. After that, I designed the cloud migration so the same lakehouse pattern could be productionized with cloud storage, managed Spark, orchestration, governance, monitoring, and BI reporting.
```

### Recommended Cloud Target: Azure
Azure fits this project well because the lakehouse can map cleanly to ADLS Gen2, Databricks, Power BI, Purview, and Azure Monitor.

Cloud architecture:

```text
Source files / operational systems
        ↓
Azure Data Lake Storage Gen2 - raw zone
        ↓
Azure Databricks / Spark
        ↓
Delta Bronze tables
        ↓
Delta Silver tables
        ↓
Delta Gold tables
        ↓
Power BI dashboards
        ↓
Purview governance + Azure Monitor observability
```

### Local-to-Cloud Component Mapping

| Local Component | Cloud Component |
|---|---|
| Local `data/` folder | Azure Data Lake Storage Gen2 raw container/path |
| Local Bronze Delta folders | ADLS Gen2 Bronze Delta path |
| Local Silver Delta folders | ADLS Gen2 Silver Delta path |
| Local Gold Delta folders | ADLS Gen2 Gold Delta path |
| Local PySpark scripts | Azure Databricks notebooks or Databricks jobs |
| `run_pipeline.ps1` | Databricks Workflows or Azure Data Factory pipeline |
| Local Hive/Derby metastore | Databricks Unity Catalog or managed Hive metastore |
| Local validation commands | Automated validation jobs |
| Local logs/console output | Azure Monitor and Log Analytics |
| Manual secrets/config | Azure Key Vault |
| Gold query outputs | Power BI semantic model and reports |

### Proposed Cloud Storage Layout

```text
abfss://identity-lakehouse@<storage-account>.dfs.core.windows.net/
    raw/
        enrolment/
        demographic/
        biometric/
    bronze/
        enrolment/
        demographic/
        biometric/
    silver/
        enrolment_valid/
        demographic_valid/
        biometric_valid/
    gold/
        dim_date/
        dim_location/
        fact_enrolment/
        fact_demographic/
        fact_biometric/
        kpi_identity_coverage_daily/
    checkpoints/
    audit/
```

### Cloud Implementation Phases

#### Phase 1: Local Completion Gate
- Bronze ingestion and validation must pass locally.
- Silver schema normalization and quality rules must pass locally.
- Basic Gold facts, dimensions, and KPI outputs should exist.
- Pipeline rerun behavior must be predictable.
- Paths should be configurable so local paths can later be replaced with cloud paths.

#### Phase 2: Cloud Storage Setup
- Create ADLS Gen2 storage account.
- Create raw, bronze, silver, gold, checkpoints, and audit zones.
- Upload sample raw data to the cloud raw zone.
- Define folder and table naming conventions.

#### Phase 3: Managed Spark Setup
- Create Azure Databricks workspace.
- Configure cluster/runtime with Delta Lake support.
- Connect Databricks to ADLS Gen2 using service principal, managed identity, or workspace identity.
- Store credentials and connection values in Azure Key Vault or Databricks secrets.

#### Phase 4: Code Migration
- Move PySpark scripts into Databricks jobs or notebooks.
- Replace hardcoded local paths with configurable base paths.
- Use the same Bronze, Silver, and Gold transformation logic where possible.
- Keep local and cloud configs separate.

Example config direction:

```json
{
  "environment": "azure",
  "raw_base_path": "abfss://identity-lakehouse@<storage-account>.dfs.core.windows.net/raw",
  "bronze_base_path": "abfss://identity-lakehouse@<storage-account>.dfs.core.windows.net/bronze",
  "silver_base_path": "abfss://identity-lakehouse@<storage-account>.dfs.core.windows.net/silver",
  "gold_base_path": "abfss://identity-lakehouse@<storage-account>.dfs.core.windows.net/gold"
}
```

#### Phase 5: Orchestration
- Convert local script execution into Databricks Workflows or Azure Data Factory pipelines.
- Run Bronze, validation, Silver, validation, Gold, and dashboard refresh steps in order.
- Support table-level reruns for recovery.
- Add job parameters for environment, table list, mode, and run id.

#### Phase 6: Governance and Security
- Use Unity Catalog or Microsoft Purview for cataloging, ownership, lineage, and discovery.
- Apply role-based access to raw, Bronze, Silver, and Gold zones.
- Restrict sensitive columns where needed.
- Keep audit metadata and run history queryable.

#### Phase 7: Monitoring and Operations
- Track job success/failure, runtime, row counts, and data freshness.
- Send alerts for failed jobs or invalid quality checks.
- Store operational logs in Azure Monitor or Log Analytics.
- Convert manual runbooks into repeatable operational procedures.

#### Phase 8: Reporting
- Connect Power BI to Gold tables or semantic model outputs.
- Build dashboards for state, district, scheme, enrolment, demographic, biometric, and identity coverage KPIs.
- Validate dashboard numbers against Gold SQL queries.

### Cloud Acceptance Checklist
- Local Bronze, Silver, and Gold pipeline is stable before migration.
- Cloud paths are configurable and not hardcoded.
- Raw data can be loaded from ADLS Gen2.
- Databricks can write Delta tables to Bronze, Silver, and Gold zones.
- Cloud jobs can run in the correct dependency order.
- Validation checks run after each major layer.
- Gold tables are consumable by Power BI or another BI layer.
- Governance, access, and monitoring approach is documented.

### Final Result of Cloud Migration

This stage produces:

- A cloud-ready Identity Lakehouse architecture
- Configurable local and cloud execution design
- ADLS Gen2-based lake storage plan
- Databricks/Spark production compute plan
- Orchestrated Bronze, Silver, and Gold pipeline design
- BI, governance, and monitoring roadmap

## Current Status Summary
- EDA foundation: Completed
- 14-step framework implementation: Completed
- Enrollment/Demographic/Biometric profiling: Completed
- Documentation artifacts: Completed
- Bronze ingestion and validation: Implemented
- Bronze incremental CSV loading: Implemented using `data/upcoming_data` and `bronze_control.ingested_files`
- Silver incremental Bronze-to-Silver loading: Implemented using `silver_control.processed_bronze_batches`
- Silver layer: Active development phase
- Current Silver focus: schema normalization, data type checking, column naming standardization, reusable PySpark transformation flow, and future quality/quarantine rules
- Gold layer: Planned after Silver layer stabilizes
- Cloud migration architecture: Planned and documented as a post-local-completion productionization phase

## Appendix A: Stage-by-Stage Acceptance Checklist

Use this checklist to decide whether a stage is conceptually complete, operationally stable, and ready to hand off to the next stage.

### Stage 2: Raw Data Modeling and Contracts
- Grain of every source table is clearly defined.
- Required business columns are documented.
- Expected data types are documented.
- Known quality problems are listed.
- Source-to-target understanding exists before pipeline coding.

### Stage 3: Bronze Layer
- Raw files are ingested successfully into Delta.
- Bronze tables are queryable by name.
- Metadata columns are present for lineage.
- Partitioning strategy is applied and validated.
- Incremental file loading is controlled by `bronze_control.ingested_files`.
- Rerun behavior is controlled and documented.
- Bronze validation checks pass.

### Stage 4: Silver Layer
- Bronze-to-Silver incremental flow exists and is being refined.
- Processed Bronze batches are tracked in `silver_control.processed_bronze_batches`.
- Silver test database/table workflow exists through `silver_copy` and `*_valid_test` tables.
- Schema normalization is the current active work.
- Expected columns, column order, and data types are being validated table by table.
- Cleaning, null handling, deduplication, quarantine, and full quality metrics still need to be completed before Silver is fully accepted.

### Stage 5: Gold Layer
- Business grain is defined for each mart.
- Dimensions are conformed across use cases.
- Fact tables reference dimensions consistently.
- KPI definitions are documented.
- Gold outputs are ready for dashboards and policy analysis.

### Stage 6: Data Entry Platform
- Users can submit records through controlled workflows.
- Input validation happens before data is accepted.
- Audit fields are captured for every write event.
- Authentication and authorization are enforced.
- Operational system data can flow safely into Bronze.

### Stage 7: Streaming Integration
- Streaming source and schema are defined.
- Checkpointing and recovery strategy are configured.
- Replay and backfill approach is documented.
- Streaming data can be reconciled with batch history.
- Failure handling is deterministic and testable.

### Stage 8: Dashboard and Reporting
- Core KPIs are agreed with business meaning.
- Dashboard datasets come from Gold, not ad hoc tables.
- Filters and drill-down paths are defined.
- Refresh expectations are documented.
- Visual outputs are validated against known numbers.

### Stage 9: Security and Governance
- Access model is defined by role.
- Sensitive columns are identified.
- Auditability exists across ingestion and reporting.
- Data ownership is documented.
- Governance controls are aligned with actual usage.

### Stage 10: Platform Hardening
- Backup and recovery path is understood.
- Performance bottlenecks are identified.
- Storage and compute expectations are documented.
- Failure scenarios are known and recoverable.
- Monitoring strategy exists for critical pipelines.

### Stage 11: CI/CD and Testing
- Critical scripts are testable.
- Validation and quality checks can be automated.
- Deployment and release steps are repeatable.
- Documentation is updated as part of delivery.
- Changes can be promoted safely with confidence.

### Stage 12: Go-Live and Operations
- Support ownership is assigned.
- Incident runbooks are available.
- SLA and alert expectations are defined.
- Pilot rollout plan exists.
- Production readiness review is completed.

### Stage 13: Cloud Migration and Productionization
- Local pipeline completion gate is defined.
- Cloud storage, compute, orchestration, BI, governance, and monitoring mapping is documented.
- ADLS Gen2 storage layout is planned.
- Databricks migration approach is defined.
- Local-to-cloud path configuration strategy is documented.
- Cloud acceptance checklist exists.

## Appendix B: Bronze, Silver, Gold Comparison

This section helps distinguish the purpose of each lakehouse layer in practical terms.

### Bronze
- Purpose: capture raw source truth with minimal business interpretation.
- Data shape: close to source system structure.
- Main focus: ingestion reliability, lineage, replay safety, ACID storage.
- Typical users: data engineers, platform maintainers.
- Typical questions answered:
- Did the file arrive?
- How many rows were loaded?
- Can the load be replayed safely?
- Where did this row come from?

### Silver
- Purpose: create standardized, validated, and trustworthy datasets.
- Data shape: cleaned and business-safe.
- Main focus: quality rules, standardization, schema discipline, conformance.
- Typical users: data engineers, analysts, transformation developers.
- Typical questions answered:
- Is the data valid?
- Are columns standardized?
- Can this dataset be safely joined?
- Are quality issues isolated before analytics?

### Gold
- Purpose: present business-ready facts, dimensions, and KPIs.
- Data shape: star-schema-style or dashboard-oriented marts.
- Main focus: semantic modeling, KPI logic, consumption performance.
- Typical users: analysts, BI developers, stakeholders, policy teams.
- Typical questions answered:
- How is enrollment trending over time?
- Which districts lag in linkage?
- What is the biometric coverage by state?
- Which schemes show beneficiary anomalies?

## Appendix C: Validation Command Reference

These commands are useful during development, demonstrations, and interviews.

### Bronze Metadata Validation
```python
spark.sql("SHOW TABLES IN bronze").show(truncate=False)
spark.sql("DESCRIBE DETAIL bronze.demographic").select("partitionColumns", "numFiles", "sizeInBytes").show(truncate=False)
spark.sql("SELECT COUNT(*) FROM bronze.demographic").show()
spark.sql("SELECT COUNT(*) FROM bronze.demographic WHERE bronze_ingest_ts IS NULL").show()
spark.sql("SELECT COUNT(*) FROM bronze.demographic WHERE bronze_source_file IS NULL").show()
spark.sql("SELECT COUNT(*) FROM bronze.demographic WHERE bronze_batch_id IS NULL").show()
```

### Silver Quality Validation
```python
spark.sql("SHOW TABLES IN silver").show(truncate=False)
spark.sql("DESCRIBE DETAIL silver.demographic_valid").select("partitionColumns", "numFiles", "sizeInBytes").show(truncate=False)
spark.sql("SELECT COUNT(*) FROM silver.demographic_valid").show()
spark.sql("SELECT COUNT(*) FROM silver.demographic_valid WHERE date IS NULL").show()
```

### Gold Validation
```python
spark.sql("SHOW TABLES IN gold").show(truncate=False)
spark.sql("SELECT * FROM gold.dim_date LIMIT 10").show(truncate=False)
spark.sql("SELECT * FROM gold.dim_location LIMIT 10").show(truncate=False)
spark.sql("SELECT * FROM gold.fact_demographic LIMIT 10").show(truncate=False)
```

### Partition Pruning Validation
```python
spark.sql("EXPLAIN FORMATTED SELECT * FROM bronze.demographic WHERE date = DATE '2025-03-01'").show(truncate=False)
spark.sql("EXPLAIN FORMATTED SELECT * FROM silver.enrolment_valid WHERE date = DATE '2025-03-01'").show(truncate=False)
spark.sql("DESCRIBE DETAIL bronze.demographic").select("partitionColumns").show(truncate=False)
```

### Re-runnability Validation
```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables demographic -BronzeMode overwrite
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables demographic -BronzeMode overwrite
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeMode append
```

## Appendix D: Interview Explanation Bank

Use these short explanations when you need to describe the project quickly.

### Explain the Project in 30 Seconds
This project is a government-style lakehouse built on Spark and Delta Lake using Medallion Architecture. Bronze stores raw departmental data with lineage and replay safety, Silver applies cleaning and validation, and Gold is designed for KPI-ready analytics and dashboard consumption.

### Explain Why Delta Lake Was Chosen
Delta Lake adds ACID transactions, schema handling, and reliable read/write behavior on top of file-based storage. That makes it appropriate for repeatable ingestion, partitioned storage, validation, and production-style data engineering workflows.

### Explain Why Bronze Needs Metadata
Bronze must remain auditable. Metadata like source file, ingest timestamp, and batch identifier helps trace every row back to its load event, which is important for debugging, governance, and replay safety.

### Explain Why Silver Exists
Silver separates raw storage from trusted business-ready data. It is the place where data is standardized, validated, and shaped into something safe for joins, analytics, and downstream modeling.

### Explain Why Gold Uses Dimensions and Facts
Gold focuses on analytics consumption. Facts store measurable events and dimensions provide conformed descriptive context. This improves KPI consistency, BI usability, and dashboard performance.

### Explain Why Partitioning Was Added
Partitioning reduces unnecessary data scans by organizing storage around high-value filter columns like date. That improves query performance and makes the storage layout more scalable as data volume grows.

### Explain Why Re-runnability Matters
Production pipelines fail sometimes. A rerunnable design ensures the system can recover safely without manual cleanup and without creating duplicated or corrupted history.

## Appendix E: Example Production Runbooks

These are sample operational playbooks that can later be converted into formal runbooks.

### Runbook 1: Bronze Load Failed
1. Confirm which table failed and capture the run id.
2. Check whether the source file path is available.
3. Review the Spark application log for the failing stage.
4. Confirm whether partial Delta output was committed or rolled back.
5. Rerun only the affected table in overwrite mode.
6. Re-run Bronze validation for that table.
7. If successful, resume downstream Silver processing.

### Runbook 2: Silver Validation Failed
1. Identify which rule failed and on which table.
2. Compare Silver output count to Bronze input count.
3. Inspect null, schema, and parsing issues.
4. Check whether a recent source schema or format changed.
5. Correct transformation logic or quarantine logic as needed.
6. Rerun only the affected Silver table.
7. Re-check counts and quality metrics before promotion.

### Runbook 3: Dashboard KPI Mismatch
1. Identify the metric definition in the Gold layer.
2. Confirm the dashboard query is using the correct Gold table.
3. Check whether the latest Gold refresh completed.
4. Validate the KPI directly in Spark SQL.
5. Compare dashboard result to direct query output.
6. If mismatch remains, inspect semantic model joins and filters.
7. Publish a corrected KPI note or dashboard fix.

### Runbook 4: Partitioning Appears Incorrect
1. Run `DESCRIBE DETAIL` on the table.
2. Confirm the expected `partitionColumns`.
3. Check whether the latest write actually rewrote the table.
4. Validate filtered queries using `EXPLAIN FORMATTED`.
5. Confirm the partition column is not null-heavy.
6. If needed, rerun the table with the corrected partition normalization logic.

## Appendix F: Gold Layer Candidate Outputs for This Domain

These are realistic Gold outputs that fit the identity and government-benefit theme of this project.

### Core Dimensions
- `gold.dim_date`
- `gold.dim_location`
- `gold.dim_scheme`
- `gold.dim_data_source`

### Core Facts
- `gold.fact_demographic`
- `gold.fact_enrolment`
- `gold.fact_biometric`
- `gold.fact_aadhaar_voter_linkage`
- `gold.fact_scheme_beneficiary`
- `gold.fact_district_scheme_payment`

### KPI Marts
- `gold.kpi_identity_coverage_daily`
- `gold.kpi_biometric_authentication_daily`
- `gold.kpi_scheme_distribution_monthly`
- `gold.kpi_linkage_quality_statewise`
- `gold.kpi_enrolment_vs_population_gap`

### Executive Views
- `gold.executive_state_summary`
- `gold.executive_district_summary`
- `gold.executive_scheme_performance`
- `gold.executive_identity_risk_view`

## Appendix G: What Still Needs Implementation After Documentation

This README now contains detailed design guidance, but some later-stage items remain future implementation work.

### Already Implemented in Code
- Bronze ingestion
- Bronze metadata
- Bronze partitioning
- Bronze rerunnability controls
- Bronze validation
- Bronze-to-Silver transformation flow
- Silver test-copy workflow for safe experimentation
- Silver partitioning
- Spark launcher and project run scripts

### Planned but Not Yet Fully Implemented
- Full Silver schema normalization for all datasets
- Silver data contract enforcement
- Silver quarantine datasets and quality scoring
- Full Gold table build scripts
- Data entry application
- Streaming ingestion path
- Dashboard delivery assets
- Formal CI pipeline
- Production monitoring stack
- Full operational runbook automation

### Why This Distinction Matters
- Documentation shows architectural intent.
- Implemented code shows current working capability.
- Keeping these separate makes the README more honest and more professional.




-----------------------------------------------------

Based on your **IdentityLakehouse** roadmap, here’s the **phase-by-phase tech stack** used across the whole project—from Stage 0 to Stage 13. I mapped this directly from your project document. 

---

# Stage 0 — Problem Definition & Scope

### Tech / Skills Used

* Domain modeling
* Data modeling basics
* Business requirement gathering
* Architecture thinking
* Documentation

### Tools

* Markdown / README
* Diagram tools (optional)

### Concepts

* Data grain
* Business keys
* Entity relationships

---

# Stage 1 — EDA Foundation

### Tech Used

## Python

* pandas
* numpy

## Jupyter Notebook

## Visualization

* matplotlib

### Concepts

* null analysis
* duplicates
* profiling
* outliers
* cardinality
* distributions

---

# Stage 2 — Data Contracts & Quality Rulebook

### Tech Used

## Python

## SQL

### Data Quality Concepts

* schema validation
* type validation
* domain validation
* quality scoring

Possible frameworks later:

* Great Expectations

---

# Stage 3 — Bronze Layer

This is your first real DE layer.

### Core Tech

## Apache Spark

## PySpark

## Delta Lake

## File formats

* CSV
* JSON
* Apache Parquet

### Storage Concepts

* partitioning
* append
* overwrite

### Metadata

* lineage
* batch id
* source file

### Supporting tools

* PowerShell
* Python virtual environments

---

# Stage 4 — Silver Layer

(Current phase)

### Core Tech

## Apache Spark

## PySpark

## Spark SQL

## Delta Lake

### Advanced Spark

* window functions
* repartition
* joins
* aggregations

### Data Quality

* quarantine datasets
* deduplication
* schema normalization
* contract enforcement

---

# Stage 5 — Gold Layer

### Core Tech

## Spark SQL

## PySpark

## Delta Lake

### Data Modeling

* star schema
* snowflake schema
* fact tables
* dimension tables

### Analytics

* KPI engineering
* aggregations
* marts

---

# Stage 6 — Data Entry Platform

### Backend

## FastAPI or Flask

### Database

## PostgreSQL

### Frontend

* HTML
* CSS
* JavaScript

### Security

* JWT
* RBAC

---

# Stage 7 — Streaming (Kappa)

### Core Streaming Tech

## Apache Kafka

## Spark Structured Streaming

## Delta Lake

### Concepts

* watermarking
* checkpoints
* idempotency
* event-time processing

---

# Stage 8 — Dashboard Layer

### BI Tools

## Microsoft Power BI

### Optional

* Tableau

### Concepts

* semantic models
* DAX
* KPIs
* drill-down reports

---

# Stage 9 — Security & Governance

### Security

## Microsoft Azure services:

* Azure Key Vault
* Managed Identity

### Governance

* Unity Catalog
* Purview

### Concepts

* RBAC
* column masking
* lineage

---

# Stage 10 — Reliability & Performance

### Tech

## Spark tuning

## Delta optimization

### Concepts

* partition pruning
* compaction
* autoscaling
* cluster tuning

---

# Stage 11 — CI/CD & Testing

### Version Control

## Git

## GitHub

### CI/CD

## GitHub Actions

### Testing

* pytest

### Quality

* linting

---

# Stage 12 — Production Operations

### Monitoring

## Azure Monitor

### Logging

## Python logging

### Alerting

* SLA alerts

---

# Stage 13 — Cloud Productionization

### Cloud Stack

## Microsoft Azure

### Storage

* ADLS Gen2

### Compute

## Azure Databricks

### Security

* Key Vault

### Governance

* Purview

### BI

* Power BI

---

# Full stack of your project

In one line:

**Python → pandas → SQL → Spark → Delta Lake → FastAPI → PostgreSQL → Kafka → Power BI → Azure → Databricks → GitHub**

That is the complete tech stack your project uses end-to-end.
