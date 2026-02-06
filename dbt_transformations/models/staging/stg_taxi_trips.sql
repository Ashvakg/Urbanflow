{{ config(materialized='view') }}

WITH raw_source AS (
    SELECT * FROM {{ source('raw_data', 'TAXI_DATA_RAW') }}
)

SELECT
    -- Added dropoff and passenger count to make the ID more unique
    md5(cast(concat(
        raw_file_content:tpep_pickup_datetime::text, 
        raw_file_content:tpep_dropoff_datetime::text,
        raw_file_content:VendorID::text,
        raw_file_content:passenger_count::text
    ) as varchar)) as trip_id,
    
    raw_file_content:VendorID::INT as vendor_id,
    raw_file_content:tpep_pickup_datetime::TIMESTAMP_NTZ as pickup_datetime,
    raw_file_content:tpep_dropoff_datetime::TIMESTAMP_NTZ as dropoff_datetime,
    raw_file_content:passenger_count::INT as passenger_count,
    raw_file_content:trip_distance::FLOAT as trip_distance,
    raw_file_content:fare_amount::FLOAT as fare_amount,
    raw_file_content:tip_amount::FLOAT as tip_amount,
    raw_file_content:total_amount::FLOAT as total_amount
FROM raw_source
WHERE raw_file_content:fare_amount::FLOAT > 0

-- Optional: If you still have duplicate files in S3, use this to keep only one
QUALIFY row_number() OVER (PARTITION BY trip_id ORDER BY pickup_datetime) = 1