
CREATE OR ALTER PROCEDURE bronze.load_biometric_data 
AS 
BEGIN

    DECLARE 
        @start_time DATETIME, 
        @end_time DATETIME,
        @batch_start_time DATETIME,
        @batch_end_time DATETIME; 

    BEGIN TRY

        SET @batch_start_time = GETDATE();

        PRINT '================================================';
        PRINT 'Loading BIOMETRIC_DATA Layer';
        PRINT '================================================';

         ------------------------------------------------
        -- FILE 1
        ------------------------------------------------

           SET @start_time = GETDATE();

        TRUNCATE TABLE bronze.api_data_aadhar_biometric_0_500000;

        BULK INSERT bronze.api_data_aadhar_biometric_0_500000
        FROM 'C:\Users\Atul bhardwaj\OneDrive\Desktop\coding 2 year\IdentityLakehouse\data\api_data_aadhar_biometric\api_data_aadhar_biometric_0_500000.csv'
        WITH (
            FIRSTROW = 2,
            FIELDTERMINATOR = ',',
            TABLOCK
        );

        SET @end_time = GETDATE();

        PRINT 'File 1 Duration: ' + 
              CAST(DATEDIFF(SECOND, @start_time, @end_time) AS NVARCHAR) + ' seconds';

        ------------------------------------------------
        -- FILE 2
        ------------------------------------------------
        SET @start_time = GETDATE();

        TRUNCATE TABLE bronze.api_data_aadhar_biometric_500000_1000000;

        BULK INSERT bronze.api_data_aadhar_biometric_500000_1000000
        FROM 'C:\Users\Atul bhardwaj\OneDrive\Desktop\coding 2 year\IdentityLakehouse\data\api_data_aadhar_biometric\api_data_aadhar_biometric_500000_1000000.csv'
        WITH (
            FIRSTROW = 2,
            FIELDTERMINATOR = ',',
            TABLOCK
        );

        SET @end_time = GETDATE();

        PRINT 'File 2 Duration: ' + 
              CAST(DATEDIFF(SECOND, @start_time, @end_time) AS NVARCHAR) + ' seconds';

        ------------------------------------------------
        -- FILE 3
        ------------------------------------------------
        SET @start_time = GETDATE();

        TRUNCATE TABLE bronze.api_data_aadhar_biometric_1000000_1500000;

        BULK INSERT bronze.api_data_aadhar_biometric_1000000_1500000
        FROM 'C:\Users\Atul bhardwaj\OneDrive\Desktop\coding 2 year\IdentityLakehouse\data\api_data_aadhar_biometric\api_data_aadhar_biometric_1000000_1500000.csv'
        WITH (
            FIRSTROW = 2,
            FIELDTERMINATOR = ',',
            TABLOCK
        );

        SET @end_time = GETDATE();

        PRINT 'File 3 Duration: ' + 
              CAST(DATEDIFF(SECOND, @start_time, @end_time) AS NVARCHAR) + ' seconds';

        ------------------------------------------------
        -- FILE 4
        ------------------------------------------------
        SET @start_time = GETDATE();

        TRUNCATE TABLE bronze.api_data_aadhar_biometric_1500000_1861108;

        BULK INSERT bronze.api_data_aadhar_biometric_1500000_1861108
        FROM 'C:\Users\Atul bhardwaj\OneDrive\Desktop\coding 2 year\IdentityLakehouse\data\api_data_aadhar_biometric\api_data_aadhar_biometric_1500000_1861108.csv'
        WITH (
            FIRSTROW = 2,
            FIELDTERMINATOR = ',',
            TABLOCK
        );

        SET @end_time = GETDATE();

        PRINT 'File 4 Duration: ' + 
              CAST(DATEDIFF(SECOND, @start_time, @end_time) AS NVARCHAR) + ' seconds';

      

    END TRY
    BEGIN CATCH

        PRINT '================================================';
        PRINT 'ERROR OCCURRED';
        PRINT ERROR_MESSAGE();
        PRINT '================================================';

    END CATCH

END;



