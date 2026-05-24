from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import LongType, StringType, StructField, StructType, TimestampType


SPARK_WAREHOUSE_DIR = "/app/spark-warehouse"
HIVE_METASTORE_URL = "jdbc:derby:;databaseName=/app/metastore_db;create=true"

DEFAULT_LANDING_ROOT = "/app/data/upcoming_data"
DEFAULT_BRONZE_ROOT = "/app/scripts/bronze_layer"
DEFAULT_LANDING_CONTRACT_PATH = "/app/scripts/spark/schema_contracts/incoming_csv_schema_contracts.json"
DEFAULT_BRONZE_CONTRACT_PATH = "/app/scripts/spark/schema_contracts/bronze_schema_contracts.json"
DEFAULT_REPORT_PATH = "/app/scripts/silver_layer/_validation/schema_validation_results"
DEFAULT_QUARANTINE_ROOT = "/app/scripts/silver_layer/quarantine"

REQUIRED_BRONZE_METADATA_COLUMNS = {
    "bronze_ingest_ts": "timestamp",
    "bronze_source_file": "string",
    "bronze_batch_id": "string",
}

REPORT_SCHEMA = StructType(
    [
        StructField("validation_run_id", StringType(), False),
        StructField("source_layer", StringType(), False),
        StructField("table_name", StringType(), False),
        StructField("validation_ts", TimestampType(), False),
        StructField("status", StringType(), False),
        StructField("missing_columns", StringType(), False),
        StructField("new_columns", StringType(), False),
        StructField("datatype_mismatches", StringType(), False),
        StructField("metadata_issues", StringType(), False),
        StructField("actual_schema_json", StringType(), False),
        StructField("expected_schema_json", StringType(), False),
        StructField("row_count", LongType(), False),
    ]
)


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def build_spark(app_name: str, master: str) -> SparkSession:
    return (
        SparkSession.builder.appName(app_name)
        .master(master)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.catalogImplementation", "hive")
        .config("spark.sql.warehouse.dir", SPARK_WAREHOUSE_DIR)
        .config("javax.jdo.option.ConnectionURL", HIVE_METASTORE_URL)
        .enableHiveSupport()
        .getOrCreate()
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate incoming CSV or Bronze Delta schemas against JSON contracts."
    )
    parser.add_argument("--master", default="spark://spark-master:7077")
    parser.add_argument(
        "--source-layer",
        choices=["landing", "bronze"],
        default="landing",
        help="landing validates CSV files under upcoming_data; bronze validates Bronze Delta tables.",
    )
    parser.add_argument("--landing-root", default=DEFAULT_LANDING_ROOT)
    parser.add_argument("--bronze-root", default=DEFAULT_BRONZE_ROOT)
    parser.add_argument(
        "--contract-path",
        default=None,
        help="Optional JSON schema contract. Defaults based on --source-layer.",
    )
    parser.add_argument("--report-path", default=DEFAULT_REPORT_PATH)
    parser.add_argument("--quarantine-root", default=DEFAULT_QUARANTINE_ROOT)
    parser.add_argument("--tables", nargs="+", default=["all"])
    parser.add_argument("--run-id", default="manual_schema_validation")
    parser.add_argument(
        "--allow-new-columns",
        action="store_true",
        help="Report new columns as drift but do not fail validation for them.",
    )
    parser.add_argument(
        "--skip-quarantine",
        action="store_true",
        help="Do not write failed rows to schema quarantine tables.",
    )
    return parser.parse_args()


def default_contract_path(source_layer: str, contract_path: str | None) -> str:
    if contract_path:
        return contract_path
    if source_layer == "landing":
        return DEFAULT_LANDING_CONTRACT_PATH
    return DEFAULT_BRONZE_CONTRACT_PATH


def load_contracts(contract_path: str) -> Dict[str, Dict[str, str]]:
    with open(contract_path, "r", encoding="utf-8") as handle:
        raw_contracts = json.load(handle)
    return {
        table: {column: dtype.lower() for column, dtype in schema.items()}
        for table, schema in raw_contracts.items()
    }


def list_delta_dirs(path: Path) -> List[str]:
    if not path.exists():
        return []
    return sorted(
        child.name
        for child in path.iterdir()
        if child.is_dir() and (child / "_delta_log").exists()
    )


def list_landing_tables(path: Path) -> List[str]:
    if not path.exists():
        return []
    return sorted(
        child.name
        for child in path.iterdir()
        if child.is_dir() and list(child.rglob("*.csv"))
    )


