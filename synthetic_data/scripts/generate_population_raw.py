from pathlib import Path
import csv
import random

# -------------------------------------------------------------------
# Synthetic Generator: population_raw (large fact-like table)
# Uses real district names from District_Masters.csv
# Required columns in master: State Name, District Name
# -------------------------------------------------------------------

TARGET_ROWS = 1_000_000  # 10 lakh
SEED = 42

random_gen = random.Random(SEED)

out_dir = Path('synthetic_data/synthetic')
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / 'population_raw.csv'

district_master_file = Path('synthetic_data/synthetic/District_Masters.csv')

columns = [
    'date',
    'state',
    'district',
    'pincode',
    'population_total',
    'male',
    'female',
    'age_0_5',
    'age_6_17',
    'age_18_plus',
]

if not district_master_file.exists():
    raise FileNotFoundError(f'Missing district master file: {district_master_file}')

# Read and deduplicate real state-district pairs
district_pairs = []
seen_pairs = set()
with district_master_file.open('r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    if 'State Name' not in reader.fieldnames or 'District Name' not in reader.fieldnames:
        raise ValueError('District_Masters.csv must include columns: State Name, District Name')

    for row in reader:
        state = row['State Name'].strip().title()
        district = row['District Name'].strip().title()
        key = (state, district)
        if state and district and key not in seen_pairs:
            seen_pairs.add(key)
            district_pairs.append(key)

if not district_pairs:
    raise ValueError('No valid state-district pairs found in District_Masters.csv')

# Build location key pool by assigning multiple pincodes to each district
locations = []
for state, district in district_pairs:
    pincode_base = random_gen.randint(100000, 999000)
    for i in range(3):
        locations.append((state, district, str(pincode_base + i)))

# Shuffle once so records look random while still covering all districts
random_gen.shuffle(locations)

# Build month list (24 months)
months = []
for year in [2023, 2024]:
    for month in range(1, 13):
        months.append((year, month))

location_count = len(locations)
month_count = len(months)
print(f'Total master districts: {len(district_pairs)}')
print(f'Total location keys (district x pincode): {location_count}')

with out_file.open('w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(columns)

    for i in range(TARGET_ROWS):
        # Deterministic cycling guarantees all districts are covered repeatedly
        state, district, pincode = locations[i % location_count]
        year, month = months[(i // location_count) % month_count]

        base_pop = random_gen.randint(80_000, 350_000)
        trend = ((year - 2023) * 1200) + (month * 60)
        noise = int(random_gen.gauss(0, 1800))
        total = max(50_000, base_pop + trend + noise)

        male = int(total * random_gen.uniform(0.50, 0.53))
        female = max(0, total - male)

        age_0_5 = int(total * random_gen.uniform(0.07, 0.11))
        age_6_17 = int(total * random_gen.uniform(0.18, 0.26))
        age_18_plus = max(0, total - age_0_5 - age_6_17)

        writer.writerow([
            f'{year}-{month:02d}-01',
            state,
            district,
            pincode,
            total,
            male,
            female,
            age_0_5,
            age_6_17,
            age_18_plus,
        ])

        if (i + 1) % 200_000 == 0:
            print(f'Written rows: {i + 1}')

print('Created:', out_file)
print('Target rows:', TARGET_ROWS)
