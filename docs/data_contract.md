# UrbanFlow Data Contract – Yellow Taxi Trips

## Contract Metadata
- **Dataset:** yellow_taxi_trips
- **Contract Version:** 1.0.0
- **Status:** Draft
- **Owner:** UrbanFlow Data Team
- **Source:** NYC TLC – Yellow Taxi Trip Records

---

## Interface / Delivery
- **Update Frequency:** Monthly
- **File Format:** CSV
- **Encoding:** UTF-8
- **Timezone:** America/New_York
- **Expected Arrival:** By the 5th day of the following month

---

## Schema Definition

| Column Name | Data Type | Nullable | Description | Constraints |
|------------|-----------|----------|-------------|-------------|
| VendorID | integer | No | Taxi provider identifier | Positive integer |
| tpep_pickup_datetime | timestamp | No | Trip pickup datetime | Valid timestamp |
| tpep_dropoff_datetime | timestamp | No | Trip dropoff datetime | ≥ pickup time |
| passenger_count | float | No | Number of passengers | ≥ 0 |
| trip_distance | float | No | Trip distance in miles | ≥ 0 |
| RatecodeID | float | No | Rate code for the trip | ≥ 1 |
| store_and_fwd_flag | string | No | Stored before sending flag (Y/N) | Values: Y, N |
| PULocationID | integer | No | Pickup location ID | Valid TLC zone |
| DOLocationID | integer | No | Dropoff location ID | Valid TLC zone |
| payment_type | integer | No | Payment method code | ≥ 1 |
| fare_amount | float | No | Base fare amount | ≥ 0 |
| extra | float | No | Extra charges | ≥ 0 |
| mta_tax | float | No | MTA tax | ≥ 0 |
| tip_amount | float | No | Tip amount | ≥ 0 |
| tolls_amount | float | No | Toll charges | ≥ 0 |
| improvement_surcharge | float | No | Improvement surcharge | ≥ 0 |
| total_amount | float | No | Total trip cost | ≥ 0 |
| congestion_surcharge | float | No | Congestion surcharge | ≥ 0 |
| Airport_fee | float | No | Airport pickup/dropoff fee | ≥ 0 |
| cbd_congestion_fee | float | No | Central Business District congestion fee | ≥ 0 |

---

## Data Quality Rules

### Critical (Fail Job)
- All columns listed in the schema must exist
- No NULL values in non-nullable columns
- `tpep_dropoff_datetime >= tpep_pickup_datetime`
- Monetary fields must be numeric and ≥ 0
- `store_and_fwd_flag` must be either `Y` or `N`

### Warnings (Log but Continue)
- `passenger_count` > 6
- `trip_distance` > 300 miles
- `total_amount` > 1000

---

## Change Policy

### Breaking Changes
- Removing a column
- Renaming a column
- Changing a column’s data type
- Changing column meaning

### Non-Breaking Changes
- Adding a new nullable column
- Adding new valid codes (e.g., payment types)

---

## Notes
- Source files may be re-published by NYC TLC for historical months
- Numeric fields are floats in raw data and may be cast to decimals downstream
- Data is intended for analytical use only
