{{ config(materialized='table') }}

SELECT
    CASE 
        WHEN avg_speed_mph < 10 THEN '1. Gridlock (0-10 mph)'
        WHEN avg_speed_mph < 20 THEN '2. Heavy (10-20 mph)'
        ELSE '3. Free Flow (20+ mph)'
    END as traffic_condition,
    COUNT(*) as trip_count,
    ROUND(AVG(tip_percentage), 2) as avg_tip_pct,
    ROUND(AVG(total_revenue), 2) as avg_revenue_per_trip,
    -- Does gridlock reduce tips?
    ROUND(SUM(total_revenue), 0) as total_economic_value
FROM {{ ref('fact_taxi_trips') }}
GROUP BY 1
ORDER BY 1