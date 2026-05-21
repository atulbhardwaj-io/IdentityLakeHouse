# demographic

CSV files placed here incrementally load into `bronze.demographic`.

Recommended folder and file format:

```text
year=YYYY/month=MM/day=DD/demographic_YYYY_MM_DD.csv
```

Example:

```text
year=2026/month=05/day=21/demographic_2026_05_21.csv
```

Load only this table:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables demographic
```

Reload this table's files:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables demographic -ForceBronzeReprocess
```


--- to run all
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables all