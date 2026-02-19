PRINT 'Merging All Bronze Tables...';

IF OBJECT_ID('bronze.api_data_aadhar_demographic_full', 'U') IS NOT NULL
DROP TABLE bronze.api_data_aadhar_demographic_full;

SELECT *
INTO bronze.api_data_aadhar_demographic_full
FROM bronze.api_data_aadhar_demographic_0_500000
UNION ALL
SELECT * FROM bronze.api_data_aadhar_demographic_500000_1000000
UNION ALL
SELECT * FROM bronze.api_data_aadhar_demographic_1000000_1500000
UNION ALL
SELECT * FROM bronze.api_data_aadhar_demographic_1500000_2000000
UNION ALL
SELECT * FROM bronze.api_data_aadhar_demographic_2000000_2071700;

PRINT 'Merge Completed Successfully';
