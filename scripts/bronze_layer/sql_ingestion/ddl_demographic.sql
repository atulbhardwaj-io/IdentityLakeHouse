----CREATE DATABASE Identitylakehouse;
----GO
----USE Identitylakehouse
----GO
----CREATE SCHEMA bronze; 


-----------------------------------------
--IF OBJECT_ID('bronze.api_data_aadhar_enrolment_0_500000', 'U') IS NOT NULL

--    DROP TABLE bronze.api_data_aadhar_enrolment_0_500000;

--GO



---- Create table with columns matching your image

--CREATE TABLE bronze.api_data_aadhar_enrolment_0_500000 (

--    [date]           date,

--    [state]          NVARCHAR(50),

--    [district]       NVARCHAR(50),

--    [pincode]        int,

--    [age_0_5]        smallint,

--    [age_5_17]        smallint,

--    [age_18_greater]  smallint

--);

--GO
--------------------------------------------------



--IF OBJECT_ID('bronze.api_data_aadhar_enrolment_500000_1000000', 'U') IS NOT NULL

--    DROP TABLE bronze.api_data_aadhar_enrolment_500000_1000000;

--GO





--CREATE TABLE bronze.api_data_aadhar_enrolment_500000_1000000 (

--    [date]           date,

--    [state]          NVARCHAR(50),

--    [district]       NVARCHAR(50),

--    [pincode]        int,

--    [age_0_5]        smallint,

--    [age_5_17]        smallint,

--    [age_18_greater]  smallint

--);

--GO
-----------------------------------------



--IF OBJECT_ID('bronze.api_data_aadhar_enrolment_1000000_1006029', 'U') IS NOT NULL

--    DROP TABLE bronze.api_data_aadhar_enrolment_1000000_1006029;

--GO





--CREATE TABLE bronze.api_data_aadhar_enrolment_1000000_1006029 (

--    [date]           date,

--    [state]          NVARCHAR(50),

--    [district]       NVARCHAR(50),

--    [pincode]        int,

--    [age_0_5]        smallint,

--    [age_5_17]        smallint,

--    [age_18_greater]  smallint

--);


-----------------------------------------


/* 1. SETUP DATABASE AND SCHEMA
*/
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'Identitylakehouse')
    CREATE DATABASE Identitylakehouse;
GO

USE Identitylakehouse;
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'bronze')
    EXEC('CREATE SCHEMA bronze');
GO

/* 2. TABLE 1: 0 to 500k
*/
IF OBJECT_ID('bronze.api_data_aadhar_demographic_0_500000', 'U') IS NOT NULL
    DROP TABLE bronze.api_data_aadhar_demographic_0_500000;
GO

CREATE TABLE bronze.api_data_aadhar_demographic_0_500000 (
    [date]           NVARCHAR(50), 
    [state]          NVARCHAR(255),
    [district]       NVARCHAR(255),
    [pincode]        NVARCHAR(50),
    [demo_age_5_17]     INT,
    [demo_age_7]       INT
    
);
USE Identitylakehouse;
GO

---------------------------------------
-- Table 1: 0 to 500,000
---------------------------------------
IF OBJECT_ID('bronze.api_data_aadhar_demographic_500000_1000000', 'U') IS NOT NULL
    DROP TABLE bronze.api_data_aadhar_demographic_500000_1000000;
GO

CREATE TABLE bronze.api_data_aadhar_demographic_500000_1000000 (
    [date]           NVARCHAR(50),  -- Changed from DATE to NVARCHAR
    [state]          NVARCHAR(100), -- Increased size to avoid truncation
    [district]       NVARCHAR(100), -- Increased size
    [pincode]        NVARCHAR(20),  -- NVARCHAR handles leading zeros better
     [demo_age_5_17]     INT,
    [demo_age_7]       INT
);
GO

---------------------------------------
-- Table 2: 500,000 to 1,000,000
---------------------------------------
IF OBJECT_ID('bronze.api_data_aadhar_demographic_1000000_1500000', 'U') IS NOT NULL
    DROP TABLE bronze.api_data_aadhar_demographic_1000000_1500000;
GO

CREATE TABLE bronze.api_data_aadhar_demographic_1000000_1500000(
    [date]           NVARCHAR(50),
    [state]          NVARCHAR(100),
    [district]       NVARCHAR(100),
    [pincode]        NVARCHAR(20),
    [demo_age_5_17]     INT,
    [demo_age_7]       INT
);
GO

---------------------------------------
-- Table 3: 1,000,000 to 1,006,029
---------------------------------------
IF OBJECT_ID('bronze.api_data_aadhar_demographic_1500000_2000000', 'U') IS NOT NULL
    DROP TABLE bronze.api_data_aadhar_demographic_1500000_2000000;
GO

CREATE TABLE bronze.api_data_aadhar_demographic_1500000_2000000 (
    [date]           NVARCHAR(50),
    [state]          NVARCHAR(100),
    [district]       NVARCHAR(100),
    [pincode]        NVARCHAR(20),
    [demo_age_5_17]     INT,
    [demo_age_7]       INT
);
GO
IF OBJECT_ID('bronze.api_data_aadhar_demographic_2000000_2071700', 'U') IS NOT NULL
    DROP TABLE bronze.api_data_aadhar_demographic_2000000_2071700;
GO

CREATE TABLE bronze.api_data_aadhar_demographic_2000000_2071700 (
    [date]           NVARCHAR(50),
    [state]          NVARCHAR(100),
    [district]       NVARCHAR(100),
    [pincode]        NVARCHAR(20),
    [demo_age_5_17]     INT,
    [demo_age_7]       INT
);