def resolve_tables(requested: List[str], source_layer: str, landing_root: Path, bronze_root: Path) -> List[str]:
    if "all" not in requested:
        return requested
    if source_layer == "landing":
        return list_landing_tables(landing_root)
    return list_delta_dirs(bronze_root)


def landing_files_for_table(landing_root: Path, table_name: str) -> List[str]:
    table_root = landing_root / table_name
    if not table_root.exists():
        return []
    return sorted(str(path) for path in table_root.rglob("*.csv"))


def read_source_df(
    spark: SparkSession,
    source_layer: str,
    table_name: str,
    landing_root: Path,
    bronze_root: Path,
) -> DataFrame:
    if source_layer == "bronze":
        bronze_path = bronze_root / table_name
        logging.info("Reading Bronze Delta table=%s path=%s", table_name, bronze_path)
        return spark.read.format("delta").load(str(bronze_path))

    file_paths = landing_files_for_table(landing_root, table_name)
    if not file_paths:
        raise FileNotFoundError(f"No incoming CSV files found for table={table_name} under {landing_root}")

    logging.info("Reading incoming CSV table=%s files=%s", table_name, len(file_paths))
    return spark.read.option("header", True).option("inferSchema", True).csv(file_paths)


def normalize_type(data_type: str) -> str:
    aliases = {
        "integer": "int",
        "bigint": "long",
    }
    lowered = data_type.lower()
    return aliases.get(lowered, lowered)


def dataframe_schema_map(df: DataFrame) -> Dict[str, str]:
    return {
        field.name: normalize_type(field.dataType.simpleString())
        for field in df.schema.fields
    }


def find_missing_columns(expected: Dict[str, str], actual: Dict[str, str]) -> List[str]:
    return sorted(column for column in expected if column not in actual)


def find_new_columns(expected: Dict[str, str], actual: Dict[str, str]) -> List[str]:
    return sorted(column for column in actual if column not in expected)


def find_type_mismatches(expected: Dict[str, str], actual: Dict[str, str]) -> List[Dict[str, str]]:
    mismatches = []
    for column, expected_type in expected.items():
        if column not in actual:
            continue
        actual_type = actual[column]
        if normalize_type(expected_type) != normalize_type(actual_type):
            mismatches.append(
                {
                    "column": column,
                    "expected": normalize_type(expected_type),
                    "actual": normalize_type(actual_type),
                }
            )
    return mismatches


def find_metadata_issues(source_layer: str, actual: Dict[str, str]) -> List[Dict[str, str]]:
    if source_layer == "landing":
        return []

    issues = []
    for column, expected_type in REQUIRED_BRONZE_METADATA_COLUMNS.items():
        if column not in actual:
            issues.append({"column": column, "issue": "missing_metadata_column"})
            continue
        actual_type = actual[column]
        if normalize_type(actual_type) != expected_type:
            issues.append(
                {
                    "column": column,
                    "issue": "metadata_type_mismatch",
                    "expected": expected_type,
                    "actual": actual_type,
                }
            )
    return issues


def validation_status(
    missing_columns: Iterable[str],
    new_columns: Iterable[str],
    type_mismatches: Iterable[Dict[str, str]],
    metadata_issues: Iterable[Dict[str, str]],
    allow_new_columns: bool,
) -> str:
    has_critical_drift = bool(list(missing_columns)) or bool(list(type_mismatches)) or bool(list(metadata_issues))
    has_new_columns = bool(list(new_columns))
    if has_critical_drift or (has_new_columns and not allow_new_columns):
        return "FAIL"
    return "PASS"


def json_dump(value) -> str:
    return json.dumps(value, sort_keys=True)


def print_issue_block(title: str, rows: List[str]) -> None:
    if not rows:
        print(f"{title}: none")
        return

    print(f"{title}:")
    for row in rows:
        print(f"  - {row}")


def format_type_mismatches(type_mismatches: List[Dict[str, str]]) -> List[str]:
    return [
        (
            f"{item['column']} | expected={item['expected']} | "
            f"actual={item['actual']} | action=fix incoming file, Bronze cast, or schema contract"
        )
        for item in type_mismatches
    ]


def format_metadata_issues(metadata_issues: List[Dict[str, str]]) -> List[str]:
    formatted = []
    for item in metadata_issues:
        if item["issue"] == "missing_metadata_column":
            formatted.append(f"{item['column']} | issue=missing | action=check Bronze ingestion metadata")
        else:
            formatted.append(
                f"{item['column']} | issue=type_mismatch | expected={item['expected']} | "
                f"actual={item['actual']} | action=fix Bronze metadata type"
            )
    return formatted


