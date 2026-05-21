# voter_registry_raw

CSV files placed here incrementally load into `bronze.voter_registry_raw`.

Recommended folder and file format:

```text
year=YYYY/month=MM/day=DD/voter_registry_raw_YYYY_MM_DD.csv
```

Example:

```text
year=2026/month=05/day=21/voter_registry_raw_2026_05_21.csv
```

Load only this table:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables voter_registry_raw
```

Reload this table's files:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables voter_registry_raw -ForceBronzeReprocess
```
