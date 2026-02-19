PRINT 'Merging All Bronze Tables...';

IF OBJECT_ID('bronze.api_data_aadhar_biometric_full', 'U') IS NOT NULL
DROP TABLE bronze.api_data_aadhar_biometric_full;

SELECT *
INTO bronze.api_data_aadhar_biometric_full
FROM bronze.api_data_aadhar_biometric_0_500000
UNION ALL
SELECT * FROM bronze.api_data_aadhar_biometric_500000_1000000
UNION ALL
SELECT * FROM bronze.api_data_aadhar_biometric_1000000_1500000
UNION ALL
SELECT * FROM bronze.api_data_aadhar_biometric_1500000_1861108


PRINT 'Merge Completed Successfully';