def print_table_report(
    source_layer: str,
    table_name: str,
    status: str,
    row_count: int,
    missing_columns: List[str],
    new_columns: List[str],
    type_mismatches: List[Dict[str, str]],
    metadata_issues: List[Dict[str, str]],
    allow_new_columns: bool,
) -> None:
    print("\n" + "=" * 96)
    print(
        f"SCHEMA VALIDATION | source={source_layer} | table={table_name} | "
        f"status={status} | rows={row_count}"
    )
    print("=" * 96)

    if status == "PASS":
        print("Result: PASS. Schema contract matched. This data can continue to the next stage.")
    else:
        print("Result: FAIL. Pipeline should stop before the next stage.")

    print_issue_block(
        "Missing columns",
        [f"{column} | action=add column in source or remove from contract" for column in missing_columns],
    )
    print_issue_block(
        "New columns",
        [
            (
                f"{column} | action={'allowed by --allow-new-columns' if allow_new_columns else 'review drift or add to contract'}"
            )
            for column in new_columns
        ],
    )
    print_issue_block("Datatype mismatches", format_type_mismatches(type_mismatches))
    print_issue_block("Metadata issues", format_metadata_issues(metadata_issues))


def print_final_summary(report_rows: List[Dict[str, object]]) -> None:
    print("\n" + "=" * 96)
    print("SCHEMA VALIDATION SUMMARY")
    print("=" * 96)
    print(f"{'SOURCE':10} {'TABLE':35} {'STATUS':8} {'ROWS':12} {'MISS':6} {'NEW':6} {'TYPE':6} {'META':6}")
    print("-" * 96)

    for row in report_rows:
        missing_count = len(json.loads(row["missing_columns"]))
        new_count = len(json.loads(row["new_columns"]))
        type_count = len(json.loads(row["datatype_mismatches"]))
        meta_count = len(json.loads(row["metadata_issues"]))
        print(
            f"{row['source_layer'][:10]:10} {row['table_name'][:35]:35} {row['status']:8} "
            f"{row['row_count']:<12} {missing_count:<6} {new_count:<6} {type_count:<6} {meta_count:<6}"
        )

    failed_tables = [row["table_name"] for row in report_rows if row["status"] != "PASS"]
    print("-" * 96)
    print(f"validated_tables={len(report_rows)}")
    print(f"failed_tables={failed_tables if failed_tables else 'none'}")
    if failed_tables:
        print("Decision: FAIL. Pipeline must stop before the next stage.")
    else:
        print("Decision: PASS. Pipeline can continue.")


def make_report_row(
    run_id: str,
    source_layer: str,
    table_name: str,
    status: str,
    row_count: int,
    expected_schema: Dict[str, str],
    actual_schema: Dict[str, str],
    missing_columns: List[str],
    new_columns: List[str],
    type_mismatches: List[Dict[str, str]],
    metadata_issues: List[Dict[str, str]],
) -> Dict[str, object]:
    return {
        "validation_run_id": run_id,
        "source_layer": source_layer,
        "table_name": table_name,
        "validation_ts": datetime.utcnow(),
        "status": status,
        "missing_columns": json_dump(missing_columns),
        "new_columns": json_dump(new_columns),
        "datatype_mismatches": json_dump(type_mismatches),
        "metadata_issues": json_dump(metadata_issues),
        "actual_schema_json": json_dump(actual_schema),
        "expected_schema_json": json_dump(expected_schema),
        "row_count": int(row_count),
    }


def register_report_table(spark: SparkSession, report_path: str) -> None:
    spark.sql("CREATE DATABASE IF NOT EXISTS silver_control")
    spark.sql(
        "CREATE TABLE IF NOT EXISTS silver_control.schema_validation_results "
        f"USING DELTA LOCATION '{report_path}'"
    )


