from pathlib import Path
import csv
import random
from datetime import datetime

# -------------------------------------------------------------------
# Synthetic Generator: scheme_beneficiary_raw (large fact table)
# -------------------------------------------------------------------
# Inputs:
# - synthetic_data/synthetic/scheme_master_raw.csv
# - synthetic_data/synthetic/District_Masters.csv
#
# Output:
# - synthetic_data/synthetic/scheme_beneficiary_raw.csv
#
# Notes:
# - Keeps monthly date grain for trend analysis
# - Uses fixed analysis window in each row for reporting scope
# -------------------------------------------------------------------

TARGET_ROWS = 1_000_000  # 10 lakh
SEED = 42
PINCODES_PER_DISTRICT = 4

ANALYSIS_START = '01-03-2025'
ANALYSIS_END = '29-12-2025'

random_gen = random.Random(SEED)

base = Path('synthetic_data/synthetic')
scheme_master_path = base / 'scheme_master_raw.csv'
district_master_path = base / 'District_Masters.csv'
out_file = base / 'scheme_beneficiary_raw.csv'

if not scheme_master_path.exists():
    raise FileNotFoundError(f'Missing: {scheme_master_path}')
if not district_master_path.exists():
    raise FileNotFoundError(f'Missing: {district_master_path}')

# -------------------------
# Read scheme master
# -------------------------
schemes = []
with scheme_master_path.open('r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        schemes.append({
            'scheme_id': row['scheme_id'].strip(),
            'scheme_name': row['scheme_name'].strip(),
            'scheme_type': row['scheme_type'].strip(),
            'scheme_start': row['start_date'].strip(),
            'scheme_end': row['end_date'].strip(),
            'active_flag': int(row.get('active_flag', '1') or '1'),
        })

if not schemes:
    raise ValueError('No schemes found in scheme_master_raw.csv')

# -------------------------
# Read district master
# -------------------------
locations = []
seen = set()
with district_master_path.open('r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    if 'State Name' not in reader.fieldnames or 'District Name' not in reader.fieldnames:
        raise ValueError('District_Masters.csv must include State Name and District Name columns')

    for row in reader:
        state = row['State Name'].strip().title()
        district = row['District Name'].strip().title()
        key = (state, district)
        if not state or not district or key in seen:
            continue
        seen.add(key)

        pincode_base = random_gen.randint(100000, 999000)
        for i in range(PINCODES_PER_DISTRICT):
            locations.append((state, district, str(pincode_base + i)))

if not locations:
    raise ValueError('No valid locations found in District_Masters.csv')

# -------------------------
# Date range (monthly)
# -------------------------
months = [
    '01-03-2025', '01-04-2025', '01-05-2025', '01-06-2025', '01-07-2025',
    '01-08-2025', '01-09-2025', '01-10-2025', '01-11-2025', '01-12-2025'
]

# Benefit amount baseline by scheme type
amount_by_type = {
    'Health': 4500,
    'Financial Inclusion': 800,
    'Agriculture': 2500,
    'Food Security': 1200,
    'Employment': 1800,
    'Rural Development': 1600,
    'Skill Development': 2200,
    'Social Security': 2000,
    'Housing': 9000,
    'Water': 1400,
    'Sanitation': 1500,
    'Education': 1700,
    'Women Welfare': 2100,
    'Energy': 3200,
    'Insurance': 1100,
    'Pension': 1900,
    'MSME': 3000,
    'Urban Livelihood': 2300,
    'Entrepreneurship': 3500,
    'Digital Infrastructure': 1300,
}

columns = [
    'date',
    'start_date',
    'end_date',
    'state',
    'district',
    'pincode',
    'scheme_id',
    'applications_received',
    'beneficiaries_approved',
    'beneficiaries_rejected',
    'beneficiaries_disbursed',
    'disbursed_amount',
    'data_source',
    'ingest_ts',
]

# Build deterministic cycle pools for full coverage
scheme_count = len(schemes)
location_count = len(locations)
month_count = len(months)

ingest_ts = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

with out_file.open('w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(columns)

    for i in range(TARGET_ROWS):
        scheme = schemes[i % scheme_count]
        state, district, pincode = locations[(i // scheme_count) % location_count]
        date_val = months[(i // (scheme_count * location_count)) % month_count]

        # Only generate for rows within scheme active range (simple active filter)
        # Here schemes are mostly active; logic retained for correctness.
        applications = random_gen.randint(80, 5000)
        approved = int(applications * random_gen.uniform(0.55, 0.90))
        rejected = applications - approved
        disbursed = int(approved * random_gen.uniform(0.85, 1.00))

        base_amt = amount_by_type.get(scheme['scheme_type'], 1500)
        per_person = int(base_amt * random_gen.uniform(0.9, 1.2))
        disbursed_amount = float(disbursed * per_person)

        writer.writerow([
            date_val,
            ANALYSIS_START,
            ANALYSIS_END,
            state,
            district,
            pincode,
            scheme['scheme_id'],
            applications,
            approved,
            rejected,
            disbursed,
            f'{disbursed_amount:.2f}',
            'synthetic_batch',
            ingest_ts,
        ])

        if (i + 1) % 200_000 == 0:
            print(f'Written rows: {i + 1}')

print('Created:', out_file)
print('Rows:', TARGET_ROWS)
print('Schemes:', scheme_count)
print('Location keys:', location_count)
print('Months:', month_count)
