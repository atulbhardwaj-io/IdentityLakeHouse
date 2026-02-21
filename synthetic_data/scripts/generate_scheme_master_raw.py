from pathlib import Path
import csv

# Generate scheme_master_raw table with real Indian scheme names
# Output: synthetic_data/synthetic/scheme_master_raw.csv

out_dir = Path('synthetic_data/synthetic')
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / 'scheme_master_raw.csv'

columns = [
    'scheme_id',
    'scheme_name',
    'scheme_type',
    'target_group',
    'start_date',
    'end_date',
    'eligibility_rule',
    'active_flag',
]

# NOTE:
# - Dates are approximate operational dates for synthetic engineering use.
# - This table is a realistic master/reference table for downstream joins.
scheme_catalog = [
    ('Ayushman Bharat - PM-JAY', 'Health', 'Low Income Families', '2018-09-01', '2035-12-31', 'SECC/eligible households; family verification', 1),
    ('PM Ayushman Bharat Health Infrastructure Mission', 'Health', 'General', '2021-10-01', '2035-12-31', 'State and district health infra eligibility', 1),
    ('Pradhan Mantri Jan Arogya Yojana', 'Health', 'Low Income Families', '2018-09-01', '2035-12-31', 'Socio-economic criteria and ID verification', 1),
    ('Pradhan Mantri Jan Dhan Yojana', 'Financial Inclusion', 'General', '2014-08-01', '2035-12-31', 'Bank account + KYC requirements', 1),
    ('Pradhan Mantri Kisan Samman Nidhi', 'Agriculture', 'Farmers', '2019-02-01', '2035-12-31', 'Landholding farmer verification', 1),
    ('Pradhan Mantri Fasal Bima Yojana', 'Agriculture', 'Farmers', '2016-01-01', '2035-12-31', 'Enrolled farmer + crop insurance criteria', 1),
    ('Pradhan Mantri Krishi Sinchai Yojana', 'Agriculture', 'Farmers', '2015-07-01', '2035-12-31', 'Irrigation and agriculture eligibility', 1),
    ('Soil Health Card Scheme', 'Agriculture', 'Farmers', '2015-02-01', '2035-12-31', 'Farmer registration and land details', 1),
    ('National Food Security Act - PDS', 'Food Security', 'Low Income Families', '2013-09-01', '2035-12-31', 'Ration card category based', 1),
    ('One Nation One Ration Card', 'Food Security', 'Low Income Families', '2019-06-01', '2035-12-31', 'Portable ration entitlement verification', 1),
    ('Mahatma Gandhi National Rural Employment Guarantee Act', 'Employment', 'Rural Households', '2006-02-01', '2035-12-31', 'Job card and rural household verification', 1),
    ('Deendayal Antyodaya Yojana - NRLM', 'Rural Development', 'Women', '2011-06-01', '2035-12-31', 'SHG membership and rural eligibility', 1),
    ('Deen Dayal Upadhyaya Grameen Kaushalya Yojana', 'Skill Development', 'Unemployed Adults', '2014-09-01', '2035-12-31', 'Youth skill training eligibility', 1),
    ('National Social Assistance Programme', 'Social Security', 'Senior Citizens', '1995-08-01', '2035-12-31', 'Age/income criteria under NSAP', 1),
    ('Pradhan Mantri Awas Yojana - Gramin', 'Housing', 'Low Income Families', '2016-11-01', '2035-12-31', 'Housing deprivation criteria', 1),
    ('Pradhan Mantri Awas Yojana - Urban', 'Housing', 'Urban Households', '2015-06-01', '2035-12-31', 'Urban housing eligibility criteria', 1),
    ('Jal Jeevan Mission', 'Water', 'Rural Households', '2019-08-01', '2035-12-31', 'Household tap connection coverage criteria', 1),
    ('Swachh Bharat Mission - Gramin', 'Sanitation', 'Rural Households', '2014-10-01', '2035-12-31', 'Household sanitation eligibility', 1),
    ('Swachh Bharat Mission - Urban', 'Sanitation', 'Urban Households', '2014-10-01', '2035-12-31', 'Urban sanitation and waste eligibility', 1),
    ('PM POSHAN (Mid-Day Meal)', 'Education', 'Children', '2021-09-01', '2035-12-31', 'School enrollment verification', 1),
    ('Samagra Shiksha', 'Education', 'Students', '2018-04-01', '2035-12-31', 'School and state implementation criteria', 1),
    ('PM SHRI Schools', 'Education', 'Students', '2022-09-01', '2035-12-31', 'Selected schools and student coverage', 1),
    ('Beti Bachao Beti Padhao', 'Women Welfare', 'Women', '2015-01-01', '2035-12-31', 'Girl child and women empowerment criteria', 1),
    ('Pradhan Mantri Matru Vandana Yojana', 'Women Welfare', 'Women', '2017-01-01', '2035-12-31', 'Pregnant/lactating mother criteria', 1),
    ('Mission Shakti', 'Women Welfare', 'Women', '2022-04-01', '2035-12-31', 'Women safety and empowerment criteria', 1),
    ('Sukanya Samriddhi Yojana', 'Women Welfare', 'Children', '2015-01-01', '2035-12-31', 'Girl child account criteria', 1),
    ('Pradhan Mantri Ujjwala Yojana', 'Energy', 'Low Income Families', '2016-05-01', '2035-12-31', 'BPL household LPG criteria', 1),
    ('Pradhan Mantri Suraksha Bima Yojana', 'Insurance', 'General', '2015-05-01', '2035-12-31', 'Eligible bank account and age criteria', 1),
    ('Pradhan Mantri Jeevan Jyoti Bima Yojana', 'Insurance', 'General', '2015-05-01', '2035-12-31', 'Eligible bank account and age criteria', 1),
    ('Atal Pension Yojana', 'Pension', 'General', '2015-06-01', '2035-12-31', 'Age and contribution criteria', 1),
    ('Pradhan Mantri Mudra Yojana', 'MSME', 'Unemployed Adults', '2015-04-01', '2035-12-31', 'Micro-enterprise credit eligibility', 1),
    ('PM SVANidhi', 'Urban Livelihood', 'Unemployed Adults', '2020-06-01', '2035-12-31', 'Street vendor identification criteria', 1),
    ('Start-up India', 'Entrepreneurship', 'General', '2016-01-01', '2035-12-31', 'DPIIT-recognized startup criteria', 1),
    ('Stand-Up India', 'Entrepreneurship', 'Women', '2016-04-01', '2035-12-31', 'SC/ST/women enterprise loan eligibility', 1),
    ('Pradhan Mantri Kaushal Vikas Yojana', 'Skill Development', 'Unemployed Adults', '2015-07-01', '2035-12-31', 'Skill training and certification criteria', 1),
    ('Digital India Programme', 'Digital Infrastructure', 'General', '2015-07-01', '2035-12-31', 'Public digital service implementation criteria', 1),
    ('BharatNet', 'Digital Infrastructure', 'Rural Households', '2011-10-01', '2035-12-31', 'Rural broadband rollout eligibility', 1),
    ('PM Vishwakarma', 'Skill Development', 'Unemployed Adults', '2023-09-01', '2035-12-31', 'Traditional artisan verification', 1),
    ('National Health Mission', 'Health', 'General', '2013-05-01', '2035-12-31', 'Public health programme eligibility', 1),
]

rows = []
for i, item in enumerate(scheme_catalog, start=1):
    scheme_id = f'SCH{str(i).zfill(4)}'
    rows.append([scheme_id, item[0], item[1], item[2], item[3], item[4], item[5], item[6]])

with out_file.open('w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(columns)
    writer.writerows(rows)

print('Created:', out_file)
print('Total rows:', len(rows))
print('Columns:', len(columns))
print('Sample row:', rows[0])
