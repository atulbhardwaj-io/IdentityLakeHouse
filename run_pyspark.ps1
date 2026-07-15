param(
    [string]$ContainerName = "spark-master",
    [string]$MasterUrl = "spark://spark-master:7077",
    [string]$WarehouseDir = "/app/spark-warehouse",
    [string]$MetastoreUrl = "jdbc:derby:;databaseName=/app/metastore_db;create=true"
)

$ErrorActionPreference = "Stop"


# ============================================================
# FUNCTION: Run command inside Spark Docker container
# ============================================================

function Invoke-InSparkContainer {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    Write-Host ""
    Write-Host "[DEBUG] Executing inside container '$ContainerName':" `
        -ForegroundColor DarkGray

    Write-Host $Command -ForegroundColor DarkGray
    Write-Host ""

    # -it is needed because PySpark is an interactive shell
    docker exec -it $ContainerName /bin/bash -lc "$Command"

    if ($LASTEXITCODE -ne 0) {
        throw "Command failed in container '$ContainerName'. Exit code: $LASTEXITCODE"
    }
}


# ============================================================
# START
# ============================================================

Write-Host "============================================================" `
    -ForegroundColor Cyan

Write-Host "                    PYSPARK SHELL" `
    -ForegroundColor Cyan

Write-Host "============================================================" `
    -ForegroundColor Cyan

Write-Host ""

Write-Host "Container: $ContainerName"
Write-Host "Master:    $MasterUrl"
Write-Host "Warehouse: $WarehouseDir"
Write-Host "Metastore: $MetastoreUrl"

Write-Host ""


# ============================================================
# CHECK WHETHER CONTAINER IS RUNNING
# ============================================================

Write-Host "[CHECK] Checking Spark container..." `
    -ForegroundColor Yellow

$containerRunning = docker inspect `
    -f '{{.State.Running}}' `
    $ContainerName 2>$null

if ($containerRunning -ne "true") {
    throw "Docker container '$ContainerName' is not running."
}

Write-Host "[OK] Container '$ContainerName' is running." `
    -ForegroundColor Green


# ============================================================
# PREPARE IVY CACHE
# ============================================================

Write-Host ""
Write-Host "[SETUP] Preparing Ivy cache..." `
    -ForegroundColor Yellow

Invoke-InSparkContainer "mkdir -p /tmp/.ivy2/cache /tmp/.ivy2/jars"


# ============================================================
# BUILD PYSPARK COMMAND
# ============================================================

Write-Host ""
Write-Host "[START] Starting interactive PySpark shell..." `
    -ForegroundColor Yellow

# IMPORTANT:
# Keep the complete PySpark command on ONE LINE.
# This prevents Bash from treating --master, --packages,
# and --conf as separate commands.

$pysparkCmd = "/opt/spark/bin/pyspark --master $MasterUrl --packages io.delta:delta-spark_2.12:3.0.0 --conf spark.jars.ivy=/tmp/.ivy2 --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog --conf spark.sql.catalogImplementation=hive --conf spark.sql.warehouse.dir=$WarehouseDir --conf 'spark.hadoop.javax.jdo.option.ConnectionURL=$MetastoreUrl'"


# ============================================================
# START INTERACTIVE PYSPARK SHELL
# ============================================================

Invoke-InSparkContainer $pysparkCmd