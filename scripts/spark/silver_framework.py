from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)
from pyspark.sql.window import Window


DEFAULT_SCHEMA_CONFIG_ROOT = "/app/configs/schemas"
DEFAULT_QUARANTINE_ROOT = "/app/scripts/silver_layer/quarantine"
RECONCILIATION_LOG_PATH = "/app/scripts/silver_layer/_control/reconciliation_log"
DEFAULT_DOMAIN_RULES_PATH = "/app/configs/quality/domain_rules.json"
RAW_PREFIX = "__silver_raw__"
REASONS_COL = "validation_reasons"

RECONCILIATION_SCHEMA = StructType(
    [
        StructField("run_id", StringType(), False),
        StructField("dataset_name", StringType(), False),
        StructField("bronze_count", LongType(), False),
        StructField("silver_valid_count", LongType(), False),
        StructField("silver_quarantine_count", LongType(), False),
        StructField("difference", LongType(), False),
        StructField("status", StringType(), False),
        StructField("created_ts", TimestampType(), False),
    ]
)


def load_schema_config(table_name: str, config_root: str = DEFAULT_SCHEMA_CONFIG_ROOT) -> dict[str, Any] | None:
    config_path = Path(config_root) / f"{table_name}_schema.json"
    if not config_path.exists():
        return None
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def load_domain_rules(
    rules_path: str = DEFAULT_DOMAIN_RULES_PATH,
) -> dict[str, Any]:
    path = Path(rules_path)

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def expected_columns(schema_config: dict[str, Any]) -> list[str]:
    return [column["name"] for column in schema_config.get("columns", [])]


def raw_col_name(column_name: str) -> str:
    return f"{RAW_PREFIX}{column_name}"


def helper_columns(df: DataFrame) -> list[str]:
    return [column for column in df.columns if column.startswith(RAW_PREFIX)]


def schema_type_mismatches(existing_df: DataFrame, incoming_df: DataFrame) -> list[str]:
    existing_types = {field.name: field.dataType.simpleString() for field in existing_df.schema.fields}
    incoming_types = {field.name: field.dataType.simpleString() for field in incoming_df.schema.fields}
    mismatches = []

    for column_name in sorted(set(existing_types).intersection(incoming_types)):
        if existing_types[column_name] != incoming_types[column_name]:
            mismatches.append(
                f"{column_name}: existing={existing_types[column_name]}, incoming={incoming_types[column_name]}"
            )

    return mismatches


def ensure_delta_schema_compatible(
    spark: SparkSession,
    delta_path: str,
    incoming_df: DataFrame,
    table_label: str,
    mode: str = "append",
) -> None:
    if mode == "overwrite" or not (Path(delta_path) / "_delta_log").exists():
        return

    existing_df = spark.read.format("delta").load(delta_path)
    mismatches = schema_type_mismatches(existing_df, incoming_df)
    if mismatches:
        mismatch_text = "; ".join(mismatches)
        raise ValueError(
            f"Existing Delta schema is incompatible for {table_label}: {mismatch_text}. "
            "Run a one-time full Silver schema migration with --load-type full --mode overwrite "
            "for this table, then continue incremental appends."
        )


def normalize_name(name: str) -> str:
    normalized = name.strip().lower()
    normalized = normalized.replace("+", "_plus")
    normalized = normalized.replace(">=", "_greater_equal_")
    normalized = normalized.replace(">", "_greater_")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def find_source_column(df_columns: Iterable[str], canonical_col: str, aliases: Iterable[str]) -> str | None:
    original_by_normalized = {normalize_name(col_name): col_name for col_name in df_columns}
    for alias in [canonical_col, *aliases]:
        normalized_alias = normalize_name(alias)
        if normalized_alias in original_by_normalized:
            return original_by_normalized[normalized_alias]
    return None


def _coalesce_date(column_expr, formats: list[str]):
    parsed = [F.to_date(column_expr.cast("string"), fmt) for fmt in formats]
    parsed.append(column_expr.cast("date"))
    return F.coalesce(*parsed)


def _coalesce_timestamp(column_expr, formats: list[str]):
    # Spark-generated timestamp values include fractional seconds. The default
    # cast handles those and common ISO values without raising parser errors.
    return column_expr.cast("timestamp")


