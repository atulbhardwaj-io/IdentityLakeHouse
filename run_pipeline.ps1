param(
    [string]$ContainerName = "spark-master",
    [string]$MasterUrl = "spark://spark-master:7077",
    [string]$RunId = ("run_" + (Get-Date -Format "yyyyMMdd_HHmmss")),
    [string[]]$BronzeTables = @("all"),
    [ValidateSet("overwrite", "append")][string]$BronzeMode = "overwrite",
    [string[]]$SilverTables = @("all"),
    [ValidateSet("overwrite", "append")][string]$SilverMode = "overwrite",
    [switch]$RunCsvToBronze,
    [switch]$RunBronzeValidation,
    [switch]$SkipBronzeToSilver,
    [switch]$RunAadhaarTransform,
    [switch]$Promote
)

$ErrorActionPreference = "Stop"

function Invoke-InSparkContainer {
    param(
        [Parameter(Mandatory = $true)][string]$Command
    )

    docker exec $ContainerName /bin/bash -lc $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed in container '$ContainerName'."
    }
}

Write-Host "== Pipeline Start ==" -ForegroundColor Cyan
Write-Host "Container: $ContainerName"
Write-Host "Master:    $MasterUrl"
Write-Host "RunId:     $RunId"
Write-Host "Bronze:    $BronzeMode | Tables: $($BronzeTables -join ', ')"
Write-Host "Silver:    $SilverMode | Tables: $($SilverTables -join ', ')"

# Ensure writable Ivy cache inside container (fixes permission issues under /home/spark/.ivy2).
Invoke-InSparkContainer "mkdir -p /tmp/.ivy2/cache /tmp/.ivy2/jars"

if ($RunCsvToBronze) {
    Write-Host "`n[0/2] CSV -> Bronze load..." -ForegroundColor Yellow
    $bronzeTableArgs = $BronzeTables -join " "
    $csvToBronzeCmd = @"
/opt/spark/bin/spark-submit \
--master $MasterUrl \
--packages io.delta:delta-spark_2.12:3.0.0 \
--conf spark.jars.ivy=/tmp/.ivy2 \
--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
/app/scripts/spark/csv_to_delta.py \
--tables $bronzeTableArgs \
--mode $BronzeMode \
--run-id $RunId
"@
    Invoke-InSparkContainer $csvToBronzeCmd
} else {
    Write-Host "`n[SKIP] CSV -> Bronze load skipped. Use -RunCsvToBronze to run it." -ForegroundColor DarkYellow
}

if ($RunBronzeValidation) {
    Write-Host "`n[0.5/2] Bronze validation..." -ForegroundColor Yellow
    $bronzeTableArgs = $BronzeTables -join " "
    $validateBronzeCmd = @"
/opt/spark/bin/spark-submit \
--master $MasterUrl \
--packages io.delta:delta-spark_2.12:3.0.0 \
--conf spark.jars.ivy=/tmp/.ivy2 \
--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
/app/scripts/spark/validate_bronze.py \
--master $MasterUrl \
--tables $bronzeTableArgs
"@
    Invoke-InSparkContainer $validateBronzeCmd
} else {
    Write-Host "`n[SKIP] Bronze validation skipped. Use -RunBronzeValidation to run it." -ForegroundColor DarkYellow
}

if (-not $SkipBronzeToSilver) {
    Write-Host "`n[1/2] Bronze -> Silver copy (all Delta tables)..." -ForegroundColor Yellow
    $silverTableArgs = $SilverTables -join " "
    $bronzeToSilverCmd = @"
/opt/spark/bin/spark-submit \
--master $MasterUrl \
--packages io.delta:delta-spark_2.12:3.0.0 \
--conf spark.jars.ivy=/tmp/.ivy2 \
--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
--conf spark.executor.cores=1 \
--conf spark.executor.memory=1g \
--conf spark.cores.max=2 \
/app/scripts/spark/bronze_to_silver.py \
--tables $silverTableArgs \
--mode $SilverMode \
--run-id $RunId \
--register
"@
    Invoke-InSparkContainer $bronzeToSilverCmd
} else {
    Write-Host "`n[SKIP] Bronze -> Silver copy skipped." -ForegroundColor DarkYellow
}

if ($RunAadhaarTransform) {
    Write-Host "`n[2/2] Aadhaar Silver transform (test path)..." -ForegroundColor Yellow
    $transformCmd = @"
/opt/spark/bin/spark-submit \
--master $MasterUrl \
--packages io.delta:delta-spark_2.12:3.0.0 \
--conf spark.jars.ivy=/tmp/.ivy2 \
--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
/app/scripts/silver_layer/transform_aadhaar_voter_link_silver.py \
--input-path /app/scripts/silver_layer/aadhaar_voter_link_raw_valid_test \
--output-path /app/scripts/silver_layer/aadhaar_voter_link_raw_valid_test \
--main-path /app/scripts/silver_layer/aadhaar_voter_link_raw_valid \
--run-id $RunId
"@

    if ($Promote) {
        $transformCmd = $transformCmd + " --promote"
        Write-Host "[WARN] Promote is ON: main Silver table will be overwritten after transform." -ForegroundColor Red
    } else {
        Write-Host "[INFO] Test mode: main Silver table will NOT be changed." -ForegroundColor Green
    }

    Invoke-InSparkContainer $transformCmd
} else {
    Write-Host "`n[SKIP] Aadhaar transform skipped. Use -RunAadhaarTransform to run it." -ForegroundColor DarkYellow
}

Write-Host "`n== Pipeline Completed ==" -ForegroundColor Cyan
