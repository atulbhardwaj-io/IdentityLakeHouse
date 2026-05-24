import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import LongType, StringType, StructField, StructType, TimestampType


SYNTHETIC_FOLDER = "/app/synthetic_data/synthetic"
RAW_LANDING_ROOT = "/app/data/upcoming_data"
BRONZE_BASE_PATH = "/app/scripts/bronze_layer"
BRONZE_MANIFEST_PATH = f"{BRONZE_BASE_PATH}/_control/ingested_files"
BRONZE_FILE_VALIDATION_PATH = f"{BRONZE_BASE_PATH}/_control/incoming_file_validation_results"
INCOMING_SCHEMA_CONTRACT_PATH = "/app/scripts/spark/schema_contracts/incoming_csv_schema_contracts.json"
SKIP_FILES = {"district_masters.csv"}
SPARK_WAREHOUSE_DIR = "/app/spark-warehouse"
HIVE_METASTORE_URL = "jdbc:derby:;databaseName=/app/metastore_db;create=true"

DEMOGRAPHIC_CSV = (
    "/app/data/api_data_aadhar_demographic/api_data_aadhar_demographic/"
    "api_data_aadhar_demographic_combined.csv"
)
ENROLMENT_CSV = (
    "/app/data/api_data_aadhar_enrolment/api_data_aadhar_enrolment/"
    "api_data_aadhar_enrolment_combined.csv"
)
BIOMETRIC_CSV = (
    "/app/data/api_data_aadhar_biometric/api_data_aadhar_biometric/"
    "api_data_aadhar_biometric_combined.csv"
)

PARTITION_COLS_BY_TABLE = {
    "aadhaar_voter_link_raw": ["partition_year", "partition_month"],
    "biometric": ["partition_year", "partition_month"],
    "demographic": ["partition_year", "partition_month"],
    "district_scheme_payment_raw": ["partition_year", "partition_month"],
    "enrolment": ["partition_year", "partition_month"],
    "population_raw": ["partition_year", "partition_month"],
    "scheme_beneficiary_raw": ["partition_year", "partition_month"],
    "scheme_master_raw": ["active_flag"],
    "voter_registry_raw": ["partition_year", "partition_month"],
}

MANIFEST_SCHEMA = StructType(
    [
        StructField("table_name", StringType(), False),
        StructField("source_file_path", StringType(), False),
        StructField("source_file_name", StringType(), False),
        StructField("source_file_size_bytes", LongType(), True),
        StructField("source_file_modified_ts", TimestampType(), True),
        StructField("bronze_batch_id", StringType(), False),
        StructField("bronze_ingest_ts", TimestampType(), False),
        StructField("row_count", LongType(), False),
        StructField("status", StringType(), False),
    ]
)

FILE_VALIDATION_SCHEMA = StructType(
    [
        StructField("validation_run_id", StringType(), False),
        StructField("table_name", StringType(), False),
        StructField("source_file_path", StringType(), False),
        StructField("source_file_name", StringType(), False),
        StructField("validation_ts", TimestampType(), False),
        StructField("status", StringType(), False),
        StructField("row_count", LongType(), False),
        StructField("issues_json", StringType(), False),
    ]
)


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("IdentityLakehouse")
        .master("spark://spark-master:7077")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.warehouse.dir", SPARK_WAREHOUSE_DIR)
        .config("javax.jdo.option.ConnectionURL", HIVE_METASTORE_URL)
        .enableHiveSupport()
        .getOrCreate()
    )


def load_csv(spark: SparkSession, file_path: str):
    return (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(file_path)
    )


def load_csv_files(spark: SparkSession, file_paths: List[str]):
    return (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(file_paths)
    )


def load_schema_contracts(contract_path: str) -> Dict[str, Dict[str, str]]:
    with open(contract_path, "r", encoding="utf-8") as handle:
        raw_contracts = json.load(handle)
    return {
        table_name: {column: dtype.lower() for column, dtype in schema.items()}
        for table_name, schema in raw_contracts.items()
    }


def apply_bronze_metadata(df, run_id: str):
    return (
        df.withColumn("bronze_ingest_ts", F.current_timestamp())
        .withColumn("bronze_source_file", F.input_file_name())
        .withColumn("bronze_batch_id", F.lit(run_id))
    )