def quote_identifier(name: str) -> str:
    return f"`{name.replace('`', '``')}`"


def sql_string_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def cast_raw_column(raw_name: str, data_type: str, schema_config: dict[str, Any]):
    normalized_type = data_type.lower()
    if normalized_type == "date":
        return _coalesce_date(F.col(raw_name), schema_config.get("date_formats", ["dd-MM-yyyy", "yyyy-MM-dd"]))
    if normalized_type == "timestamp":
        return _coalesce_timestamp(
            F.col(raw_name),
            schema_config.get("timestamp_formats", ["yyyy-MM-dd'T'HH:mm:ss'Z'", "yyyy-MM-dd HH:mm:ss"]),
        )
    if normalized_type == "string":
        return F.trim(F.col(raw_name).cast("string"))
    quoted_raw = quote_identifier(raw_name)
    return F.expr(f"try_cast({quoted_raw} as {normalized_type})")


def cast_for_type(column_expr, data_type: str, schema_config: dict[str, Any]):
    normalized_type = data_type.lower()
    if normalized_type == "date":
        return _coalesce_date(column_expr, schema_config.get("date_formats", ["dd-MM-yyyy", "yyyy-MM-dd"]))
    if normalized_type == "timestamp":
        return _coalesce_timestamp(
            column_expr,
            schema_config.get("timestamp_formats", ["yyyy-MM-dd'T'HH:mm:ss'Z'", "yyyy-MM-dd HH:mm:ss"]),
        )
    if normalized_type == "string":
        return F.trim(column_expr.cast("string"))
    return column_expr.cast(normalized_type)


def normalize_schema(df: DataFrame, schema_config: dict[str, Any], run_id: str) -> tuple[DataFrame, dict[str, Any]]:
    raw_selected = []
    mapped_columns: dict[str, str | None] = {}
    missing_columns: list[str] = []

    for column_config in schema_config.get("columns", []):
        canonical_col = column_config["name"]
        aliases = column_config.get("aliases", [])
        data_type = column_config.get("type", "string")
        source_col = find_source_column(df.columns, canonical_col, aliases)
        mapped_columns[canonical_col] = source_col

        if source_col:
            source_expr = F.col(f"`{source_col}`")
        elif canonical_col == "silver_processed_ts":
            source_expr = F.current_timestamp()
        elif canonical_col == "silver_run_id":
            source_expr = F.lit(run_id)
        elif canonical_col in ("partition_year", "partition_month"):
            source_expr = F.lit(None)
        else:
            source_expr = F.lit(None)
            missing_columns.append(canonical_col)

        raw_selected.append(source_expr.cast("string").alias(raw_col_name(canonical_col)))

    normalized_df = df.select(*raw_selected)

    for column_config in schema_config.get("columns", []):
        canonical_col = column_config["name"]
        data_type = column_config.get("type", "string")
        normalized_df = normalized_df.withColumn(
            canonical_col,
            cast_raw_column(raw_col_name(canonical_col), data_type, schema_config),
        )

    if "date" in normalized_df.columns:
        if "partition_year" in normalized_df.columns:
            normalized_df = normalized_df.withColumn("partition_year", F.year(F.col("date")).cast("int"))
        if "partition_month" in normalized_df.columns:
            normalized_df = normalized_df.withColumn("partition_month", F.month(F.col("date")).cast("int"))

    ordered_columns = expected_columns(schema_config)
    normalized_df = normalized_df.select(*ordered_columns, *[raw_col_name(column) for column in ordered_columns])

    actual_types = {field.name: field.dataType.simpleString() for field in normalized_df.schema.fields}
    report = {
        "dataset_name": schema_config.get("dataset_name"),
        "mapped_columns": mapped_columns,
        "missing_columns": missing_columns,
        "output_columns": ordered_columns,
        "output_types": {column: actual_types.get(column) for column in ordered_columns},
    }
    return normalized_df, report


def _has_raw_value(column_name: str):
    raw_name = raw_col_name(column_name)
    return F.col(raw_name).isNotNull() & (F.trim(F.col(raw_name).cast("string")) != "")


