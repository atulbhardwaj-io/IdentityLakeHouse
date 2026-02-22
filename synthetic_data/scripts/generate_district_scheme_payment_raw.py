from pathlib import Path
import csv
import random
from datetime import datetime, timezone

# -------------------------------------------------------------------
# Synthetic Generator: district_scheme_payment_raw
# -------------------------------------------------------------------
# Purpose:
# - Core district-level finance/performance fact for scheme analytics
# - Supports: "How is scheme X performing in district Y over time?"
#
# Inputs:
# - synthetic_data/synthetic/scheme_master_raw.csv
# - synthetic_data/synthetic/District_Masters.csv
#
# Output:
# - synthetic_data/synthetic/district_scheme_payment_raw.csv
# -------------------------------------------------------------------

TARGET_ROWS = 1_000_000  # 10 lakh
SEED = 42
PINCODES_PER_DISTRICT = 4

random_gen = random.Random(SEED)

base = Path("synthetic_data/synthetic")
scheme_master_path = base / "scheme_master_raw.csv"
district_master_path = base / "District_Masters.csv"
out_file = base / "district_scheme_payment_raw.csv"

if not scheme_master_path.exists():
    raise FileNotFoundError(f"Missing: {scheme_master_path}")
if not district_master_path.exists():
    raise FileNotFoundError(f"Missing: {district_master_path}")

# -------------------------
# Read scheme master
# -------------------------
schemes = []
with scheme_master_path.open("r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    needed = {"scheme_id", "scheme_type"}
    if not needed.issubset(set(reader.fieldnames or [])):
        raise ValueError("scheme_master_raw.csv must include scheme_id and scheme_type")

    for row in reader:
        scheme_id = row["scheme_id"].strip()
        scheme_type = row["scheme_type"].strip()
        if not scheme_id:
            continue
        schemes.append((scheme_id, scheme_type))

if not schemes:
    raise ValueError("No schemes found in scheme_master_raw.csv")

# -------------------------
# Read district master
# -------------------------
locations = []
seen = set()
with district_master_path.open("r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    if "State Name" not in reader.fieldnames or "District Name" not in reader.fieldnames:
        raise ValueError("District_Masters.csv must include State Name and District Name columns")

    for row in reader:
        state = row["State Name"].strip().title()
        district = row["District Name"].strip().title()
        key = (state, district)
        if not state or not district or key in seen:
            continue
        seen.add(key)

        pincode_base = random_gen.randint(100000, 999000)
        for i in range(PINCODES_PER_DISTRICT):
            locations.append((state, district, str(pincode_base + i)))

if not locations:
    raise ValueError("No valid locations found in District_Masters.csv")

# Monthly grain dates in analysis window
months = [
    "01-03-2025",
    "01-04-2025",
    "01-05-2025",
    "01-06-2025",
    "01-07-2025",
    "01-08-2025",
    "01-09-2025",
    "01-10-2025",
    "01-11-2025",
    "01-12-2025",
]

# Average per-beneficiary payout baseline by scheme type
amount_by_type = {
    "Health": 4500,
    "Financial Inclusion": 900,
    "Agriculture": 2600,
    "Food Security": 1300,
    "Employment": 2000,
    "Rural Development": 1700,
    "Skill Development": 2300,
    "Social Security": 2400,
    "Housing": 10000,
    "Water": 1400,
    "Sanitation": 1600,
    "Education": 1800,
    "Women Welfare": 2200,
    "Energy": 3200,
    "Insurance": 1200,
    "Pension": 2100,
    "MSME": 3400,
    "Urban Livelihood": 2400,
    "Entrepreneurship": 3600,
    "Digital Infrastructure": 1500,
}

columns = [
    "date",
    "state",
    "district",
    "pincode",
    "scheme_id",
    "beneficiaries_paid",
    "failed_payments",
    "pending_payments",
    "avg_amount_per_beneficiary",
    "amount_paid",
    "amount_failed",
    "amount_pending",
    "utilization_pct",
    "data_source",
    "ingest_ts",
]

scheme_count = len(schemes)
location_count = len(locations)
month_count = len(months)
ingest_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

with out_file.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(columns)

    for i in range(TARGET_ROWS):
        scheme_id, scheme_type = schemes[i % scheme_count]
        state, district, pincode = locations[(i // scheme_count) % location_count]
        date_val = months[(i // (scheme_count * location_count)) % month_count]

        paid = random_gen.randint(60, 4500)
        failed = random_gen.randint(0, max(2, int(paid * 0.08)))
        pending = random_gen.randint(0, max(2, int(paid * 0.12)))

        avg_amount = int(amount_by_type.get(scheme_type, 1800) * random_gen.uniform(0.90, 1.20))

        amount_paid = float(paid * avg_amount)
        amount_failed = float(failed * avg_amount)
        amount_pending = float(pending * avg_amount)

        total_amount = amount_paid + amount_failed + amount_pending
        utilization_pct = round((amount_paid / total_amount) * 100.0, 2) if total_amount > 0 else 0.0

        writer.writerow(
            [
                date_val,
                state,
                district,
                pincode,
                scheme_id,
                paid,
                failed,
                pending,
                avg_amount,
                f"{amount_paid:.2f}",
                f"{amount_failed:.2f}",
                f"{amount_pending:.2f}",
                utilization_pct,
                "government_website",
                ingest_ts,
            ]
        )

        if (i + 1) % 200_000 == 0:
            print(f"Written rows: {i + 1}")

print("Created:", out_file)
print("Rows:", TARGET_ROWS)
print("Schemes:", scheme_count)
print("Location keys:", location_count)
print("Months:", month_count)
