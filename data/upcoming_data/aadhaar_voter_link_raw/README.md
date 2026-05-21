# aadhaar_voter_link_raw

CSV files placed here incrementally load into `bronze.aadhaar_voter_link_raw`.

Recommended folder and file format:

```text
year=YYYY/month=MM/day=DD/aadhaar_voter_link_raw_YYYY_MM_DD.csv
```

Example:

```text
year=2026/month=05/day=21/aadhaar_voter_link_raw_2026_05_21.csv
```

Load only this table:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables aadhaar_voter_link_raw
```

Reload this table's files:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables aadhaar_voter_link_raw -ForceBronzeReprocess
```

--- to run all
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables all