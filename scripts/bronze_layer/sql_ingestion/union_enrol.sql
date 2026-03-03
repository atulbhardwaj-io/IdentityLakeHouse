USE Identitylakehouse;
GO

-- 1. Create the master table structure
IF OBJECT_ID('bronze.api_data_aadhar_enrolment_full', 'U') IS NOT NULL
    DROP TABLE bronze.api_data_aadhar_enrolment_full;
GO

CREATE TABLE bronze.api_data_aadhar_enrolment_full (
    [date]           NVARCHAR(50),
    [state]          NVARCHAR(100),
    [district]       NVARCHAR(100),
    [pincode]        NVARCHAR(20),
    [age_0_5]        INT,
    [age_5_17]       INT,
    [age_18_greater] INT
);
GO

-- 2. Insert all data from the batch tables
INSERT INTO bronze.api_data_aadhar_enrolment_full
SELECT * FROM bronze.api_data_aadhar_enrolment_0_500000
UNION ALL
SELECT * FROM bronze.api_data_aadhar_enrolment_500000_1000000
UNION ALL
SELECT * FROM bronze.api_data_aadhar_enrolment_1000000_1006029;
GO

-- 3. Final Verification
SELECT 
    (SELECT COUNT(*) FROM bronze.api_data_aadhar_enrolment_full) AS Total_Merged_Rows;