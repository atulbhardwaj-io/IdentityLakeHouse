# IdentityLakeHouse

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
Use project venv Python:

```powershell
.\venv\Scripts\python.exe scripts/bronze_layer/sql_ingestion/build_bronze_synthetic.py --tables district_scheme_payment_raw --mode overwrite
```

Run all synthetic raw tables:

```powershell
.\venv\Scripts\python.exe scripts/bronze_layer/sql_ingestion/build_bronze_synthetic.py --tables all --mode overwrite
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

### Silver Layer Implementation Phases

Below are the phases you should implement, what you need to learn, and how to implement them conceptually.

### Phase 1: Bronze Data Loading
#### What You Need to Learn

- Spark DataFrame API
- Reading Delta tables
- Distributed dataset processing
- Lazy evaluation in Spark

#### How to Implement

Load the Bronze tables as Spark DataFrames and treat them as the source input for all Silver transformations.

This phase ensures the Silver pipeline always reads consistent snapshots of raw data.

### Phase 2: Schema Normalization
#### What You Need to Learn

- Schema design principles
- Column selection and ordering
- Data modeling basics
- Schema drift handling

#### How to Implement

Define the expected schema for each dataset.

Ensure:

- column names are standardized
- column order is consistent
- unnecessary columns are removed

The goal is to create a stable schema that never surprises downstream systems.

### Phase 3: Data Type Validation
#### What You Need to Learn

- Data type systems
- Schema enforcement
- Validation logic

#### How to Implement

Validate that each field conforms to the expected data type.

Examples:

- dates must be valid dates
- numeric fields must contain numbers
- identifiers must follow correct format

Records with invalid types must be captured and sent to a quarantine dataset.

### Phase 4: Data Type Normalization
#### What You Need to Learn

- Schema casting
- Data transformation
- DataFrame column operations

#### How to Implement

Convert all fields to their canonical data types.

Examples:

- date fields -> date
- numeric measures -> double or integer
- categorical attributes -> string

This ensures consistent analytics behavior.

### Phase 5: Data Contract Enforcement
#### What You Need to Learn

- Data contracts
- validation frameworks
- business rule enforcement

#### How to Implement

Define rules that guarantee dataset integrity.

Examples:

- unique dataset keys
- non-negative numeric values
- valid identifier formats

Rows violating rules should be quarantined instead of deleted.

### Phase 6: Deduplication
#### What You Need to Learn

- Window functions
- Record prioritization strategies
- Dataset grain definition

#### How to Implement

Define the unique key of the dataset.

Example grain:

(date, state, district, pincode)

Use deterministic logic to keep only one record per key.

This prevents incorrect analytical results.

### Phase 7: Domain Validation
#### What You Need to Learn

- Domain constraints
- categorical data validation
- reference data validation

#### How to Implement

Ensure fields only contain valid domain values.

Examples:

- valid state codes
- valid gender values
- valid district names

Invalid domain values must be isolated in quarantine tables.

### Phase 8: Null Handling
#### What You Need to Learn

- mandatory field rules
- null handling strategies

#### How to Implement

Identify critical columns that must never be null.

Examples:

- date
- state
- district
- pincode

Rows missing mandatory values should be rejected or quarantined.

### Phase 9: Derived Columns
#### What You Need to Learn

- feature engineering basics
- column transformations

#### How to Implement

Create standardized derived attributes that simplify analytics.

Examples:

- year
- month
- region groupings

Derived fields improve query performance and analytical usability.

### Phase 10: Late Arriving Data Handling
#### What You Need to Learn

- event time vs processing time
- watermarking
- incremental reprocessing strategies

#### How to Implement

Some records may arrive later than expected.

Example scenario:

- Event date: March 1
- Arrival date: March 5

Solution:

Process a rolling historical window during each run (for example last 7 days).

This ensures late data is captured without full table reprocessing.

### Phase 11: Audit Columns and Data Freshness
#### What You Need to Learn

- metadata tracking
- operational monitoring

#### How to Implement

Add metadata columns that track:

- when Silver processing occurred
- how old the data is
- which pipeline run produced the record

This enables data freshness monitoring and debugging.

### Phase 12: Quarantine Dataset Management
#### What You Need to Learn

- data governance
- error classification
- operational monitoring

#### How to Implement

All invalid records should be stored separately rather than discarded.

Each quarantined record should contain:

- failure reason
- failed rule
- pipeline run identifier

This ensures full traceability of data issues.

### Phase 13: Writing Silver Tables
#### What You Need to Learn

- distributed write operations
- partitioning strategies
- Delta Lake storage design

#### How to Implement

Write cleaned and validated datasets as Delta tables in the Silver layer.

Design partition strategies carefully to ensure efficient queries and scalable storage.

### Phase 14: Data Quality Metrics
#### What You Need to Learn

- data observability
- pipeline monitoring
- quality scoring systems

#### How to Implement

Track operational metrics such as:

- number of records processed
- number of valid records
- number of quarantined records
- number of duplicates removed

These metrics provide visibility into pipeline health.

### Phase 15: Incremental Processing
#### What You Need to Learn

- incremental ingestion patterns
- watermark tracking
- batch processing strategies

#### How to Implement

Instead of reprocessing the entire Bronze dataset, process only newly ingested data.

This improves pipeline efficiency and reduces compute cost.

### Phase 16: Validation and Reconciliation
#### What You Need to Learn

- data reconciliation techniques
- validation strategies

#### How to Implement

Verify that no data is lost during processing.

Example validation concept:

bronze_records = silver_valid_records + quarantined_records

This ensures pipeline correctness.

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

## Stage 7: Streaming (Kappa) Integration
### Objectives
Use one processing logic for real-time and replay.

### Build
- CDC/app events -> Kafka/Event Hubs
- Spark Structured Streaming -> Bronze -> Silver -> Gold
- Checkpointing, watermarking, idempotency

### Output
- Live data with replay capability

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

## Stage 12: Go-Live and Operations
### Objectives
Run as a real production service.

### Build
- Pilot launch -> phased rollout
- SLA monitoring and alerts
- Incident runbook and support model

### Output
- Fully operational government analytics platform

## Current Status Summary
- EDA foundation: Completed
- 14-step framework implementation: Completed
- Enrollment/Demographic/Biometric profiling: Completed
- Documentation artifacts: Completed
- Bronze/Silver/Gold production pipeline: Next active build phase