def add_reason(df: DataFrame, condition, reason: str) -> DataFrame:
    return df.withColumn(
        REASONS_COL,
        F.when(condition, F.array_union(F.col(REASONS_COL), F.array(F.lit(reason)))).otherwise(F.col(REASONS_COL)),
    )

def add_domain_rules(
    df: DataFrame,
    domain_rules: dict[str, Any],
) -> DataFrame:

    result_df = df

    # ---------------------------------------------------------
    # Date relationships
    # Example:
    # end_date >= start_date
    # ---------------------------------------------------------

    for rule in domain_rules.get("date_relationships", []):

        left_column = rule["left"]
        operator = rule["operator"]
        right_column = rule["right"]
        reason = rule["reason"]

        if (
            left_column not in result_df.columns
            or right_column not in result_df.columns
        ):
            continue

        left_expr = F.col(left_column)
        right_expr = F.col(right_column)

        if operator == ">=":

            invalid_condition = (
                left_expr.isNotNull()
                & right_expr.isNotNull()
                & (left_expr < right_expr)
            )

        elif operator == ">":

            invalid_condition = (
                left_expr.isNotNull()
                & right_expr.isNotNull()
                & (left_expr <= right_expr)
            )

        elif operator == "<=":

            invalid_condition = (
                left_expr.isNotNull()
                & right_expr.isNotNull()
                & (left_expr > right_expr)
            )

        elif operator == "<":

            invalid_condition = (
                left_expr.isNotNull()
                & right_expr.isNotNull()
                & (left_expr >= right_expr)
            )

        elif operator == "==":

            invalid_condition = (
                left_expr.isNotNull()
                & right_expr.isNotNull()
                & (left_expr != right_expr)
            )

        else:

            raise ValueError(
                f"Unsupported domain rule operator: {operator}"
            )

        result_df = add_reason(
            result_df,
            invalid_condition,
            reason,
        )

    # ---------------------------------------------------------
    # Sum relationships
    # Example:
    # voter_total =
    # male_voters + female_voters + other_voters
    # ---------------------------------------------------------

    for rule in domain_rules.get("sum_relationships", []):

        target_column = rule["target"]
        source_columns = rule["columns"]
        reason = rule["reason"]

        required_columns = [target_column] + source_columns

        if any(
            column not in result_df.columns
            for column in required_columns
        ):
            continue

        target_expr = F.col(target_column)

        source_expr = None

        for column in source_columns:

            if source_expr is None:

                source_expr = F.col(column)

            else:

                source_expr = source_expr + F.col(column)

        all_values_present = target_expr.isNotNull()

        for column in source_columns:

            all_values_present = (
                all_values_present
                & F.col(column).isNotNull()
            )

        invalid_condition = (
            all_values_present
            & (target_expr != source_expr)
        )

        result_df = add_reason(
            result_df,
            invalid_condition,
            reason,
        )

    # ---------------------------------------------------------
    # Arithmetic relationships
    # Example:
    # net_change =
    # new_registrations - deletions
    # ---------------------------------------------------------

    for rule in domain_rules.get("arithmetic_relationships", []):

        target_column = rule["target"]
        left_column = rule["left"]
        operator = rule["operator"]
        right_column = rule["right"]
        reason = rule["reason"]

        required_columns = [
            target_column,
            left_column,
            right_column,
        ]

        if any(
            column not in result_df.columns
            for column in required_columns
        ):
            continue

        target_expr = F.col(target_column)
        left_expr = F.col(left_column)
        right_expr = F.col(right_column)

        all_values_present = (
            target_expr.isNotNull()
            & left_expr.isNotNull()
            & right_expr.isNotNull()
        )

        if operator == "-":

            expected_expr = left_expr - right_expr

        elif operator == "+":

            expected_expr = left_expr + right_expr

        else:

            raise ValueError(
                f"Unsupported arithmetic relationship operator: {operator}"
            )

        invalid_condition = (
            all_values_present
            & (target_expr != expected_expr)
        )

        result_df = add_reason(
            result_df,
            invalid_condition,
            reason,
        )

    return result_df


