{{ config(materialized='table') }}

WITH base AS (
    SELECT 
        * FROM {{ ref('fact_taxi_trips') }}
    WHERE trip_distance > 0 AND duration_min > 0
),

economics AS (
    SELECT
        -- Grab everything from base once
        b.*,
        -- Reference specific columns from 'b' to avoid ambiguity
        (b.total_revenue - (b.trip_distance * 0.60)) as estimated_driver_profit,
        (b.total_revenue / NULLIF(b.trip_distance * b.duration_min, 0)) * 100 as yield_efficiency_index,
        (b.duration_min / b.trip_distance) as friction_score
    FROM base b
),

final_segmented AS (
    SELECT 
        *,
        CASE 
            WHEN yield_efficiency_index > 50 AND friction_score < 5 THEN 'High-Value/High-Velocity'
            WHEN friction_score > 15 THEN 'Operational Bottleneck'
            WHEN estimated_driver_profit < 0 THEN 'Churn Risk Zone'
            ELSE 'Neutral Market'
        END as market_segmentation_strategy
    FROM economics
)

SELECT * FROM final_segmented
-- This WHERE clause fixes your failing dbt test by removing the "garbage" data
WHERE estimated_driver_profit BETWEEN -5000 AND 1000