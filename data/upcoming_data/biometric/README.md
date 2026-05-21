# biometric

CSV files placed here incrementally load into `bronze.biometric`.

Recommended folder and file format:

```text
year=YYYY/month=MM/day=DD/biometric_YYYY_MM_DD.csv
```

Example:

```text
year=2026/month=05/day=21/biometric_2026_05_21.csv
```

Load only this table:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables biometric
```

Reload this table's files:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables biometric -ForceBronzeReprocess
```

--- to run all

.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables all
