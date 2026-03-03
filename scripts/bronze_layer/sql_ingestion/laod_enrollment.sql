--CREATE OR ALTER PROCEDURE bronze.load_enroll AS 
--BEGIN
--	DECLARE 
--	@start_time DATETIME, 
--	@end_time DATETIME,
--	@batch_start_time DATETIME,
--	@batch_end_time DATETIME; 
--	BEGIN TRY
--	 SET @batch_start_time = GETDATE();

--		PRINT '================================================';

--		PRINT 'Loading ENROLLMENT_DATA Layer';
--		PRINT '================================================';
--		PRINT '------------------------------------------------';
--		PRINT 'Loading api_data_aadhar_enrolment_0_500000';
--		PRINT '------------------------------------------------';

--		SET @start_time = GETDATE();
--		PRINT '>> Truncating Table: bronze.api_data_aadhar_enrolment_0_500000';
--		TRUNCATE TABLE bronze.api_data_aadhar_enrolment_0_500000;
--		PRINT '>> Inserting Data Into: bronze.api_data_aadhar_enrolment_0_500000';
--		BULK INSERT bronze.api_data_aadhar_enrolment_0_500000
--		FROM 'C:\Users\Atul bhardwaj\OneDrive\Desktop\coding 2 year\IdentityLakehouse\data\api_data_aadhar_enrolment\api_data_aadhar_enrolment\api_data_aadhar_enrolment_0_500000.csv'
--		WITH (
--			FIRSTROW = 2,
--			FIELDTERMINATOR = ',',
--			TABLOCK
--		);
--		SET @end_time = GETDATE();

--		PRINT '>> Load Duration: ' + CAST(DATEDIFF(second, @start_time, @end_time) AS NVARCHAR) + ' seconds';
--		PRINT '>> -------------';

--		----------------------------------------------------------------
		
--		SET @start_time = GETDATE();
--		PRINT '>> Truncating Table: bronze.api_data_aadhar_enrolment_500000_1000000';
--		TRUNCATE TABLE bronze.api_data_aadhar_enrolment_500000_1000000;
--		PRINT '>> Inserting Data Into: bronze.api_data_aadhar_enrolment_500000_1000000';
--		BULK INSERT bronze.api_data_aadhar_enrolment_500000_1000000
--		FROM 'C:\Users\Atul bhardwaj\OneDrive\Desktop\coding 2 year\IdentityLakehouse\data\api_data_aadhar_enrolment\api_data_aadhar_enrolment\api_data_aadhar_enrolment_500000_1000000.csv'
--		WITH (
--			FIRSTROW = 2,
--			FIELDTERMINATOR = ',',
--			TABLOCK
--		);
--		SET @end_time = GETDATE();

--		PRINT '>> Load Duration: ' + CAST(DATEDIFF(second, @start_time, @end_time) AS NVARCHAR) + ' seconds';
--		PRINT '>> -------------';

--		---------------------------------------------------------


--			SET @start_time = GETDATE();
--		PRINT '>> Truncating Table: bronze.api_data_aadhar_enrolment_1000000_1006029';
--		TRUNCATE TABLE bronze.api_data_aadhar_enrolment_1000000_1006029;
--		PRINT '>> Inserting Data Into: bronze.api_data_aadhar_enrolment_1000000_1006029';
--		BULK INSERT bronze.api_data_aadhar_enrolment_1000000_1006029
--		FROM 'C:\Users\Atul bhardwaj\OneDrive\Desktop\coding 2 year\IdentityLakehouse\data\api_data_aadhar_enrolment\api_data_aadhar_enrolment\api_data_aadhar_enrolment_1000000_1006029.csv'
--		WITH (
--			FIRSTROW = 2,
--			FIELDTERMINATOR = ',',
--			TABLOCK
--		);
--		SET @end_time = GETDATE();

--		PRINT '>> Load Duration: ' + CAST(DATEDIFF(second, @start_time, @end_time) AS NVARCHAR) + ' seconds';
--		CREATE OR ALTER PROCEDURE bronze.load_enroll AS 
--BEGIN
--	DECLARE 
--	@start_time DATETIME, 
--	@end_time DATETIME,
--	@batch_start_time DATETIME,
--	@batch_end_time DATETIME; 
--	BEGIN TRY
--	 SET @batch_start_time = GETDATE();

--		PRINT '================================================';

--		PRINT 'Loading ENROLLMENT_DATA Layer';
--		PRINT '================================================';
--		PRINT '------------------------------------------------';
--		PRINT 'Loading api_data_aadhar_enrolment_0_500000';
--		PRINT '------------------------------------------------';

--		SET @start_time = GETDATE();
--		PRINT '>> Truncating Table: bronze.api_data_aadhar_enrolment_0_500000';
--		TRUNCATE TABLE bronze.api_data_aadhar_enrolment_0_500000;
--		PRINT '>> Inserting Data Into: bronze.api_data_aadhar_enrolment_0_500000';
--		BULK INSERT bronze.api_data_aadhar_enrolment_0_500000
--		FROM 'C:\Users\Atul bhardwaj\OneDrive\Desktop\coding 2 year\IdentityLakehouse\data\api_data_aadhar_enrolment\api_data_aadhar_enrolment\api_data_aadhar_enrolment_0_500000.csv'
--		WITH (
--			FIRSTROW = 2,
--			FIELDTERMINATOR = ',',
--			TABLOCK
--		);
--		SET @end_time = GETDATE();

