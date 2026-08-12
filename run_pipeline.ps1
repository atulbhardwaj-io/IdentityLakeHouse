param(
    [string]$ContainerName = "spark-master",
    [string]$MasterUrl = "spark://spark-master:7077",
    [string]$WarehouseDir = "/app/spark-warehouse",
    [string]$MetastoreUrl = "jdbc:derby:;databaseName=/app/metastore_db;create=true",
    [string]$RunId = ("run_" + (Get-Date -Format "yyyyMMdd_HHmmss")),

    [string[]]$BronzeTables = @("all"),

    [ValidateSet("overwrite", "append")]
    [string]$BronzeMode = "append",

    [ValidateSet("landing", "legacy", "both")]
    [string]$BronzeSourceMode = "landing",

    [string]$RawLandingRoot = "/app/data/upcoming_data",

    [switch]$ForceBronzeReprocess,

    [string[]]$SilverTables = @("all"),

    [ValidateSet("overwrite", "append")]
    [string]$SilverMode = "append",

    [ValidateSet("incremental", "full")]
    [string]$SilverLoadType = "incremental",

    [switch]$RunCsvToBronze,
    [switch]$SkipBronzeToSilver,
    [switch]$SkipSilverQualityValidation,
    [switch]$FailOnSilverQualityInvalid
)


# ============================================================
# ERROR HANDLING
# ============================================================

$ErrorActionPreference = "Stop"


# ============================================================
# FUNCTION: EXECUTE COMMAND INSIDE SPARK CONTAINER
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

    docker exec $ContainerName /bin/bash -lc "$Command"

    if ($LASTEXITCODE -ne 0) {

        throw "Command failed in container '$ContainerName'. Exit code: $LASTEXITCODE"

    }
}


# ============================================================
# PIPELINE INFORMATION
# ============================================================

Write-Host "============================================================" `
    -ForegroundColor Cyan

Write-Host "                    PIPELINE START" `
    -ForegroundColor Cyan

Write-Host "============================================================" `
    -ForegroundColor Cyan

Write-Host ""

Write-Host "Container:   $ContainerName"
Write-Host "Master:      $MasterUrl"
Write-Host "Warehouse:   $WarehouseDir"
Write-Host "Metastore:   $MetastoreUrl"
Write-Host "RunId:       $RunId"

Write-Host ""

Write-Host "Bronze Mode:     $BronzeMode"
Write-Host "Bronze Tables:   $($BronzeTables -join ', ')"
Write-Host "Bronze Source:   $BronzeSourceMode"
Write-Host "Landing Root:    $RawLandingRoot"

Write-Host ""

Write-Host "Silver Mode:     $SilverMode"
Write-Host "Silver LoadType: $SilverLoadType"
Write-Host "Silver Tables:   $($SilverTables -join ', ')"

Write-Host ""

Write-Host "Quality Validation: $(-not $SkipSilverQualityValidation)"

Write-Host ""


# ============================================================
# CHECK DOCKER CONTAINER
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

Invoke-InSparkContainer `
    "mkdir -p /tmp/.ivy2/cache /tmp/.ivy2/jars"


# ============================================================
# STEP 0: CSV -> BRONZE
# ============================================================

