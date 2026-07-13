param(
    [string]$ContainerName = "spark-master",
    [string]$MasterUrl = "spark://spark-master:7077",
    [string]$WarehouseDir = "/app/spark-warehouse",
    [string]$MetastoreUrl = "jdbc:derby:;databaseName=/app/metastore_db;create=true",
    [switch]$UseHiveMetastore
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

Write-Host "Starting Spark SQL in container '$ContainerName'..." -ForegroundColor Cyan

# Keep Ivy writable inside the container so Delta package resolution succeeds.
Invoke-InSparkContainer "mkdir -p /tmp/.ivy2/cache /tmp/.ivy2/jars"

if ($UseHiveMetastore) {
    Write-Host "Using Hive metastore. Close other Spark shells/jobs first to avoid Derby lock errors." -ForegroundColor Yellow
    $sparkSqlCmd = @"
/opt/spark/bin/spark-sql \
--master $MasterUrl \
--packages io.delta:delta-spark_2.12:3.0.0 \
--conf spark.jars.ivy=/tmp/.ivy2 \
--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
--conf spark.sql.catalogImplementation=hive \
--conf spark.sql.warehouse.dir=$WarehouseDir \
--conf 'spark.hadoop.javax.jdo.option.ConnectionURL=$MetastoreUrl'
"@

    Invoke-InSparkContainer $sparkSqlCmd
    return
}

Write-Host "Using Delta path views without Hive metastore, so Derby lock errors are avoided." -ForegroundColor Green

$initSqlCmd = @"
cat > /tmp/identitylakehouse_spark_sql_init.sql <<'SQL'
CREATE TEMPORARY VIEW bronze_aadhaar_voter_link_raw USING delta OPTIONS (path '/app/scripts/bronze_layer/aadhaar_voter_link_raw');
CREATE TEMPORARY VIEW bronze_biometric USING delta OPTIONS (path '/app/scripts/bronze_layer/biometric');
CREATE TEMPORARY VIEW bronze_demographic USING delta OPTIONS (path '/app/scripts/bronze_layer/demographic');
CREATE TEMPORARY VIEW bronze_district_scheme_payment_raw USING delta OPTIONS (path '/app/scripts/bronze_layer/district_scheme_payment_raw');
CREATE TEMPORARY VIEW bronze_enrolment USING delta OPTIONS (path '/app/scripts/bronze_layer/enrolment');
CREATE TEMPORARY VIEW bronze_population_raw USING delta OPTIONS (path '/app/scripts/bronze_layer/population_raw');
CREATE TEMPORARY VIEW bronze_scheme_beneficiary_raw USING delta OPTIONS (path '/app/scripts/bronze_layer/scheme_beneficiary_raw');
CREATE TEMPORARY VIEW bronze_scheme_master_raw USING delta OPTIONS (path '/app/scripts/bronze_layer/scheme_master_raw');
CREATE TEMPORARY VIEW bronze_voter_registry_raw USING delta OPTIONS (path '/app/scripts/bronze_layer/voter_registry_raw');

CREATE TEMPORARY VIEW silver_aadhaar_voter_link_raw_valid USING delta OPTIONS (path '/app/scripts/silver_layer/aadhaar_voter_link_raw_valid');
CREATE TEMPORARY VIEW silver_biometric_valid USING delta OPTIONS (path '/app/scripts/silver_layer/biometric_valid');
CREATE TEMPORARY VIEW silver_demographic_valid USING delta OPTIONS (path '/app/scripts/silver_layer/demographic_valid');
CREATE TEMPORARY VIEW silver_district_scheme_payment_raw_valid USING delta OPTIONS (path '/app/scripts/silver_layer/district_scheme_payment_raw_valid');
CREATE TEMPORARY VIEW silver_enrolment_valid USING delta OPTIONS (path '/app/scripts/silver_layer/enrolment_valid');
CREATE TEMPORARY VIEW silver_population_raw_valid USING delta OPTIONS (path '/app/scripts/silver_layer/population_raw_valid');
CREATE TEMPORARY VIEW silver_scheme_beneficiary_raw_valid USING delta OPTIONS (path '/app/scripts/silver_layer/scheme_beneficiary_raw_valid');
CREATE TEMPORARY VIEW silver_scheme_master_raw_valid USING delta OPTIONS (path '/app/scripts/silver_layer/scheme_master_raw_valid');
CREATE TEMPORARY VIEW silver_voter_registry_raw_valid USING delta OPTIONS (path '/app/scripts/silver_layer/voter_registry_raw_valid');

CREATE TEMPORARY VIEW quarantine_demographic_quality USING delta OPTIONS (path '/app/scripts/silver_layer/quarantine/demographic_quality_quarantine');
SQL
"@

Invoke-InSparkContainer $initSqlCmd

$sparkSqlCmd = @"
/opt/spark/bin/spark-sql \
--master $MasterUrl \
--packages io.delta:delta-spark_2.12:3.0.0 \
--conf spark.jars.ivy=/tmp/.ivy2 \
--conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
--conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
--conf spark.sql.catalogImplementation=in-memory \
--conf spark.sql.warehouse.dir=$WarehouseDir \
-i /tmp/identitylakehouse_spark_sql_init.sql
"@

Invoke-InSparkContainer $sparkSqlCmd