def normalize_partition_cols(df, partition_cols: List[str]) -> Tuple[object, List[str]]:
    normalized_df = df
    usable_partition_cols: List[str] = []

    if "partition_year" in partition_cols or "partition_month" in partition_cols:
        if "date" not in normalized_df.columns:
            return normalized_df, usable_partition_cols

        normalized_df = normalized_df.withColumn(
            "date",
            F.coalesce(
                F.to_date(F.col("date"), "dd-MM-yyyy"),
                F.to_date(F.col("date"), "yyyy-MM-dd"),
                F.col("date").cast("date"),
            ),
        )

        if "partition_year" in partition_cols:
            normalized_df = normalized_df.withColumn("partition_year", F.year(F.col("date")))
            usable_partition_cols.append("partition_year")

        if "partition_month" in partition_cols:
            normalized_df = normalized_df.withColumn("partition_month", F.month(F.col("date")))
            usable_partition_cols.append("partition_month")

    for col_name in partition_cols:
        if col_name in usable_partition_cols or col_name not in normalized_df.columns:
            continue

        if col_name.endswith("date") or col_name == "date":
            normalized_df = normalized_df.withColumn(
                col_name,
                F.coalesce(
                    F.to_date(F.col(col_name), "dd-MM-yyyy"),
                    F.to_date(F.col(col_name), "yyyy-MM-dd"),
                    F.col(col_name).cast("date"),
                ),
            )

        usable_partition_cols.append(col_name)

    return normalized_df, usable_partition_cols


def write_delta(df, table_name: str, mode: str) -> int:
    output_path = f"{BRONZE_BASE_PATH}/{table_name}"
    requested_partition_cols = PARTITION_COLS_BY_TABLE.get(table_name, [])
    df, partition_cols = normalize_partition_cols(df, requested_partition_cols)
    row_count = df.count()

    writer = df.write.format("delta").mode(mode)

    if mode == "overwrite":
        writer = writer.option("overwriteSchema", "true")

    if partition_cols:
        writer = writer.partitionBy(*partition_cols)

    writer.save(output_path)

    print(f"[OK] {table_name} Delta table created | rows={row_count} | mode={mode} | path={output_path}")
    if partition_cols:
        print(f"[PARTITIONED BY] {table_name}: {partition_cols}")
    else:
        print(f"[PARTITIONED BY] {table_name}: none")
    print(f"[SCHEMA] {table_name}: {df.columns}")
    return row_count


def register_bronze_table(spark: SparkSession, table_name: str) -> None:
    output_path = f"{BRONZE_BASE_PATH}/{table_name}"
    spark.sql("CREATE DATABASE IF NOT EXISTS bronze")
    spark.sql(
        f"CREATE TABLE IF NOT EXISTS bronze.{table_name} "
        f"USING DELTA LOCATION '{output_path}'"
    )
    print(f"[REGISTERED] bronze.{table_name}")


def register_manifest_table(spark: SparkSession) -> None:
    spark.sql("CREATE DATABASE IF NOT EXISTS bronze_control")
    spark.sql(
        "CREATE TABLE IF NOT EXISTS bronze_control.ingested_files "
        f"USING DELTA LOCATION '{BRONZE_MANIFEST_PATH}'"
    )
    print("[REGISTERED] bronze_control.ingested_files")


def register_file_validation_table(spark: SparkSession) -> None:
    spark.sql("CREATE DATABASE IF NOT EXISTS bronze_control")
    spark.sql(
        "CREATE TABLE IF NOT EXISTS bronze_control.incoming_file_validation_results "
        f"USING DELTA LOCATION '{BRONZE_FILE_VALIDATION_PATH}'"
    )
    print("[REGISTERED] bronze_control.incoming_file_validation_results")


def discover_legacy_table_sources() -> Dict[str, List[str]]:
    table_sources: Dict[str, List[str]] = {}

    for file_name in sorted(os.listdir(SYNTHETIC_FOLDER)):
        if not file_name.endswith(".csv"):
            continue
        if file_name.lower() in SKIP_FILES:
            continue

        table_name = file_name.replace(".csv", "").lower()
        file_path = f"{SYNTHETIC_FOLDER}/{file_name}"
        table_sources[table_name] = [file_path]

    table_sources["demographic"] = [DEMOGRAPHIC_CSV]
    table_sources["enrolment"] = [ENROLMENT_CSV]
    table_sources["biometric"] = [BIOMETRIC_CSV]

    return table_sources


def discover_landing_table_sources(raw_landing_root: str) -> Dict[str, List[str]]:
    root = Path(raw_landing_root)
    table_sources: Dict[str, List[str]] = {}

    if not root.exists():
        return table_sources

    for path in sorted(root.rglob("*.csv")):
        if path.name.lower() in SKIP_FILES:
            continue

        relative_parts = path.relative_to(root).parts
        if len(relative_parts) < 2:
            print(f"[SKIP] Landing file is not inside a table folder: {path}")
            continue

        table_name = relative_parts[0].lower()
        table_sources.setdefault(table_name, []).append(str(path))

    return table_sources


