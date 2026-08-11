from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPARK_SCRIPTS = ROOT / "scripts" / "spark"
sys.path.insert(0, str(SPARK_SCRIPTS))

from silver_framework import (  # noqa: E402
    calculate_reconciliation_status,
    load_schema_config,
    normalize_name,
    schema_type_mismatches,
)


class SilverConfigTests(unittest.TestCase):
    def test_all_schema_configs_are_valid_json(self) -> None:
        schema_dir = ROOT / "configs" / "schemas"
        schema_files = sorted(schema_dir.glob("*_schema.json"))
        self.assertGreaterEqual(len(schema_files), 9)

        for schema_file in schema_files:
            with self.subTest(schema_file=schema_file.name):
                config = json.loads(schema_file.read_text(encoding="utf-8"))
                self.assertIn("dataset_name", config)
                self.assertIn("business_keys", config)
                self.assertIn("columns", config)
                self.assertGreater(len(config["columns"]), 0)

                column_names = [column["name"] for column in config["columns"]]
                self.assertEqual(len(column_names), len(set(column_names)))
                for key in config["business_keys"]:
                    self.assertIn(key, column_names)

    def test_biometric_schema_uses_normalized_age_column(self) -> None:
        config = load_schema_config("biometric", str(ROOT / "configs" / "schemas"))
        self.assertIsNotNone(config)
        column_names = [column["name"] for column in config["columns"]]
        self.assertIn("bio_age_17_plus", column_names)
        self.assertNotIn("bio_age_17_", column_names)

    def test_normalize_name_handles_symbols(self) -> None:
        self.assertEqual(normalize_name("Bio Age 17+"), "bio_age_17_plus")
        self.assertEqual(normalize_name("pin-code"), "pin_code")


class ReconciliationTests(unittest.TestCase):
    def test_reconciliation_passes_when_counts_balance(self) -> None:
        difference, status = calculate_reconciliation_status(
            bronze_count=10,
            silver_valid_count=7,
            silver_quarantine_count=3,
        )
        self.assertEqual(difference, 0)
        self.assertEqual(status, "PASS")

    def test_reconciliation_fails_when_counts_do_not_balance(self) -> None:
        difference, status = calculate_reconciliation_status(
            bronze_count=10,
            silver_valid_count=7,
            silver_quarantine_count=2,
        )
        self.assertEqual(difference, 1)
        self.assertEqual(status, "FAIL")


class SilverSparkFrameworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from pyspark.sql import SparkSession
        except Exception as exc:  # pragma: no cover - environment dependent
            raise unittest.SkipTest(f"PySpark unavailable: {exc}") from exc

        os.environ["PYSPARK_PYTHON"] = sys.executable
        os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

        try:
            cls.spark = (
                SparkSession.builder.master("local[1]")
                .appName("silver-framework-tests")
                .config("spark.ui.enabled", "false")
                .getOrCreate()
            )
        except Exception as exc:  # pragma: no cover - environment dependent
            raise unittest.SkipTest(f"Spark session unavailable: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        spark = getattr(cls, "spark", None)
        if spark is not None:
            spark.stop()

    def test_normalization_validation_and_quarantine_routing(self) -> None:
        from silver_framework import normalize_schema, validate_types

        config = load_schema_config("biometric", str(ROOT / "configs" / "schemas"))
        rows = [
            {
                "date": "2025-03-01",
                "state": "X",
                "district": "Y",
                "pincode": "123456",
                "bio_age_5_17": "10",
                "bio_age_17_": "20",
                "bronze_ingest_ts": "2026-01-01T00:00:00Z",
                "bronze_source_file": "file.csv",
                "bronze_batch_id": "batch_1",
            },
            {
                "date": "bad-date",
                "state": "X",
                "district": "Y",
                "pincode": "123",
                "bio_age_5_17": "-1",
                "bio_age_17_": "oops",
                "bronze_ingest_ts": "2026-01-01T00:00:00Z",
                "bronze_source_file": "file.csv",
                "bronze_batch_id": "batch_1",
            },
        ]
        df = self.spark.createDataFrame(rows)
        normalized_df, report = normalize_schema(df, config, "test_run")
        valid_df, invalid_df = validate_types(normalized_df, config)

        self.assertIn("bio_age_17_plus", report["output_columns"])
        try:
            valid_count = valid_df.count()
            invalid_count = invalid_df.count()
            reasons = invalid_df.select("validation_reasons").collect()[0]["validation_reasons"]
        except Exception as exc:  # pragma: no cover - local Spark environment dependent
            raise unittest.SkipTest(f"Spark action failed in this environment: {exc}") from exc

        self.assertEqual(valid_count, 1)
        self.assertEqual(invalid_count, 1)
        self.assertIn("date_required", reasons)
        self.assertIn("date_invalid_date", reasons)
        self.assertIn("pincode_invalid_pattern", reasons)
        self.assertIn("bio_age_5_17_below_min_0", reasons)
        self.assertIn("bio_age_17_plus_invalid_numeric", reasons)

    def test_schema_type_mismatches_reports_incompatible_columns(self) -> None:
        existing_df = self.spark.createDataFrame(
            [{"pincode": 123456, "state": "X"}]
        )
        incoming_df = self.spark.createDataFrame(
            [{"pincode": "123456", "state": "X", "new_col": "allowed"}]
        )

        self.assertEqual(
            schema_type_mismatches(existing_df, incoming_df),
            ["pincode: existing=bigint, incoming=string"],
        )


if __name__ == "__main__":
    unittest.main()