def append_report_rows(spark: SparkSession, report_path: str, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    report_df = spark.createDataFrame(rows, REPORT_SCHEMA)
    (
        report_df.write.format("delta")
        .mode("append")
        .option("mergeSchema", "true")
        .save(report_path)
    )
    register_report_table(spark, report_path)


def write_schema_quarantine(
    df: DataFrame,
    source_layer: str,
    table_name: str,
    quarantine_root: str,
    run_id: str,
    validation_errors: Dict[str, object],
) -> None:
    quarantine_path = f"{quarantine_root}/{source_layer}_{table_name}_schema_quarantine"
    (
        df.withColumn("schema_validation_run_id", F.lit(run_id))
        .withColumn("schema_validation_source_layer", F.lit(source_layer))
        .withColumn("schema_validation_ts", F.current_timestamp())
        .withColumn("schema_validation_status", F.lit("FAIL"))
        .withColumn("schema_validation_errors", F.lit(json_dump(validation_errors)))
        .write.format("delta")
        .mode("append")
        .option("mergeSchema", "true")
        .save(quarantine_path)
    )


def register_quarantine_table(spark: SparkSession, source_layer: str, table_name: str, quarantine_root: str) -> None:
    quarantine_path = f"{quarantine_root}/{source_layer}_{table_name}_schema_quarantine"
    spark.sql("CREATE DATABASE IF NOT EXISTS silver_quarantine")
    spark.sql(
        f"CREATE TABLE IF NOT EXISTS silver_quarantine.{source_layer}_{table_name}_schema_quarantine "
        f"USING DELTA LOCATION '{quarantine_path}'"
    )


def validate_one_table(
    spark: SparkSession,
    source_layer: str,
    table_name: str,
    landing_root: Path,
    bronze_root: Path,
    expected_schema: Dict[str, str],
    run_id: str,
    allow_new_columns: bool,
    skip_quarantine: bool,
    quarantine_root: str,
) -> Dict[str, object]:
    df = read_source_df(spark, source_layer, table_name, landing_root, bronze_root)
    actual_schema = dataframe_schema_map(df)
    row_count = df.count()

    missing_columns = find_missing_columns(expected_schema, actual_schema)
    new_columns = find_new_columns(expected_schema, actual_schema)
    type_mismatches = find_type_mismatches(expected_schema, actual_schema)
    metadata_issues = find_metadata_issues(source_layer, actual_schema)
    status = validation_status(
        missing_columns,
        new_columns,
        type_mismatches,
        metadata_issues,
        allow_new_columns,
    )

    validation_errors = {
        "missing_columns": missing_columns,
        "new_columns": new_columns,
        "datatype_mismatches": type_mismatches,
        "metadata_issues": metadata_issues,
    }

    print_table_report(
        source_layer=source_layer,
        table_name=table_name,
        status=status,
        row_count=row_count,
        missing_columns=missing_columns,
        new_columns=new_columns,
        type_mismatches=type_mismatches,
        metadata_issues=metadata_issues,
        allow_new_columns=allow_new_columns,
    )

    if status == "FAIL" and not skip_quarantine:
        logging.warning("Schema validation failed for source=%s table=%s. Writing quarantine.", source_layer, table_name)
        write_schema_quarantine(df, source_layer, table_name, quarantine_root, run_id, validation_errors)
        register_quarantine_table(spark, source_layer, table_name, quarantine_root)

    return make_report_row(
        run_id=run_id,
        source_layer=source_layer,
        table_name=table_name,
        status=status,
        row_count=row_count,
        expected_schema=expected_schema,
        actual_schema=actual_schema,
        missing_columns=missing_columns,
        new_columns=new_columns,
        type_mismatches=type_mismatches,
        metadata_issues=metadata_issues,
    )


def main() -> None:
    configure_logging()
    args = parse_args()
    landing_root = Path(args.landing_root)
    bronze_root = Path(args.bronze_root)
    contract_path = default_contract_path(args.source_layer, args.contract_path)
    contracts = load_contracts(contract_path)
    tables = resolve_tables(args.tables, args.source_layer, landing_root, bronze_root)

    if not tables:
        raise ValueError(
            f"No tables selected. source_layer={args.source_layer}, "
            f"landing_root={landing_root}, bronze_root={bronze_root}"
        )

    spark = build_spark(f"{args.source_layer}-schema-validation", args.master)
    try:
        report_rows = []
        failed_tables = []
        for table_name in tables:
            if table_name not in contracts:
                raise ValueError(f"No schema contract found for source={args.source_layer}, table={table_name}")
            report_row = validate_one_table(
                spark=spark,
                source_layer=args.source_layer,
                table_name=table_name,
                landing_root=landing_root,
                bronze_root=bronze_root,
                expected_schema=contracts[table_name],
                run_id=args.run_id,
                allow_new_columns=args.allow_new_columns,
                skip_quarantine=args.skip_quarantine,
                quarantine_root=args.quarantine_root,
            )
            report_rows.append(report_row)
            if report_row["status"] != "PASS":
                failed_tables.append(table_name)

        append_report_rows(spark, args.report_path, report_rows)
        print_final_summary(report_rows)

        if failed_tables:
            raise ValueError(f"Schema validation failed. failed_tables={failed_tables}")
    except Exception:
        logging.exception("Schema validation failed.")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(1)
