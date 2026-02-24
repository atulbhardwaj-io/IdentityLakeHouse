# Bronze Layer Runbook (Synthetic Tables)

This runbook ingests synthetic CSV raw tables into Delta Bronze tables using PySpark.

## Script

- `scripts/bronze_layer/build_bronze_synthetic.py`

## Source Tables (CSV)

- `population_raw.csv`
- `scheme_master_raw.csv`
- `scheme_beneficiary_raw.csv`
- `voter_registry_raw.csv`
- `aadhaar_voter_link_raw.csv`
- `district_scheme_payment_raw.csv`

Input folder default:
- `synthetic_data/synthetic`

Output folder default:
- `data/bronze/synthetic`

## Step 1: Run only the most important table first

```powershell
python scripts/bronze_layer/build_bronze_synthetic.py --tables district_scheme_payment_raw --mode overwrite
```

## Step 2: Run all synthetic tables

```powershell
python scripts/bronze_layer/build_bronze_synthetic.py --tables all --mode overwrite
```

## Step 3: Incremental load pattern (append mode)

```powershell
python scripts/bronze_layer/build_bronze_synthetic.py --tables district_scheme_payment_raw scheme_beneficiary_raw --mode append
```

## Bronze Metadata Added

Each Bronze table includes:
- `bronze_ingest_ts`
- `bronze_source_file`
- `bronze_batch_id`

## Notes

- Date parsing supports both `dd-MM-yyyy` and `yyyy-MM-dd`.
- `ingest_ts` is parsed to timestamp when present.
- Bronze tables are registered under Spark catalog database: `bronze`.
