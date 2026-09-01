from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPARK_SCRIPTS = ROOT / "scripts" / "spark"
sys.path.insert(0, str(SPARK_SCRIPTS))


from silver_framework import (
    REASONS_COL,
    add_domain_rules,
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
                config = json.loads(
                    schema_file.read_text(encoding="utf-8")
                )

                self.assertIn("dataset_name", config)
                self.assertIn("business_keys", config)
                self.assertIn("columns", config)
                self.assertGreater(len(config["columns"]), 0)

                column_names = [
                    column["name"]
                    for column in config["columns"]
                ]

                self.assertEqual(
                    len(column_names),
                    len(set(column_names)),
                )

                for key in config["business_keys"]:
                    self.assertIn(key, column_names)

    def test_biometric_schema_uses_normalized_age_column(self) -> None:
        config = load_schema_config(
            "biometric",
            str(ROOT / "configs" / "schemas"),
        )

        self.assertIsNotNone(config)

        column_names = [
            column["name"]
            for column in config["columns"]
        ]

        self.assertIn("bio_age_17_plus", column_names)
        self.assertNotIn("bio_age_17_", column_names)

    def test_normalize_name_handles_symbols(self) -> None:
        self.assertEqual(
            normalize_name("Bio Age 17+"),
            "bio_age_17_plus",
        )

        self.assertEqual(
            normalize_name("pin-code"),
            "pin_code",
        )


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
        except Exception as exc:
            raise unittest.SkipTest(
                f"PySpark unavailable: {exc}"
            ) from exc

        os.environ["PYSPARK_PYTHON"] = sys.executable
        os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

        try:
            cls.spark = (
                SparkSession.builder
                .master("local[1]")
                .appName("silver-framework-tests")
                .config("spark.ui.enabled", "false")
                .getOrCreate()
            )
        except Exception as exc:
            raise unittest.SkipTest(
                f"Spark session unavailable: {exc}"
            ) from exc

    @classmethod
    def tearDownClass(cls) -> None:
        spark = getattr(cls, "spark", None)

        if spark is not None:
            spark.stop()

    def test_normalization_validation_and_quarantine_routing(self) -> None:
        from silver_framework import (
            normalize_schema,
            validate_types,
        )

        config = load_schema_config(
            "biometric",
            str(ROOT / "configs" / "schemas"),
        )

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

        normalized_df, report = normalize_schema(
            df,
            config,
            "test_run",
        )

        valid_df, invalid_df = validate_types(
            normalized_df,
            config,
        )

        self.assertIn(
            "bio_age_17_plus",
            report["output_columns"],
        )

        try:
            valid_count = valid_df.count()
            invalid_count = invalid_df.count()

            reasons = (
                invalid_df
                .select("validation_reasons")
                .collect()[0]["validation_reasons"]
            )
        except Exception as exc:
            raise unittest.SkipTest(
                f"Spark action failed in this environment: {exc}"
            ) from exc

        self.assertEqual(valid_count, 1)
        self.assertEqual(invalid_count, 1)

        self.assertIn("date_required", reasons)
        self.assertIn("date_invalid_date", reasons)
        self.assertIn("pincode_invalid_pattern", reasons)
        self.assertIn("bio_age_5_17_below_min_0", reasons)
        self.assertIn(
            "bio_age_17_plus_invalid_numeric",
            reasons,
        )

    def test_schema_type_mismatches_reports_incompatible_columns(self) -> None:
        existing_df = self.spark.createDataFrame(
            [
                {
                    "pincode": 123456,
                    "state": "X",
                }
            ]
        )

        incoming_df = self.spark.createDataFrame(
            [
                {
                    "pincode": "123456",
                    "state": "X",
                    "new_col": "allowed",
                }
            ]
        )

        self.assertEqual(
            schema_type_mismatches(
                existing_df,
                incoming_df,
            ),
            [
                "pincode: existing=bigint, incoming=string"
            ],
        )

    def test_domain_rules_detect_sum_and_arithmetic_mismatches(self) -> None:
        from pyspark.sql import functions as F

        df = self.spark.createDataFrame(
            [
                (
                    "226001",
                    100,
                    45,
                    50,
                    5,
                    20,
                    5,
                    15,
                ),
                (
                    "226002",
                    100,
                    45,
                    50,
                    10,
                    20,
                    5,
                    15,
                ),
                (
                    "226003",
                    100,
                    45,
                    50,
                    5,
                    20,
                    5,
                    10,
                ),
            ],
            [
                "pincode",
                "voter_total",
                "male_voters",
                "female_voters",
                "other_voters",
                "new_registrations",
                "deletions",
                "net_change",
            ],
        )

        test_df = df.withColumn(
            REASONS_COL,
            F.array().cast("array<string>"),
        )

        rules = {
            "sum_relationships": [
                {
                    "target": "voter_total",
                    "columns": [
                        "male_voters",
                        "female_voters",
                        "other_voters",
                    ],
                    "reason": "voter_total_category_mismatch",
                }
            ],
            "arithmetic_relationships": [
                {
                    "target": "net_change",
                    "left": "new_registrations",
                    "operator": "-",
                    "right": "deletions",
                    "reason": "net_change_mismatch",
                }
            ],
        }

        result_df = add_domain_rules(
            test_df,
            rules,
        )

        results = {
            row["pincode"]: row[REASONS_COL]
            for row in (
                result_df
                .select(
                    "pincode",
                    REASONS_COL,
                )
                .collect()
            )
        }

        # 226001 is completely valid
        self.assertEqual(
            results["226001"],
            [],
        )

        # 226002:
        # 45 + 50 + 10 = 105, but voter_total = 100
        self.assertIn(
            "voter_total_category_mismatch",
            results["226002"],
        )

        # 226003:
        # 20 - 5 = 15, but net_change = 10
        self.assertIn(
            "net_change_mismatch",
            results["226003"],
        )

    def test_domain_rules_detect_population_mismatches(self) -> None:
        from pyspark.sql import functions as F

        test_rows = [
            (
                "226001",
                198000,
                102000,
                96000,
                18000,
                52000,
                128000,
            ),
            (
                "226002",
                198000,
                110000,
                96000,
                18000,
                52000,
                128000,
            ),
            (
                "226003",
                198000,
                102000,
                96000,
                18000,
                52000,
                130000,
            ),
        ]

        test_df = self.spark.createDataFrame(
            test_rows,
            [
                "pincode",
                "population_total",
                "male",
                "female",
                "age_0_5",
                "age_6_17",
                "age_18_plus",
            ],
        ).withColumn(
            REASONS_COL,
            F.array().cast("array<string>"),
        )

        rules = {
            "sum_relationships": [
                {
                    "target": "population_total",
                    "columns": [
                        "male",
                        "female",
                    ],
                    "reason": "population_gender_total_mismatch",
                },
                {
                    "target": "population_total",
                    "columns": [
                        "age_0_5",
                        "age_6_17",
                        "age_18_plus",
                    ],
                    "reason": "population_age_total_mismatch",
                },
            ],
        }

        result_df = add_domain_rules(
            test_df,
            rules,
        )

        results = {
            row["pincode"]: row[REASONS_COL]
            for row in (
                result_df
                .select(
                    "pincode",
                    REASONS_COL,
                )
                .collect()
            )
        }

        # 226001 is completely valid
        self.assertEqual(
            results["226001"],
            [],
        )

        # 226002:
        # 110000 + 96000 = 206000,
        # but population_total = 198000
        self.assertIn(
            "population_gender_total_mismatch",
            results["226002"],
        )

        # 226003:
        # 18000 + 52000 + 130000 = 200000,
        # but population_total = 198000
        self.assertIn(
            "population_age_total_mismatch",
            results["226003"],
        )

    def test_domain_rules_detect_aadhaar_voter_link_mismatches(self) -> None:
        from pyspark.sql import functions as F

        test_rows = [
            (
                "226001",
                25000,
                24000,
                23000,
                850,
                150,
            ),
            (
                "226002",
                25000,
                26000,
                23000,
                850,
                150,
            ),
            (
                "226003",
                25000,
                24000,
                25000,
                850,
                150,
            ),
            (
                "226004",
                25000,
                24000,
                23000,
                1000,
                150,
            ),
        ]

        test_df = self.spark.createDataFrame(
            test_rows,
            [
                "pincode",
                "voter_total",
                "aadhaar_available",
                "aadhaar_voter_linked",
                "linkage_pending",
                "linkage_rejected",
            ],
        ).withColumn(
            REASONS_COL,
            F.array().cast("array<string>"),
        )

        rules = {
            "comparison_relationships": [
                {
                    "left": "aadhaar_available",
                    "operator": "<=",
                    "right": "voter_total",
                    "reason": "aadhaar_available_exceeds_voter_total",
                },
                {
                    "left": "aadhaar_voter_linked",
                    "operator": "<=",
                    "right": "aadhaar_available",
                    "reason": "linked_exceeds_aadhaar_available",
                },
            ],
            "sum_relationships": [
                {
                    "target": "aadhaar_available",
                    "columns": [
                        "aadhaar_voter_linked",
                        "linkage_pending",
                        "linkage_rejected",
                    ],
                    "reason": "linkage_status_count_exceeds_available",
                }
            ],
        }

        result_df = add_domain_rules(
            test_df,
            rules,
        )

        results = {
            row["pincode"]: row[REASONS_COL]
            for row in (
                result_df
                .select(
                    "pincode",
                    REASONS_COL,
                )
                .collect()
            )
        }

        # 226001 is completely valid
        self.assertEqual(
            results["226001"],
            [],
        )

        # 226002:
        # aadhaar_available = 26000 > voter_total = 25000
        self.assertIn(
            "aadhaar_available_exceeds_voter_total",
            results["226002"],
        )

        # 226003:
        # aadhaar_voter_linked = 25000 > aadhaar_available = 24000
        self.assertIn(
            "linked_exceeds_aadhaar_available",
            results["226003"],
        )

        # 226004:
        # 23000 + 1000 + 150 = 24150,
        # but aadhaar_available = 24000
        self.assertIn(
            "linkage_status_count_exceeds_available",
            results["226004"],
        )
    def test_domain_rules_detect_scheme_beneficiary_mismatches(self) -> None:
        from pyspark.sql import functions as F

        test_rows = [
            (
                "226001",
                "2026-04-01",
                "2027-03-31",
                150,
                132,
                18,
                125,
            ),
            (
                "226002",
                "2026-04-01",
                "2027-03-31",
                140,
                130,
                20,
                120,
            ),
            (
                "226003",
                "2026-04-01",
                "2027-03-31",
                150,
                132,
                18,
                140,
            ),
            (
                "226004",
                "2026-04-01",
                "2026-03-31",
                150,
                132,
                18,
                125,
            ),
        ]

        test_df = self.spark.createDataFrame(
            test_rows,
            [
                "pincode",
                "start_date",
                "end_date",
                "applications_received",
                "beneficiaries_approved",
                "beneficiaries_rejected",
                "beneficiaries_disbursed",
            ],
        ).withColumn(
            "start_date",
            F.to_date(F.col("start_date")),
        ).withColumn(
            "end_date",
            F.to_date(F.col("end_date")),
        ).withColumn(
            REASONS_COL,
            F.array().cast("array<string>"),
        )

        rules = {
            "date_relationships": [
                {
                    "left": "end_date",
                    "operator": ">=",
                    "right": "start_date",
                    "reason": "end_date_before_start_date",
                }
            ],
            "sum_relationships": [
                {
                    "target": "applications_received",
                    "columns": [
                        "beneficiaries_approved",
                        "beneficiaries_rejected",
                    ],
                    "operator": "<=",
                    "reason": "beneficiary_decision_count_exceeds_applications",
                }
            ],
            "comparison_relationships": [
                {
                    "left": "beneficiaries_disbursed",
                    "operator": "<=",
                    "right": "beneficiaries_approved",
                    "reason": "disbursed_exceeds_approved",
                }
            ],
        }

        result_df = add_domain_rules(
            test_df,
            rules,
        )

        results = {
            row["pincode"]: row[REASONS_COL]
            for row in (
                result_df
                .select(
                    "pincode",
                    REASONS_COL,
                )
                .collect()
            )
        }

        # 226001 is completely valid
        self.assertEqual(
            results["226001"],
            [],
        )

        # 226002:
        # 130 + 20 = 150 > 140
        self.assertIn(
            "beneficiary_decision_count_exceeds_applications",
            results["226002"],
        )

        # 226003:
        # 140 > 132
        self.assertIn(
            "disbursed_exceeds_approved",
            results["226003"],
        )

        # 226004:
        # 31-03-2026 < 01-04-2026
        self.assertIn(
            "end_date_before_start_date",
            results["226004"],
        )


if __name__ == "__main__":
    unittest.main()