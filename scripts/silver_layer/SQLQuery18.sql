IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'bronze')
    EXEC('CREATE SCHEMA silver');
GO


IF OBJECT_ID('silver.api_data_aadhar_enrolment_full', 'U') IS NOT NULL
    DROP TABLE silver.api_data_aadhar_enrolment_full;
GO

CREATE TABLE silver.data_aadhar_enrolment_full (
     [date]           NVARCHAR(50), 
    [state]          NVARCHAR(255),
    [district]       NVARCHAR(255),
    [pincode]        NVARCHAR(50),
    [age_0_5]        INT,
    [age_5_17]       INT,
    [age_18_greater] INT
);
GO

IF OBJECT_ID('silver.api_data_aadhar_demographic_full', 'U') IS NOT NULL
    DROP TABLE silver.data_aadhar_demographic_full;
GO

CREATE TABLE silver.data_aadhar_demographica_full (
   [date]           NVARCHAR(50), 
    [state]          NVARCHAR(255),
    [district]       NVARCHAR(255),
    [pincode]        NVARCHAR(50),
    [demo_age_5_17]     INT,
    [demo_age_17]       INT
);
GO

IF OBJECT_ID('silver.api_data_aadhar_biometric_full', 'U') IS NOT NULL
    DROP TABLE silver.api_data_aadhar_biometric_full;
GO

CREATE TABLE silver.data_aadhar_biometric_full (
  [date]           NVARCHAR(50), 
    [state]          NVARCHAR(255),
    [district]       NVARCHAR(255),
    [pincode]        NVARCHAR(50),
    [bio_age_5_17]     INT,
    [bio_age_17]       INT
);