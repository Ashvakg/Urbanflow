-- PILLAR 2: THE WINDOW
-- This creates a link to the S3 bucket where your 15M rows live.
CREATE OR REPLACE STAGE URBANFLOW_DB.SILVER.S3_SILVER_STAGE
  STORAGE_INTEGRATION = S3_INTEGRATION
  URL = 's3://urbanflow-silver-dev/'
  FILE_FORMAT = (TYPE = 'PARQUET');

-- PILLAR 3: THE HOME
-- We use VARIANT because Parquet is complex data. 
-- This table is our "Landing Strip."
CREATE OR REPLACE TABLE URBANFLOW_DB.RAW.TAXI_DATA_RAW (
    raw_file_content VARIANT,
    ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- PILLAR 4: THE LOAD
-- This is the engine that moved your 15.1M rows.
COPY INTO URBANFLOW_DB.RAW.TAXI_DATA_RAW (raw_file_content)
FROM @URBANFLOW_DB.SILVER.S3_SILVER_STAGE
FILE_FORMAT = (TYPE = 'PARQUET')
ON_ERROR = 'CONTINUE';

-- PILLAR 5: THE VIEW (Preparation for dbt)
-- This "flattens" the JSON/Parquet structure into readable columns.
CREATE OR REPLACE VIEW URBANFLOW_DB.RAW.VW_TAXI_DATA_EXTRACTED AS 
CREATE OR REPLACE VIEW URBANFLOW_DB.RAW.VW_TAXI_DATA_EXTRACTED AS
SELECT
    raw_file_content:VendorID::INT as vendor_id,
    raw_file_content:tpep_pickup_datetime::TIMESTAMP_NTZ as pickup_datetime,
    raw_file_content:tpep_dropoff_datetime::TIMESTAMP_NTZ as dropoff_datetime,
    raw_file_content:passenger_count::INT as passenger_count,
    raw_file_content:trip_distance::FLOAT as trip_distance,
    raw_file_content:fare_amount::FLOAT as fare_amount,
    raw_file_content:total_amount::FLOAT as total_amount,
    ingested_at
FROM URBANFLOW_DB.RAW.TAXI_DATA_RAW;