def add_duplicate_key_reason(
    df: DataFrame,
    key_columns: list[str],
) -> DataFrame:

    if (
        not key_columns
        or any(column not in df.columns for column in key_columns)
    ):
        return df

    order_columns = []

    # 1. Latest source ingestion wins
    if "ingest_ts" in df.columns:
        order_columns.append(F.col("ingest_ts").desc())

    # 2. Tie-breaker: latest Bronze ingestion
    if "bronze_ingest_ts" in df.columns:
        order_columns.append(F.col("bronze_ingest_ts").desc())

    # 3. Tie-breaker: Bronze batch
    if "bronze_batch_id" in df.columns:
        order_columns.append(F.col("bronze_batch_id").desc())

    # 4. Tie-breaker: source file
    if "bronze_source_file" in df.columns:
        order_columns.append(F.col("bronze_source_file").desc())

    # If no ordering metadata exists, keep the old duplicate behavior
    if not order_columns:
        duplicate_count = F.count(F.lit(1)).over(
            Window.partitionBy(
                *[F.col(column) for column in key_columns]
            )
        )

        return (
            df.withColumn(
                "__silver_duplicate_key_count",
                duplicate_count,
            )
            .transform(
                lambda current_df: add_reason(
                    current_df,
                    F.col("__silver_duplicate_key_count") > 1,
                    "duplicate_business_key",
                )
            )
            .drop("__silver_duplicate_key_count")
        )

    duplicate_window = (
        Window
        .partitionBy(
            *[F.col(column) for column in key_columns]
        )
        .orderBy(*order_columns)
    )

    return (
        df.withColumn(
            "__duplicate_rank",
            F.row_number().over(duplicate_window),
        )
        .transform(
            lambda current_df: add_reason(
                current_df,
                F.col("__duplicate_rank") > 1,
                "duplicate_business_key",
            )
        )
        .drop("__duplicate_rank")
    )


def validate_types(
    df: DataFrame,
    schema_config: dict[str, Any],
    domain_rules: dict[str, Any] | None = None,
) -> tuple[DataFrame, DataFrame]:
    
    checked_df = df.withColumn(REASONS_COL, F.array().cast("array<string>"))

    for column_config in schema_config.get("columns", []):
        column_name = column_config["name"]
        data_type = column_config.get("type", "string").lower()
        nullable = bool(column_config.get("nullable", True))

        if not nullable:
            if data_type == "string":
                missing_condition = F.col(column_name).isNull() | (F.trim(F.col(column_name).cast("string")) == "")
            else:
                missing_condition = F.col(column_name).isNull()
            checked_df = add_reason(checked_df, missing_condition, f"{column_name}_required")

        if data_type in ("date", "timestamp"):
            checked_df = add_reason(
                checked_df,
                _has_raw_value(column_name) & F.col(column_name).isNull(),
                f"{column_name}_invalid_{data_type}",
            )
        elif data_type in ("int", "integer", "bigint", "long", "double", "float", "short"):
            checked_df = add_reason(
                checked_df,
                _has_raw_value(column_name) & F.col(column_name).isNull(),
                f"{column_name}_invalid_numeric",
            )

        min_value = column_config.get("min_value")
        if min_value is not None:
            checked_df = add_reason(
                checked_df,
                F.col(column_name).isNotNull() & (F.col(column_name).cast("double") < float(min_value)),
                f"{column_name}_below_min_{min_value}",
            )

        max_value = column_config.get("max_value")
        if max_value is not None:
            checked_df = add_reason(
                checked_df,
                F.col(column_name).isNotNull() & (F.col(column_name).cast("double") > float(max_value)),
                f"{column_name}_above_max_{max_value}",
            )

        pattern = column_config.get("pattern")
        if pattern:
            checked_df = add_reason(
                checked_df,
                F.col(column_name).isNotNull() & ~F.col(column_name).cast("string").rlike(pattern),
                f"{column_name}_invalid_pattern",
            )

        max_length = column_config.get("max_length")
        if max_length is not None:
            checked_df = add_reason(
                checked_df,
                F.col(column_name).isNotNull() & (F.length(F.col(column_name).cast("string")) > int(max_length)),
                f"{column_name}_exceeds_length_{max_length}",
            )

    checked_df = add_duplicate_key_reason(
        checked_df,
        schema_config.get("business_keys", []),
    )

    if domain_rules:
        checked_df = add_domain_rules(
            checked_df,
            domain_rules,
        )

    checked_df = checked_df.withColumn(
        "is_quality_valid",
        F.size(F.col(REASONS_COL)) == 0,
    )

    valid_df = checked_df.filter(F.col("is_quality_valid"))
    invalid_df = checked_df.filter(~F.col("is_quality_valid"))

    return clean_valid_output(valid_df), clean_quarantine_output(invalid_df)


