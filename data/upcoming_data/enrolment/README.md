# enrolment

CSV files placed here incrementally load into `bronze.enrolment`.

Recommended folder and file format:

```text
year=YYYY/month=MM/day=DD/enrolment_YYYY_MM_DD.csv
```

Example:

```text
year=2026/month=05/day=21/enrolment_2026_05_21.csv
```

Load only this table:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables enrolment
```

Reload this table's files:

```powershell
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables enrolment -ForceBronzeReprocess
```


--- to run all
.\run_pipeline.ps1 -RunCsvToBronze -SkipBronzeToSilver -BronzeTables all