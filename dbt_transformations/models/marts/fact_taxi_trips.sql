{{ config(materialized='table') }}

SELECT
    trip_id,
    vendor_id,
    pickup_datetime,
    dropoff_datetime,
    trip_distance,
    fare_amount,
    tip_amount,
    (fare_amount + tip_amount) as total_revenue,
    datediff('minute', pickup_datetime, dropoff_datetime) as duration_min,
    -- THE "ENGINEERING" MAGIC:
    CASE 
        WHEN duration_min > 0 THEN (trip_distance / (duration_min / 60)) 
        ELSE 0 
    END as avg_speed_mph,
    (tip_amount / NULLIF(fare_amount, 0)) * 100 as tip_percentage
FROM {{ ref('stg_taxi_trips') }}
WHERE trip_distance > 0 AND fare_amount > 0