--		PRINT '>> Load Duration: ' + CAST(DATEDIFF(second, @start_time, @end_time) AS NVARCHAR) + ' seconds';
--		PRINT '>> -------------';

--		----------------------------------------------------------------
		
--		SET @start_time = GETDATE();
--		PRINT '>> Truncating Table: bronze.api_data_aadhar_enrolment_500000_1000000';
--		TRUNCATE TABLE bronze.api_data_aadhar_enrolment_500000_1000000;
--		PRINT '>> Inserting Data Into: bronze.api_data_aadhar_enrolment_500000_1000000';
--		BULK INSERT bronze.api_data_aadhar_enrolment_500000_1000000
--		FROM 'C:\Users\Atul bhardwaj\OneDrive\Desktop\coding 2 year\IdentityLakehouse\data\api_data_aadhar_enrolment\api_data_aadhar_enrolment\api_data_aadhar_enrolment_500000_1000000.csv'
--		WITH (
--			FIRSTROW = 2,
--			FIELDTERMINATOR = ',',
--			TABLOCK
--		);
--		SET @end_time = GETDATE();

--		PRINT '>> Load Duration: ' + CAST(DATEDIFF(second, @start_time, @end_time) AS NVARCHAR) + ' seconds';
--		PRINT '>> -------------';

--		---------------------------------------------------------


--			SET @start_time = GETDATE();
--		PRINT '>> Truncating Table: bronze.api_data_aadhar_enrolment_1000000_1006029';
--		TRUNCATE TABLE bronze.api_data_aadhar_enrolment_1000000_1006029;
--		PRINT '>> Inserting Data Into: bronze.api_data_aadhar_enrolment_1000000_1006029';
--		BULK INSERT bronze.api_data_aadhar_enrolment_1000000_1006029
--		FROM 'C:\Users\Atul bhardwaj\OneDrive\Desktop\coding 2 year\IdentityLakehouse\data\api_data_aadhar_enrolment\api_data_aadhar_enrolment\api_data_aadhar_enrolment_1000000_1006029.csv'
--		WITH (
--			FIRSTROW = 2,
--			FIELDTERMINATOR = ',',
--			TABLOCK
--		);
--		SET @end_time = GETDATE();

--		PRINT '>> Load Duration: ' + CAST(DATEDIFF(second, @start_time, @end_time) AS NVARCHAR) + ' seconds';
--		PRINT '>> -------------'

--	 END TRY

--    BEGIN CATCH

--        PRINT '================================================';
--        PRINT 'ERROR OCCURRED';
--        PRINT ERROR_MESSAGE();
--        PRINT '================================================';

--    END CATCH
--END;



CREATE OR ALTER PROCEDURE bronze.load_enroll 
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
        PRINT 'Loading ENROLLMENT_DATA Layer';
        PRINT '================================================';

        ------------------------------------------------
        -- FILE 1
        ------------------------------------------------
        SET @start_time = GETDATE();

        TRUNCATE TABLE bronze.api_data_aadhar_enrolment_0_500000;

        BULK INSERT bronze.api_data_aadhar_enrolment_0_500000
        FROM 'C:\Users\Atul bhardwaj\OneDrive\Desktop\coding 2 year\IdentityLakehouse\data\api_data_aadhar_enrolment\api_data_aadhar_enrolment\api_data_aadhar_enrolment_0_500000.csv'
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

        TRUNCATE TABLE bronze.api_data_aadhar_enrolment_500000_1000000;

        BULK INSERT bronze.api_data_aadhar_enrolment_500000_1000000
        FROM 'C:\Users\Atul bhardwaj\OneDrive\Desktop\coding 2 year\IdentityLakehouse\data\api_data_aadhar_enrolment\api_data_aadhar_enrolment\api_data_aadhar_enrolment_500000_1000000.csv'
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

        TRUNCATE TABLE bronze.api_data_aadhar_enrolment_1000000_1006029;

        BULK INSERT bronze.api_data_aadhar_enrolment_1000000_1006029
        FROM 'C:\Users\Atul bhardwaj\OneDrive\Desktop\coding 2 year\IdentityLakehouse\data\api_data_aadhar_enrolment\api_data_aadhar_enrolment\api_data_aadhar_enrolment_1000000_1006029.csv'
        WITH (
            FIRSTROW = 2,
            FIELDTERMINATOR = ',',
            TABLOCK
        );

        SET @end_time = GETDATE();

        PRINT 'File 3 Duration: ' + 
              CAST(DATEDIFF(SECOND, @start_time, @end_time) AS NVARCHAR) + ' seconds';

    END TRY
    BEGIN CATCH

        PRINT '================================================';
        PRINT 'ERROR OCCURRED';
        PRINT ERROR_MESSAGE();
        PRINT '================================================';

    END CATCH

END;
