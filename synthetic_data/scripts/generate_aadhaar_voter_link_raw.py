from pathlib import Path
import csv
import random
from datetime import datetime, timezone

# -------------------------------------------------------------------
# Synthetic Generator: aadhaar_voter_link_raw
# -------------------------------------------------------------------
# Output: synthetic_data/synthetic/aadhaar_voter_link_raw.csv
# Scale: 10 lakh rows
# -------------------------------------------------------------------

TARGET_ROWS = 1_000_000
SEED = 42
PINCODES_PER_DISTRICT = 4

random_gen = random.Random(SEED)

base = Path('synthetic_data/synthetic')
district_master_path = base / 'District_Masters.csv'
out_file = base / 'aadhaar_voter_link_raw.csv'

if not district_master_path.exists():
    raise FileNotFoundError(f'Missing: {district_master_path}')

# Read district master
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

months = [
    '01-03-2025', '01-04-2025', '01-05-2025', '01-06-2025', '01-07-2025',
    '01-08-2025', '01-09-2025', '01-10-2025', '01-11-2025', '01-12-2025'
]

columns = [
    'date',
    'state',
    'district',
    'pincode',
    'voter_total',
    'aadhaar_available',
    'aadhaar_voter_linked',
    'linkage_pending',
    'linkage_rejected',
    'linkage_pct',
    'kyc_pending',
    'duplicate_suspected',
    'data_source',
    'ingest_ts',
]

location_count = len(locations)
month_count = len(months)
ingest_ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

with out_file.open('w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(columns)

    for i in range(TARGET_ROWS):
        state, district, pincode = locations[i % location_count]
        date_val = months[(i // location_count) % month_count]

        voter_total = random_gen.randint(10000, 320000)
        aadhaar_available = int(voter_total * random_gen.uniform(0.80, 0.99))

        # linked cannot exceed aadhaar_available
        aadhaar_voter_linked = int(aadhaar_available * random_gen.uniform(0.70, 0.97))
        remaining = aadhaar_available - aadhaar_voter_linked

        linkage_rejected = int(remaining * random_gen.uniform(0.05, 0.25))
        linkage_pending = max(0, remaining - linkage_rejected)

        linkage_pct = round((aadhaar_voter_linked / voter_total) * 100, 2) if voter_total > 0 else 0.0
        kyc_pending = int(linkage_pending * random_gen.uniform(0.20, 0.80))
        duplicate_suspected = int(aadhaar_available * random_gen.uniform(0.001, 0.02))

        writer.writerow([
            date_val,
            state,
            district,
            pincode,
            voter_total,
            aadhaar_available,
            aadhaar_voter_linked,
            linkage_pending,
            linkage_rejected,
            linkage_pct,
            kyc_pending,
            duplicate_suspected,
            'government_website',
            ingest_ts,
        ])

        if (i + 1) % 200000 == 0:
            print(f'Written rows: {i + 1}')

print('Created:', out_file)
print('Rows:', TARGET_ROWS)
print('Location keys:', location_count)
print('Months:', month_count)