def discover_table_sources(source_mode: str, raw_landing_root: str) -> Dict[str, List[str]]:
    if source_mode == "legacy":
        return discover_legacy_table_sources()
    if source_mode == "landing":
        return discover_landing_table_sources(raw_landing_root)

    table_sources = discover_legacy_table_sources()
    for table_name, file_paths in discover_landing_table_sources(raw_landing_root).items():
        table_sources.setdefault(table_name, []).extend(file_paths)
    return table_sources


def delta_path_exists(path: str) -> bool:
    return (Path(path) / "_delta_log").exists()


def ensure_manifest(spark: SparkSession) -> None:
    if delta_path_exists(BRONZE_MANIFEST_PATH):
        register_manifest_table(spark)
        return

    empty_manifest = spark.createDataFrame([], MANIFEST_SCHEMA)
    empty_manifest.write.format("delta").mode("overwrite").save(BRONZE_MANIFEST_PATH)
    register_manifest_table(spark)


def get_processed_file_paths(spark: SparkSession, table_name: str) -> Set[str]:
    ensure_manifest(spark)
    rows = (
        spark.read.format("delta")
        .load(BRONZE_MANIFEST_PATH)
        .filter((F.col("table_name") == table_name) & (F.col("status") == "SUCCESS"))
        .select("source_file_path")
        .distinct()
        .collect()
    )
    return {row["source_file_path"] for row in rows}


def filter_new_files(spark: SparkSession, table_name: str, file_paths: List[str]) -> List[str]:
    processed_paths = get_processed_file_paths(spark, table_name)
    return [file_path for file_path in file_paths if file_path not in processed_paths]


def normalize_source_file_path(file_path: str) -> str:
    if file_path.startswith("file://"):
        return file_path[len("file://") :]
    return file_path


def collect_file_row_counts(df) -> Dict[str, int]:
    rows = df.groupBy("bronze_source_file").count().collect()
    return {
        normalize_source_file_path(row["bronze_source_file"]): int(row["count"])
        for row in rows
    }


def build_manifest_rows(
    spark: SparkSession,
    table_name: str,
    file_paths: List[str],
    run_id: str,
    file_row_counts: Dict[str, int],
):
    manifest_records = []
    for file_path in file_paths:
        path = Path(file_path)
        try:
            stat = path.stat()
            size_bytes = stat.st_size
            modified_ts = datetime.fromtimestamp(stat.st_mtime)
        except FileNotFoundError:
            size_bytes = None
            modified_ts = None

        manifest_records.append(
            {
                "table_name": table_name,
                "source_file_path": file_path,
                "source_file_name": path.name,
                "source_file_size_bytes": size_bytes,
                "source_file_modified_ts": modified_ts,
                "bronze_batch_id": run_id,
                "row_count": file_row_counts.get(file_path, 0),
                "status": "SUCCESS",
            }
        )

    manifest_df = spark.createDataFrame(manifest_records)
    manifest_df = (
        manifest_df.withColumn("bronze_ingest_ts", F.current_timestamp())
        .select(
            "table_name",
            "source_file_path",
            "source_file_name",
            "source_file_size_bytes",
            "source_file_modified_ts",
            "bronze_batch_id",
            "bronze_ingest_ts",
            "row_count",
            "status",
        )
    )
    return manifest_df


def append_manifest(
    spark: SparkSession,
    table_name: str,
    file_paths: List[str],
    run_id: str,
    file_row_counts: Dict[str, int],
) -> None:
    ensure_manifest(spark)
    manifest_df = build_manifest_rows(spark, table_name, file_paths, run_id, file_row_counts)
    manifest_df.write.format("delta").mode("append").save(BRONZE_MANIFEST_PATH)
    print(f"[MANIFEST] Recorded {len(file_paths)} file(s) for {table_name}")