if ($RunCsvToBronze) {

    Write-Host ""
    Write-Host "[0/2] CSV -> Bronze load..." `
        -ForegroundColor Yellow


    # Convert array of tables into space-separated string

    $bronzeTableArgs = $BronzeTables -join " "


    # Optional force reprocess argument

    $forceBronzeReprocessArg = ""

    if ($ForceBronzeReprocess) {

        $forceBronzeReprocessArg = " --force-reprocess"

    }


    # Build Spark Submit command as ONE SINGLE LINE.
    # This avoids Bash line continuation problems.

    $csvToBronzeCmd = "/opt/spark/bin/spark-submit --master $MasterUrl --packages io.delta:delta-spark_2.12:3.0.0 --conf spark.jars.ivy=/tmp/.ivy2 --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog --conf spark.sql.catalogImplementation=hive --conf spark.sql.warehouse.dir=$WarehouseDir --conf 'spark.hadoop.javax.jdo.option.ConnectionURL=$MetastoreUrl' /app/scripts/spark/csv_to_delta.py --tables $bronzeTableArgs --mode $BronzeMode --source-mode $BronzeSourceMode --raw-landing-root $RawLandingRoot --run-id $RunId$forceBronzeReprocessArg"


    Invoke-InSparkContainer $csvToBronzeCmd

}
else {

    Write-Host ""
    Write-Host "[SKIP] CSV -> Bronze load skipped." `
        -ForegroundColor DarkYellow

    Write-Host "       Use -RunCsvToBronze to run it." `
        -ForegroundColor DarkYellow

}


# ============================================================
# STEP 1: BRONZE -> SILVER
# ============================================================

if (-not $SkipBronzeToSilver) {

    Write-Host ""
    Write-Host "[1/2] Bronze -> Silver copy..." `
        -ForegroundColor Yellow


    # Convert Silver table array into space-separated string

    $silverTableArgs = $SilverTables -join " "


    # Build Spark Submit command as ONE SINGLE LINE

    $bronzeToSilverCmd = "/opt/spark/bin/spark-submit --master $MasterUrl --packages io.delta:delta-spark_2.12:3.0.0 --conf spark.jars.ivy=/tmp/.ivy2 --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog --conf spark.sql.catalogImplementation=hive --conf spark.sql.warehouse.dir=$WarehouseDir --conf 'spark.hadoop.javax.jdo.option.ConnectionURL=$MetastoreUrl' --conf spark.executor.cores=1 --conf spark.executor.memory=1g --conf spark.cores.max=2 /app/scripts/spark/bronze_to_silver.py --tables $silverTableArgs --mode $SilverMode --load-type $SilverLoadType --run-id $RunId --register"


    Invoke-InSparkContainer $bronzeToSilverCmd


    # ========================================================
    # STEP 1.5: SILVER QUALITY VALIDATION
    # ========================================================

    if (-not $SkipSilverQualityValidation) {

        Write-Host ""
        Write-Host "[1.5/2] Silver quality validation and quarantine..." `
            -ForegroundColor Yellow


        # Optional failure argument

        $silverQualityFailArg = ""

        if ($FailOnSilverQualityInvalid) {

            $silverQualityFailArg = " --fail-on-invalid"

        }


        # Build quality validation command as ONE SINGLE LINE

        $silverQualityCmd = "/opt/spark/bin/spark-submit --master $MasterUrl --packages io.delta:delta-spark_2.12:3.0.0 --conf spark.jars.ivy=/tmp/.ivy2 --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog --conf spark.sql.catalogImplementation=hive --conf spark.sql.warehouse.dir=$WarehouseDir --conf 'spark.hadoop.javax.jdo.option.ConnectionURL=$MetastoreUrl' /app/scripts/spark/validate_silver_quality.py --tables $silverTableArgs --run-id $RunId --validate-scope incremental$silverQualityFailArg"


        Invoke-InSparkContainer $silverQualityCmd

    }
    else {

        Write-Host ""
        Write-Host "[SKIP] Silver quality validation skipped." `
            -ForegroundColor DarkYellow

    }

}
else {

    Write-Host ""
    Write-Host "[SKIP] Bronze -> Silver copy skipped." `
        -ForegroundColor DarkYellow

}


# ============================================================
# PIPELINE COMPLETE
# ============================================================

Write-Host ""

Write-Host "============================================================" `
    -ForegroundColor Cyan

Write-Host "                  PIPELINE COMPLETED" `
    -ForegroundColor Cyan

Write-Host "============================================================" `
    -ForegroundColor Cyan
9