def clean_valid_output(df: DataFrame) -> DataFrame:
    return df.drop(*helper_columns(df), REASONS_COL, "is_quality_valid")


def clean_quarantine_output(df: DataFrame) -> DataFrame:
    return df.drop("is_quality_valid")


def add_quarantine_metadata(invalid_df: DataFrame, run_id: str) -> DataFrame:
    return (
        invalid_df.withColumn("quarantine_reason", F.to_json(F.col(REASONS_COL)))
        .withColumn("validation_timestamp", F.current_timestamp())
        .withColumn("validation_run_id", F.lit(run_id))
    )


def write_quarantine(
    spark: SparkSession,
    invalid_df: DataFrame,
    table_name: str,
    quarantine_root: str,
    run_id: str,
    mode: str = "append",
) -> None:
    quarantine_path = f"{quarantine_root}/{table_name}_quality_quarantine"
    output_df = add_quarantine_metadata(invalid_df, run_id)
    ensure_delta_schema_compatible(
        spark=spark,
        delta_path=quarantine_path,
        incoming_df=output_df,
        table_label=f"silver_quarantine.{table_name}_quality_quarantine",
        mode=mode,
    )
    writer = output_df.write.format("delta").mode(mode)
    if mode == "overwrite":
        writer = writer.option("overwriteSchema", "true")
    else:
        writer = writer.option("mergeSchema", "true")
    writer.save(quarantine_path)
    spark.sql("CREATE DATABASE IF NOT EXISTS silver_quarantine")
    spark.sql(
        f"CREATE TABLE IF NOT EXISTS silver_quarantine.{table_name}_quality_quarantine "
        f"USING DELTA LOCATION '{quarantine_path}'"
    )


def register_reconciliation_table(spark: SparkSession, reconciliation_path: str = RECONCILIATION_LOG_PATH) -> None:
    spark.sql("CREATE DATABASE IF NOT EXISTS silver_control")
    spark.sql(
        "CREATE TABLE IF NOT EXISTS silver_control.reconciliation_log "
        f"USING DELTA LOCATION '{reconciliation_path}'"
    )


def calculate_reconciliation_status(
    bronze_count: int,
    silver_valid_count: int,
    silver_quarantine_count: int,
) -> tuple[int, str]:
    difference = int(bronze_count) - int(silver_valid_count) - int(silver_quarantine_count)
    status = "PASS" if difference == 0 else "FAIL"
    return difference, status


def append_reconciliation_log(
    spark: SparkSession,
    run_id: str,
    dataset_name: str,
    bronze_count: int,
    silver_valid_count: int,
    silver_quarantine_count: int,
    reconciliation_path: str = RECONCILIATION_LOG_PATH,
) -> str:
    difference, status = calculate_reconciliation_status(
        bronze_count=bronze_count,
        silver_valid_count=silver_valid_count,
        silver_quarantine_count=silver_quarantine_count,
    )
    row = {
        "run_id": run_id,
        "dataset_name": dataset_name,
        "bronze_count": int(bronze_count),
        "silver_valid_count": int(silver_valid_count),
        "silver_quarantine_count": int(silver_quarantine_count),
        "difference": difference,
        "status": status,
        "created_ts": datetime.utcnow(),
    }
    report_df = spark.createDataFrame([row], RECONCILIATION_SCHEMA)
    report_df.write.format("delta").mode("append").option("mergeSchema", "true").save(reconciliation_path)
    register_reconciliation_table(spark, reconciliation_path)
    return status