def validate_csv_file(
    table_name: str,
    file_path: str,
    expected_columns: List[str],
    delimiter: str = ",",
) -> Dict[str, object]:
    path = Path(file_path)
    issues: List[Dict[str, object]] = []
    data_row_count = 0

    if not path.exists():
        issues.append({"check": "file_readable", "status": "FAIL", "detail": "file does not exist"})
        return build_file_validation_result(table_name, path, "FAIL", data_row_count, issues)

    if path.stat().st_size == 0:
        issues.append({"check": "empty_file", "status": "FAIL", "detail": "file size is 0 bytes"})
        return build_file_validation_result(table_name, path, "FAIL", data_row_count, issues)

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            first_line = handle.readline()
            if not first_line:
                issues.append({"check": "empty_file", "status": "FAIL", "detail": "file has no header row"})
                return build_file_validation_result(table_name, path, "FAIL", data_row_count, issues)

            if delimiter not in first_line and len(expected_columns) > 1:
                issues.append(
                    {
                        "check": "delimiter_validation",
                        "status": "FAIL",
                        "detail": f"expected delimiter '{delimiter}' not found in header",
                    }
                )

            handle.seek(0)
            reader = csv.reader(handle, delimiter=delimiter)
            try:
                header = next(reader)
            except StopIteration:
                issues.append({"check": "header_validation", "status": "FAIL", "detail": "missing header"})
                return build_file_validation_result(table_name, path, "FAIL", data_row_count, issues)

            header = [column.strip() for column in header]
            if not header or all(not column for column in header):
                issues.append({"check": "header_validation", "status": "FAIL", "detail": "blank header"})
                return build_file_validation_result(table_name, path, "FAIL", data_row_count, issues)

            missing_columns = [column for column in expected_columns if column not in header]
            if missing_columns:
                issues.append(
                    {
                        "check": "basic_column_existence",
                        "status": "FAIL",
                        "missing_columns": missing_columns,
                    }
                )

            malformed_examples = []
            expected_width = len(header)
            for row in reader:
                if not row or all(not value.strip() for value in row):
                    continue
                data_row_count += 1
                if len(row) != expected_width and len(malformed_examples) < 5:
                    malformed_examples.append(
                        {
                            "line_number": reader.line_num,
                            "expected_columns": expected_width,
                            "actual_columns": len(row),
                        }
                    )

            if data_row_count == 0:
                issues.append({"check": "empty_file", "status": "FAIL", "detail": "file has header but no data rows"})

            if malformed_examples:
                issues.append(
                    {
                        "check": "malformed_row_detection",
                        "status": "FAIL",
                        "examples": malformed_examples,
                    }
                )

    except UnicodeDecodeError as exc:
        issues.append({"check": "file_readable", "status": "FAIL", "detail": f"encoding error: {exc}"})
    except OSError as exc:
        issues.append({"check": "file_readable", "status": "FAIL", "detail": str(exc)})
    except csv.Error as exc:
        issues.append({"check": "malformed_row_detection", "status": "FAIL", "detail": str(exc)})

    status = "FAIL" if issues else "PASS"
    return build_file_validation_result(table_name, path, status, data_row_count, issues)


def build_file_validation_result(
    table_name: str,
    path: Path,
    status: str,
    row_count: int,
    issues: List[Dict[str, object]],
) -> Dict[str, object]:
    return {
        "table_name": table_name,
        "source_file_path": str(path),
        "source_file_name": path.name,
        "status": status,
        "row_count": int(row_count),
        "issues_json": json.dumps(issues, sort_keys=True),
    }


def validate_incoming_files(
    table_name: str,
    file_paths: List[str],
    schema_contracts: Dict[str, Dict[str, str]],
) -> Tuple[List[str], List[Dict[str, object]]]:
    if table_name not in schema_contracts:
        raise ValueError(f"No incoming CSV schema contract found for table: {table_name}")

    expected_columns = list(schema_contracts[table_name].keys())
    validation_results = [
        validate_csv_file(table_name, file_path, expected_columns)
        for file_path in file_paths
    ]
    valid_files = [
        result["source_file_path"]
        for result in validation_results
        if result["status"] == "PASS"
    ]
    return valid_files, validation_results


def append_file_validation_results(
    spark: SparkSession,
    run_id: str,
    validation_results: List[Dict[str, object]],
) -> None:
    if not validation_results:
        return

    rows = []
    for result in validation_results:
        rows.append(
            {
                "validation_run_id": run_id,
                "table_name": result["table_name"],
                "source_file_path": result["source_file_path"],
                "source_file_name": result["source_file_name"],
                "validation_ts": datetime.utcnow(),
                "status": result["status"],
                "row_count": int(result["row_count"]),
                "issues_json": result["issues_json"],
            }
        )

    validation_df = spark.createDataFrame(rows, FILE_VALIDATION_SCHEMA)
    validation_df.write.format("delta").mode("append").save(BRONZE_FILE_VALIDATION_PATH)
    register_file_validation_table(spark)


def print_file_validation_report(table_name: str, validation_results: List[Dict[str, object]]) -> None:
    print("\n" + "=" * 90)
    print(f"INCOMING FILE VALIDATION | table={table_name}")
    print("=" * 90)
    for result in validation_results:
        print(
            f"{result['status']} | file={result['source_file_name']} | "
            f"rows={result['row_count']} | issues={result['issues_json']}"
        )


