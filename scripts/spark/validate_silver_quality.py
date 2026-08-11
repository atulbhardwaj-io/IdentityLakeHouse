from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import LongType, StringType, StructField, StructType, TimestampType

from silver_framework import DEFAULT_SCHEMA_CONFIG_ROOT, ensure_delta_schema_compatible, load_schema_config


SPARK_WAREHOUSE_DIR = "/app/spark-warehouse"
HIVE_METASTORE_URL = "jdbc:derby:;databaseName=/app/metastore_db;create=true"
DEFAULT_SILVER_ROOT = "/app/scripts/silver_layer"
DEFAULT_QUALITY_RULES_PATH = "/app/scripts/spark/quality_contracts/silver_quality_rules.json"
DEFAULT_REPORT_PATH = "/app/scripts/silver_layer/_validation/quality_validation_results"
DEFAULT_QUARANTINE_ROOT = "/app/scripts/silver_layer/quarantine"

REPORT_SCHEMA = StructType(
    [
        StructField("validation_run_id", StringType(), False),
        StructField("table_name", StringType(), False),
        StructField("validation_ts", TimestampType(), False),
        StructField("validation_scope", StringType(), False),
        StructField("status", StringType(), False),
        StructField("total_rows", LongType(), False),
        StructField("valid_rows", LongType(), False),
        StructField("invalid_rows", LongType(), False),
        StructField("rule_summary_json", StringType(), False),
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
    parser = argparse.ArgumentParser(description="Validate Silver business quality rules and quarantine invalid rows.")
    parser.add_argument("--master", default="spark://spark-master:7077")
    parser.add_argument("--silver-root", default=DEFAULT_SILVER_ROOT)
    parser.add_argument("--rules-path", default=DEFAULT_QUALITY_RULES_PATH)
    parser.add_argument("--schema-config-root", default=DEFAULT_SCHEMA_CONFIG_ROOT)
    parser.add_argument("--report-path", default=DEFAULT_REPORT_PATH)
    parser.add_argument("--quarantine-root", default=DEFAULT_QUARANTINE_ROOT)
    parser.add_argument("--tables", nargs="+", default=["all"])
    parser.add_argument("--run-id", default="manual_quality_validation")
    parser.add_argument(
        "--validate-scope",
        choices=["incremental", "full"],
        default="incremental",
        help="Validate only rows for --run-id when silver_run_id exists, or validate the full Silver table.",
    )
    parser.add_argument("--fail-on-invalid", action="store_true", help="Exit non-zero when invalid rows are found.")
    return parser.parse_args()


def load_quality_rules(path: str) -> Dict[str, Dict[str, object]]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def rules_from_schema_config(table_name: str, schema_config_root: str) -> Dict[str, object] | None:
    schema_config = load_schema_config(table_name, schema_config_root)
    if not schema_config:
        return None

    required_columns = []
    non_negative_columns = []
    percentage_columns = []
    pincode_column = None

    for column in schema_config.get("columns", []):
        column_name = column["name"]
        if not column.get("nullable", True):
            required_columns.append(column_name)
        if column.get("min_value") == 0:
            non_negative_columns.append(column_name)
        if column.get("min_value") == 0 and column.get("max_value") == 100:
            percentage_columns.append(column_name)
        if column_name == "pincode":
            pincode_column = "pincode"

    return {
        "required_columns": required_columns,
        "non_negative_columns": non_negative_columns,
        "percentage_columns": percentage_columns,
        "pincode_column": pincode_column,
        "duplicate_key_columns": schema_config.get("business_keys", []),
    }


def list_valid_tables(silver_root: Path) -> List[str]:
    if not silver_root.exists():
        return []
    names = []
    for child in silver_root.iterdir():
        if child.is_dir() and child.name.endswith("_valid") and (child / "_delta_log").exists():
            names.append(child.name[: -len("_valid")])
    return sorted(names)


def resolve_tables(requested: List[str], silver_root: Path) -> List[str]:
    if "all" in requested:
        return list_valid_tables(silver_root)
    return requested


def add_reason(df: DataFrame, condition, reason: str) -> DataFrame:
    return df.withColumn(
        "quality_reasons",
        F.when(condition, F.array_union(F.col("quality_reasons"), F.array(F.lit(reason)))).otherwise(
            F.col("quality_reasons")
        ),
    )


def add_duplicate_key_reason(df: DataFrame, key_columns: List[str]) -> DataFrame:
    if not key_columns or any(column not in df.columns for column in key_columns):
        return df

    duplicate_count = F.count(F.lit(1)).over(Window.partitionBy(*[F.col(column) for column in key_columns]))
    return (
        df.withColumn("__duplicate_key_count", duplicate_count)
        .transform(lambda current_df: add_reason(current_df, F.col("__duplicate_key_count") > 1, "duplicate_business_key"))
        .drop("__duplicate_key_count")
    )


def apply_quality_rules(df: DataFrame, rules: Dict[str, object]) -> DataFrame:
    checked_df = df.withColumn("quality_reasons", F.array().cast("array<string>"))

    for column in rules.get("required_columns", []):
        if column not in checked_df.columns:
            checked_df = checked_df.withColumn(column, F.lit(None).cast("string"))
        checked_df = add_reason(
            checked_df,
            F.col(column).isNull() | (F.trim(F.col(column).cast("string")) == ""),
            f"{column}_required",
        )

    pincode_column = rules.get("pincode_column")
    if pincode_column and pincode_column in checked_df.columns:
        checked_df = add_reason(
            checked_df,
            ~F.col(pincode_column).cast("string").rlike(r"^[0-9]{6}$"),
            f"{pincode_column}_must_be_6_digits",
        )

    for column in rules.get("non_negative_columns", []):
        if column in checked_df.columns:
            checked_df = add_reason(
                checked_df,
                F.col(column).isNotNull() & (F.col(column).cast("double") < 0),
                f"{column}_negative",
            )

    for column in rules.get("percentage_columns", []):
        if column in checked_df.columns:
            checked_df = add_reason(
                checked_df,
                F.col(column).isNotNull()
                & ((F.col(column).cast("double") < 0) | (F.col(column).cast("double") > 100)),
                f"{column}_outside_0_100",
            )

    key_columns = rules.get("duplicate_key_columns", [])
    if key_columns and all(column in checked_df.columns for column in key_columns):
        checked_df = add_duplicate_key_reason(checked_df, key_columns)

    return checked_df.withColumn("is_quality_valid", F.size(F.col("quality_reasons")) == 0)


def reason_summary(df: DataFrame) -> Dict[str, int]:
    rows = (
        df.filter(~F.col("is_quality_valid"))
        .select(F.explode("quality_reasons").alias("reason"))
        .groupBy("reason")
        .count()
        .collect()
    )
    return {row["reason"]: int(row["count"]) for row in rows}


def register_report_table(spark: SparkSession, report_path: str) -> None:
    spark.sql("CREATE DATABASE IF NOT EXISTS silver_control")
    spark.sql(
        "CREATE TABLE IF NOT EXISTS silver_control.quality_validation_results "
        f"USING DELTA LOCATION '{report_path}'"
    )


def append_report(spark: SparkSession, report_path: str, row: Dict[str, object]) -> None:
    report_df = spark.createDataFrame([row], REPORT_SCHEMA)
    report_df.write.format("delta").mode("append").option("mergeSchema", "true").save(report_path)
    register_report_table(spark, report_path)


def write_quarantine(
    spark: SparkSession,
    invalid_df: DataFrame,
    table_name: str,
    quarantine_root: str,
    run_id: str,
) -> None:
    quarantine_path = f"{quarantine_root}/{table_name}_quality_quarantine"
    output_df = (
        invalid_df.withColumn("quality_validation_run_id", F.lit(run_id))
        .withColumn("quality_validation_ts", F.current_timestamp())
        .withColumn("quality_reasons_json", F.to_json(F.col("quality_reasons")))
    )
    ensure_delta_schema_compatible(
        spark=spark,
        delta_path=quarantine_path,
        incoming_df=output_df,
        table_label=f"silver_quarantine.{table_name}_quality_quarantine",
    )
    (
        output_df.write.format("delta")
        .mode("append")
        .option("mergeSchema", "true")
        .save(quarantine_path)
    )
    spark.sql("CREATE DATABASE IF NOT EXISTS silver_quarantine")
    spark.sql(
        f"CREATE TABLE IF NOT EXISTS silver_quarantine.{table_name}_quality_quarantine "
        f"USING DELTA LOCATION '{quarantine_path}'"
    )


def validate_table(
    spark: SparkSession,
    table_name: str,
    silver_root: Path,
    rules: Dict[str, object],
    run_id: str,
    validate_scope: str,
    report_path: str,
    quarantine_root: str,
) -> bool:
    silver_path = silver_root / f"{table_name}_valid"
    if not (silver_path / "_delta_log").exists():
        print(f"[SKIP] Silver table not found: {silver_path}")
        return True

    df = spark.read.format("delta").load(str(silver_path))
    if validate_scope == "incremental" and "silver_run_id" in df.columns:
        df = df.filter(F.col("silver_run_id") == F.lit(run_id))

    total_rows = df.count()
    if total_rows == 0:
        print("\n" + "=" * 96)
        print(f"SILVER QUALITY VALIDATION | table={table_name} | status=PASS")
        print("=" * 96)
        print("total_rows=0")
        print("valid_rows=0")
        print("invalid_rows=0")
        print(f"validate_scope={validate_scope}")
        print("rule_summary={}")

        append_report(
            spark,
            report_path,
            {
                "validation_run_id": run_id,
                "table_name": table_name,
                "validation_ts": datetime.utcnow(),
                "validation_scope": validate_scope,
                "status": "PASS",
                "total_rows": 0,
                "valid_rows": 0,
                "invalid_rows": 0,
                "rule_summary_json": "{}",
            },
        )
        return True

    checked_df = apply_quality_rules(df, rules)
    checked_df = checked_df.cache()
    invalid_df = checked_df.filter(~F.col("is_quality_valid"))
    invalid_rows = invalid_df.count()
    valid_rows = total_rows - invalid_rows
    summary = reason_summary(checked_df)
    status = "PASS" if invalid_rows == 0 else "FAIL"

    print("\n" + "=" * 96)
    print(f"SILVER QUALITY VALIDATION | table={table_name} | status={status}")
    print("=" * 96)
    print(f"total_rows={total_rows}")
    print(f"valid_rows={valid_rows}")
    print(f"invalid_rows={invalid_rows}")
    print(f"validate_scope={validate_scope}")
    print(f"rule_summary={json.dumps(summary, sort_keys=True)}")

    if invalid_rows > 0:
        write_quarantine(spark, invalid_df, table_name, quarantine_root, run_id)

    append_report(
        spark,
        report_path,
        {
            "validation_run_id": run_id,
            "table_name": table_name,
            "validation_ts": datetime.utcnow(),
            "validation_scope": validate_scope,
            "status": status,
            "total_rows": int(total_rows),
            "valid_rows": int(valid_rows),
            "invalid_rows": int(invalid_rows),
            "rule_summary_json": json.dumps(summary, sort_keys=True),
        },
    )
    checked_df.unpersist()
    return status == "PASS"


def main() -> None:
    configure_logging()
    args = parse_args()
    silver_root = Path(args.silver_root)
    rules_by_table = load_quality_rules(args.rules_path)
    tables = resolve_tables(args.tables, silver_root)
    if not tables:
        raise ValueError(f"No Silver tables selected. silver_root={silver_root}")

    spark = build_spark("silver-quality-validation", args.master)
    try:
        failed_tables = []
        for table_name in tables:
            table_rules = rules_by_table.get(table_name) or rules_from_schema_config(
                table_name, args.schema_config_root
            )
            if not table_rules:
                print(f"[SKIP] No quality rules for {table_name}")
                continue
            table_passed = validate_table(
                spark=spark,
                table_name=table_name,
                silver_root=silver_root,
                rules=table_rules,
                run_id=args.run_id,
                validate_scope=args.validate_scope,
                report_path=args.report_path,
                quarantine_root=args.quarantine_root,
            )
            if not table_passed:
                failed_tables.append(table_name)

        print("\n" + "=" * 96)
        print("SILVER QUALITY VALIDATION SUMMARY")
        print("=" * 96)
        print(
            f"validated_tables={len([table for table in tables if rules_by_table.get(table) or rules_from_schema_config(table, args.schema_config_root)])}"
        )
        print(f"failed_tables={failed_tables if failed_tables else 'none'}")

        if failed_tables and args.fail_on_invalid:
            raise ValueError(f"Silver quality validation failed. failed_tables={failed_tables}")
    except Exception:
        logging.exception("Silver quality validation failed.")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(1)
