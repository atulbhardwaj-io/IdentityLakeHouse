param(
    [string]$ContainerName = "spark-master",
    [string]$MasterUrl = "spark://spark-master:7077",
    [string]$WarehouseDir = "/app/spark-warehouse",
    [string]$MetastoreUrl = "jdbc:derby:;databaseName=/app/metastore_db;create=true"
)

$ErrorActionPreference = "Stop"

function Invoke-InSparkContainer {
    param(
        [Parameter(Mandatory = $true)][string]$Command
    )

    docker exec -it $ContainerName /bin/bash -lc $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed in container '$ContainerName'."
    }
}

Write-Host "Starting PySpark in container '$ContainerName'..." -ForegroundColor Cyan

# Keep Ivy writable inside the container so Delta package resolution succeeds.
Invoke-InSparkContainer "mkdir -p /tmp/.ivy2/cache /tmp/.ivy2/jars"

$pysparkCmd = @"
/opt/spark/bin/pyspark \
--master $MasterUrl \
--packages io.delta:delta-spark_2.12:3.0.0 \
--conf spark.jars.ivy=/tmp/.ivy2 \
--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
--conf spark.sql.catalogImplementation=hive \
--conf spark.sql.warehouse.dir=$WarehouseDir \
--conf 'javax.jdo.option.ConnectionURL=$MetastoreUrl'
"@

Invoke-InSparkContainer $pysparkCmd