def parse_args():
    parser = argparse.ArgumentParser(description="Build Bronze Delta tables from raw CSV files.")
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["all"],
        help="Table names to process, or 'all'.",
    )
    parser.add_argument(
        "--mode",
        choices=["overwrite", "append"],
        default="append",
        help="Write mode for Bronze Delta tables.",
    )
    parser.add_argument(
        "--source-mode",
        choices=["landing", "legacy", "both"],
        default="landing",
        help="landing reads /app/data/upcoming_data recursively; legacy reads the old fixed project CSVs; both combines them.",
    )
    parser.add_argument(
        "--raw-landing-root",
        default=RAW_LANDING_ROOT,
        help="Durable incoming CSV root. Expected layout: <root>/<table_name>/year=YYYY/month=MM/day=DD/*.csv",
    )
    parser.add_argument(
        "--schema-contract-path",
        default=INCOMING_SCHEMA_CONTRACT_PATH,
        help="Incoming CSV schema contract used for basic file validation.",
    )
    parser.add_argument(
        "--skip-file-validation",
        action="store_true",
        help="Skip lightweight incoming file validation before Bronze write.",
    )
    parser.add_argument(
        "--skip-invalid-files",
        action="store_true",
        help="Reject invalid files but continue loading valid files. Default fails the table when any file is invalid.",
    )
    parser.add_argument(
        "--run-id",
        default="manual_run",
        help="Logical run id for logging and replay tracking.",
    )
    parser.add_argument(
        "--allow-append-all",
        action="store_true",
        help="Deprecated safety flag kept for compatibility. File manifest now prevents appending already ingested files.",
    )
    parser.add_argument(
        "--force-reprocess",
        action="store_true",
        help="Ignore the ingestion manifest and process selected files again. Use only for controlled backfills.",
    )
    return parser.parse_args()


def resolve_tables(requested_tables: List[str], available_tables: List[str]) -> List[str]:
    if "all" in requested_tables:
        return sorted(available_tables)

    unknown_tables = sorted(set(requested_tables) - set(available_tables))
    if unknown_tables:
        raise ValueError(f"Unknown table(s): {', '.join(unknown_tables)}")

    return requested_tables


def main() -> None:
    args = parse_args()
    table_sources = discover_table_sources(args.source_mode, args.raw_landing_root)
    selected_tables = resolve_tables(args.tables, list(table_sources.keys()))
    schema_contracts = load_schema_contracts(args.schema_contract_path)

    spark = build_spark()
    print("Spark Session Created")
    print(f"[RUN_ID] {args.run_id}")
    print(f"[MODE] {args.mode}")
    print(f"[SOURCE_MODE] {args.source_mode}")
    print(f"[RAW_LANDING_ROOT] {args.raw_landing_root}")
    print(f"[TABLES] {', '.join(selected_tables)}")

    try:
        ensure_manifest(spark)
        for table_name in selected_tables:
            print(f"Processing {table_name}...")
            candidate_files = table_sources[table_name]
            new_files = candidate_files if args.force_reprocess else filter_new_files(
                spark, table_name, candidate_files
            )

            if not new_files:
                print(f"[SKIP] No new CSV files for {table_name}")
                continue

            if not args.skip_file_validation:
                valid_files, validation_results = validate_incoming_files(
                    table_name,
                    new_files,
                    schema_contracts,
                )
                append_file_validation_results(spark, args.run_id, validation_results)
                print_file_validation_report(table_name, validation_results)

                invalid_files = [
                    result for result in validation_results if result["status"] != "PASS"
                ]
                if invalid_files and not args.skip_invalid_files:
                    invalid_names = [result["source_file_name"] for result in invalid_files]
                    raise ValueError(
                        f"Incoming file validation failed for table={table_name}. "
                        f"Rejected files={invalid_names}"
                    )
                new_files = valid_files

                if not new_files:
                    print(f"[SKIP] No valid CSV files for {table_name}")
                    continue

            print(f"[FILES] {table_name}: {len(new_files)} new of {len(candidate_files)} discovered")
            df = load_csv_files(spark, new_files)
            df = apply_bronze_metadata(df, args.run_id)
            file_row_counts = collect_file_row_counts(df)
            row_count = write_delta(df, table_name, args.mode)
            append_manifest(spark, table_name, new_files, args.run_id, file_row_counts)
            register_bronze_table(spark, table_name)
    finally:
        spark.stop()
        print("ALL DELTA TABLES CREATED SUCCESSFULLY")

if __name__ == "__main__":
    main()


# chnage add 
