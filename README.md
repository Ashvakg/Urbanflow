# 🚕 UrbanFlow — Cloud Lakehouse Platform for Urban Mobility Analytics

> **A production-grade data engineering portfolio project** demonstrating end-to-end lakehouse architecture on AWS using NYC Taxi & Limousine Commission (TLC) trip record data. Built to reflect real-world design decisions around scalability, data quality, and self-serve analytics.

[![AWS](https://img.shields.io/badge/AWS-Cloud%20Platform-FF9900?logo=amazonaws)](https://aws.amazon.com/)
[![Snowflake](https://img.shields.io/badge/Snowflake-Data%20Warehouse-29B5E8?logo=snowflake)](https://www.snowflake.com/)
[![dbt](https://img.shields.io/badge/dbt-Transformation-FF694B?logo=dbt)](https://www.getdbt.com/)
[![Apache Spark](https://img.shields.io/badge/Apache%20Spark-Processing-E25A1C?logo=apachespark)](https://spark.apache.org/)
[![Dagster](https://img.shields.io/badge/Dagster-Orchestration-6B4FBB)](https://dagster.io/)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?logo=terraform)](https://www.terraform.io/)

---

## 📌 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack & Design Decisions](#3-tech-stack--design-decisions)
4. [Data Source](#4-data-source)
5. [Medallion Layer Design](#5-medallion-layer-design)
6. [Pipeline Walkthrough](#6-pipeline-walkthrough)
7. [dbt Transformation Layer](#7-dbt-transformation-layer)
8. [Orchestration with Dagster](#8-orchestration-with-dagster)
9. [Infrastructure as Code (Terraform)](#9-infrastructure-as-code-terraform)
10. [Data Quality & Testing](#10-data-quality--testing)
11. [Key Analytical Outputs](#12-key-analytical-outputs)
12. [Challenges & Solutions](#13-challenges--solutions)
13. [Future Roadmap](#14-future-roadmap)
14. [Interview Q&A Reference](#15-interview-qa-reference)

---

## 1. Project Overview

**UrbanFlow** is a cloud lakehouse platform that ingests, processes, and models New York City taxi trip data to produce analytics-ready datasets for urban mobility insights. The project simulates a production data platform with:

- **Scalable ingestion** of multi-year, multi-file Parquet datasets (~3M+ rows/month)
- **Distributed processing** via PySpark for compute-heavy transformation
- **Modular SQL transformation** via dbt following the medallion architecture
- **Declarative orchestration** via Dagster with asset-based lineage
- **Cloud-native warehousing** on Snowflake with optimised clustering and virtual warehouses
- **Infrastructure reproducibility** via Terraform

The project deliberately mirrors the structure and thinking of a real analytics engineering or data platform role — not a tutorial walkthrough.

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          DATA SOURCES                                │
│          NYC TLC Trip Record Data (Parquet, monthly files)           │
│          https://www.nyc.gov/site/tlc/about/tlc-trip-record-data     │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        INGESTION LAYER (AWS)                         │
│                                                                      │
│   ┌─────────────┐     ┌──────────────┐     ┌──────────────────────┐ │
│   │  Python     │────▶│   AWS S3     │────▶│   AWS Glue Catalog   │ │
│   │  Ingestion  │     │  (Raw Zone)  │     │   (Schema Registry)  │ │
│   │  Script     │     │              │     │                      │ │
│   └─────────────┘     └──────────────┘     └──────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER (PySpark / EMR)                  │
│                                                                      │
│   Raw Parquet ──▶ Schema Enforcement ──▶ Deduplication              │
│                ──▶ Null Handling      ──▶ Type Casting               │
│                ──▶ Partition Writing  ──▶ S3 Processed Zone          │
└──────────────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    SNOWFLAKE (Cloud Data Warehouse)                   │
│                                                                      │
│   BRONZE (Raw Stage)  ──▶  SILVER (Cleaned/Conformed)               │
│                        ──▶  GOLD (Business/Analytical Models)        │
│                                                                      │
│   Managed via dbt (models, tests, docs, snapshots)                  │
└──────────────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│               ORCHESTRATION & OBSERVABILITY (Dagster)                │
│                                                                      │
│   Asset Graph ──▶ Partitioned Jobs ──▶ Schedules ──▶ Alerts         │
└──────────────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│             ANALYTICS / CONSUMPTION LAYER (BI / SQL)                 │
│                                                                      │
│   Gold Layer SQL ──▶ BI Tool Connections (Tableau / Power BI ready) │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack & Design Decisions

| Layer | Tool | Why Chosen |
|---|---|---|
| Cloud Platform | **AWS** | Industry-standard; S3 for durable object storage, IAM for fine-grained security |
| Data Warehouse | **Snowflake** | Separation of storage and compute; instant elasticity; Parquet-native COPY INTO |
| Transformation | **dbt Core** | Version-controlled SQL; built-in testing; lineage DAG; documentation generation |
| Processing | **PySpark (EMR)** | Handles 100M+ row datasets efficiently; columnar Parquet native; parallelism |
| Orchestration | **Dagster** | Asset-centric model aligns with modern data engineering; native dbt integration |
| IaC | **Terraform** | Reproducible, versioned infrastructure; avoids cloud console drift |
| Format | **Parquet** | Columnar; highly compressed; Snowflake, Spark, and Athena all read natively |
| Partitioning | **Year/Month** | Aligns with TLC data release cadence; enables partition pruning in queries |

### Why not Airflow?
Dagster was chosen over Airflow because its **asset-based model** makes data lineage explicit — every asset knows what it produces and what it depends on. This maps naturally to how analysts think about data, and avoids "task soup" in DAGs where the data contract between steps is implicit.

### Why not Databricks?
EMR + Snowflake was chosen to demonstrate understanding of the **multi-tool open ecosystem** rather than a single-vendor stack. In practice, this also reduces lock-in and maps to many mid-market company architectures.

### Why Snowflake over Redshift or BigQuery?
- **Snowflake's external stage + COPY INTO** pattern allows S3 to remain the source of truth without data duplication at load time
- **Virtual warehouses** can be suspended automatically, making costs predictable
- **Role-based access control** is granular and maps directly to business unit separation

---

## 4. Data Source

**NYC TLC Trip Record Data**
- Source: [NYC Open Data / TLC](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
- Format: Parquet (monthly files, ~100–400MB per file)
- Record types used: **Yellow Taxi**, **Green Taxi**, **For-Hire Vehicle (FHV)**
- Key fields: pickup/dropoff datetime, pickup/dropoff location ID, passenger count, trip distance, fare amount, tip amount, payment type, rate code

**Volume:**
| Year | Yellow Taxi Rows |
|------|-----------------|
| 2022 | ~35M |
| 2023 | ~38M |
| 2024 | ~40M (partial) |

**Lookup Tables:**
- `taxi_zone_lookup.csv` — maps location IDs to borough, zone, and service zone
- `payment_type_lookup` — maps payment type codes to descriptions

---

## 5. Medallion Layer Design

UrbanFlow follows a strict **three-layer medallion architecture** inside Snowflake, managed entirely through dbt.

### 🥉 Bronze — Raw Ingestion
- **Purpose:** Exact replica of source data loaded from S3 via Snowflake external stage
- **No transformations.** Data is loaded as-is.
- **Schema:** Source schema with a `_loaded_at` metadata column appended
- **Database:** `URBANFLOW_RAW`
- **Example table:** `raw_yellow_trips`

### 🥈 Silver — Cleaned & Conformed
- **Purpose:** Enforce schema, fix data types, handle nulls, deduplicate, standardise naming
- **Transformations applied:**
  - `pickup_datetime` / `dropoff_datetime` cast from string to TIMESTAMP_NTZ
  - `passenger_count` nulls defaulted to 0 with a flag column
  - Negative `fare_amount` records filtered with dbt test + logged to a bad-data table
  - Location IDs joined to the zone lookup table to enrich with borough/zone names
  - Deduplication on `(vendor_id, pickup_datetime, dropoff_datetime, pu_location_id)`
- **Database:** `URBANFLOW_SILVER`
- **Example table:** `stg_yellow_trips`

### 🥇 Gold — Business-Ready Models
- **Purpose:** Aggregated, dimensional, and metric tables for analytics consumption
- **Models:**
  - `fct_trips` — fact table at trip grain with all enriched attributes
  - `dim_zones` — zone dimension with borough, service zone, coordinates
  - `dim_time` — date spine with time attributes (hour, day of week, is_weekend, is_peak_hour)
  - `agg_daily_revenue` — daily revenue by borough and payment type
  - `agg_hourly_demand` — pickup volume by hour and zone
  - `agg_driver_efficiency` — avg trip distance, duration, fare per pickup zone
- **Database:** `URBANFLOW_GOLD`

---

## 6. Pipeline Walkthrough

### Step 1 — Ingestion
```python
# ingestion/download_tlc_data.py
# Downloads monthly Parquet files from TLC S3 bucket
# Uploads to s3://urbanflow-raw/yellow_taxi/year=YYYY/month=MM/
```
- Parameterised by year and month
- Idempotent — skips if file already exists in target S3 path
- Logs file size, row count, and upload time to a metadata table in Snowflake

### Step 2 — PySpark Processing (EMR)
```
Raw Parquet (S3 raw zone)
    ↓
Schema validation (enforce expected column types)
    ↓
Null/outlier handling (e.g., trip_distance > 500 flagged)
    ↓
Deduplication (dropDuplicates on key columns)
    ↓
Write to S3 processed zone (year/month partitioned)
```

Key PySpark patterns used:
- `spark.read.parquet()` with schema enforcement (not inferred) to avoid schema drift
- Window functions for deduplication: `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)`
- Broadcast joins for small lookup tables (zone lookup ~300 rows)

### Step 3 — Snowflake Load (COPY INTO)
```sql
COPY INTO URBANFLOW_RAW.PUBLIC.RAW_YELLOW_TRIPS
FROM @urbanflow_s3_stage/yellow_taxi/
FILE_FORMAT = (TYPE = PARQUET)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = CONTINUE;
```

- External stage points to S3 with IAM role-based auth (no hardcoded keys)
- `ON_ERROR = CONTINUE` used in Bronze; Silver tests catch bad records
- Loaded with metadata column `_loaded_at = CURRENT_TIMESTAMP()`

### Step 4 — dbt Transformations
```
dbt run --select staging.*       # Bronze → Silver
dbt run --select marts.*         # Silver → Gold
dbt test                         # Run all data quality tests
dbt docs generate && dbt docs serve  # Generate lineage docs
```

### Step 5 — Dagster Orchestration
- All steps above are wrapped as **Dagster assets**
- A daily schedule triggers the pipeline for the prior month's data
- Asset materialisation status is visible in the Dagster UI
- Failed asset runs trigger Slack alerts via webhook sensor

---

## 7. dbt Transformation Layer

### Project Structure
```
urbanflow_dbt/
├── models/
│   ├── staging/
│   │   ├── _staging__sources.yml      # Source definitions + freshness tests
│   │   ├── stg_yellow_trips.sql
│   │   ├── stg_green_trips.sql
│   │   └── stg_fhv_trips.sql
│   ├── intermediate/
│   │   └── int_trips_unioned.sql      # Union yellow + green with shared schema
│   └── marts/
│       ├── core/
│       │   ├── fct_trips.sql
│       │   ├── dim_zones.sql
│       │   └── dim_time.sql
│       └── analytics/
│           ├── agg_daily_revenue.sql
│           ├── agg_hourly_demand.sql
│           └── agg_driver_efficiency.sql
├── tests/
│   ├── assert_no_negative_fares.sql
│   └── assert_trip_duration_positive.sql
├── macros/
│   ├── generate_schema_name.sql       # Custom schema routing
│   └── safe_divide.sql                # Null-safe division macro
├── snapshots/
│   └── snap_zone_lookup.sql           # SCD Type 2 on zone reference data
├── seeds/
│   ├── payment_type_lookup.csv
│   └── rate_code_lookup.csv
└── dbt_project.yml
```

### Key dbt Patterns Used

**Incremental models** — Silver trip tables use `is_incremental()` to only process new records:
```sql
{{ config(
    materialized='incremental',
    unique_key='trip_id',
    incremental_strategy='merge',
    cluster_by=['pickup_date']
) }}

SELECT ...
{% if is_incremental() %}
WHERE _loaded_at > (SELECT MAX(_loaded_at) FROM {{ this }})
{% endif %}
```

**Custom tests** — Beyond built-in `not_null` and `unique`:
```sql
-- tests/assert_no_negative_fares.sql
SELECT trip_id
FROM {{ ref('stg_yellow_trips') }}
WHERE fare_amount < 0
```

**Source freshness** — Alerts if raw data hasn't been updated within expected SLA:
```yaml
sources:
  - name: raw
    freshness:
      warn_after: {count: 25, period: hour}
      error_after: {count: 49, period: hour}
    loaded_at_field: _loaded_at
```

**Documentation** — Every model and column has a description in `.yml` files, auto-rendered in `dbt docs`.

---

## 8. Orchestration with Dagster

### Asset Graph Design
```
download_raw_files          (partitioned by month)
        │
        ▼
spark_process_raw           (partitioned by month)
        │
        ▼
snowflake_load_bronze       (partitioned by month)
        │
        ▼
dbt_staging_models          (depends on bronze assets)
        │
        ▼
dbt_mart_models             (depends on staging assets)
        │
        ▼
analytics_ready_signal      (final asset, triggers BI refresh)
```

### Why Asset-Based Orchestration?
With Dagster's software-defined assets:
- **Lineage is explicit** — you can trace any gold model back to the raw S3 file
- **Backfills are safe** — re-materialise a specific month partition without full reruns
- **Observability** — asset materialisation history tracked natively; no custom logging

### Partitioning Strategy
```python
monthly_partition = MonthlyPartitionsDefinition(start_date="2022-01")
```
- Each partition = one calendar month of TLC data
- Allows selective backfill (e.g., reload January 2023 without touching other months)
- dbt incremental models align with this — only process the relevant month's records

---

## 9. Infrastructure as Code (Terraform)

### Resources Managed

```hcl
# S3 Buckets
resource "aws_s3_bucket" "urbanflow_raw" { ... }
resource "aws_s3_bucket" "urbanflow_processed" { ... }

# IAM Role for Snowflake External Stage
resource "aws_iam_role" "snowflake_s3_access" { ... }
resource "aws_iam_policy" "s3_read_policy" { ... }

# EMR Cluster (on-demand for Spark jobs)
resource "aws_emr_cluster" "urbanflow_spark" { ... }

# Snowflake Resources (via Snowflake Terraform Provider)
resource "snowflake_database" "urbanflow_raw" { ... }
resource "snowflake_warehouse" "urbanflow_wh" {
  warehouse_size = "X-SMALL"
  auto_suspend   = 60
  auto_resume    = true
}
resource "snowflake_stage" "s3_external_stage" { ... }
```

### Key Principles
- **No hardcoded credentials** — Snowflake auth via key-pair; AWS via IAM roles
- **Remote state** — Terraform state stored in S3 + DynamoDB lock table
- **Workspace separation** — `dev` and `prod` workspaces with separate variable files
- **Auto-suspend** on Snowflake warehouse set to 60s — cost control

---

## 10. Data Quality & Testing

### Testing Pyramid

| Level | Tool | What is tested |
|---|---|---|
| Schema | dbt `not_null`, `unique` | All primary keys, critical FK fields |
| Range | dbt custom tests | Fare ≥ 0, trip_distance ≥ 0, duration > 0 |
| Referential integrity | dbt `relationships` | All location IDs exist in dim_zones |
| Freshness | dbt source freshness | Raw data loaded within SLA window |
| Row count | Dagster asset checks | Silver row count ≥ 95% of Bronze |
| Statistical | PySpark validation | Fare amount Z-score outlier detection |

### Handling Bad Data
- Records failing Bronze tests are **not blocked** — they load into Bronze as-is
- Silver models **filter** bad records and write them to a `_rejected` table with a reason code
- Gold models only consume Silver-validated data
- This pattern allows full auditability: you can always trace back why a record was excluded

---

## 11. Key Analytical Outputs

### 1. Demand Heatmap by Hour and Borough
- Peak demand: Manhattan weekdays 08:00–09:00 and 17:00–19:00
- Brooklyn pickups spike on Friday/Saturday evenings

### 2. Revenue per Mile by Zone
- JFK Airport and Midtown zones consistently show highest revenue/mile (flat rate + tips)
- Far Rockaway and Staten Island ferry zones show lowest revenue density

### 3. Payment Type Trends
- Credit card payments grew from ~65% (2022) to ~78% (2024)
- Cash trip share declining across all boroughs

### 4. Tip Behaviour Analysis
- Tip rate strongly correlated with payment type (credit card: avg 18.4%, cash: 0%)
- Pre-paid flat-rate trips (JFK) show lower tip rates than metered trips

### 5. Trip Duration vs. Distance Efficiency
- Airport trips show longest distance with predictable duration
- Midtown short trips show highest duration variability (traffic sensitivity)

---

## 12. Challenges & Solutions

### Challenge 1: Schema Drift Across TLC Monthly Files
**Problem:** TLC changed column names and data types across years (e.g., `RatecodeID` → `RateCodeID`; field additions in 2023).

**Solution:** Defined a **canonical schema** in PySpark with explicit `StructType`. Any file not conforming is flagged and sent to a schema-mismatch S3 path for manual review. dbt source schema tests provide a second line of defence.

---

### Challenge 2: Incremental Model Deduplication
**Problem:** TLC occasionally republishes corrected files for prior months, causing duplicate records on reload.

**Solution:** Used dbt `incremental_strategy='merge'` with a composite `unique_key` on `(vendor_id, pickup_datetime, dropoff_datetime, pu_location_id)`. Upserts ensure corrected records overwrite originals without duplicating.

---

### Challenge 3: Snowflake Cost Control at Development Scale
**Problem:** Running full Spark jobs and Snowflake queries during development was expensive.

**Solution:**
- Dagster `dev` asset config uses a 10% sample of raw data
- Snowflake auto-suspend set to 60 seconds
- dbt `--target dev` points to a separate `DEV` database with a smaller warehouse (XS vs S in prod)
- Terraform workspace separation prevents accidental prod runs

---

### Challenge 4: Orchestrating dbt within Dagster
**Problem:** Ensuring dbt models are represented as first-class assets in Dagster (not just a shell command in a task).

**Solution:** Used `dagster-dbt` integration with `load_assets_from_dbt_project()` — this parses the dbt `manifest.json` and automatically creates one Dagster asset per dbt model, preserving the full lineage graph natively.

---

## 13. Future Roadmap

- [ ] **Streaming ingestion** — Replace batch S3 download with Kinesis Data Firehose for near-real-time trips
- [ ] **Great Expectations** — Add GE checkpoints as an additional data quality layer at the Spark processing step
- [ ] **dbt Semantic Layer** — Expose Gold metrics via dbt's semantic layer for Metabase/Tableau direct query
- [ ] **ML feature store** — Build a `fct_trip_features` table suitable for demand forecasting model training
- [ ] **Cost monitoring** — Integrate Snowflake QUERY_HISTORY and Terraform cost estimation into CI pipeline
- [ ] **CI/CD** — GitHub Actions pipeline: `dbt parse` → `dbt test --select state:modified` → merge gate

---

## 14. Interview Q&A Reference

> This section exists to help you recall design decisions quickly in interviews.

---

**Q: Why did you build this project?**
> My day-to-day professional experience is primarily Microsoft-stack (Fabric, Power BI, Dynamics 365). UrbanFlow was built to demonstrate that I can design and build a cloud lakehouse from scratch using the open-source modern data stack — and that I can make principled architectural decisions, not just follow a tutorial.

---

**Q: Walk me through the data flow.**
> Raw Parquet files are downloaded from NYC TLC and landed in S3. PySpark on EMR handles schema enforcement, deduplication, and null handling before writing to a processed S3 zone. Snowflake's COPY INTO loads from an external S3 stage into the Bronze layer. dbt manages all transformations across Bronze → Silver → Gold following the medallion pattern. Dagster orchestrates all assets with monthly partitioning, full lineage, and Slack alerting.

---

**Q: Why Snowflake over BigQuery or Redshift?**
> Snowflake's external stage pattern keeps S3 as the source of truth — you're not copying data, you're referencing it. The virtual warehouse auto-suspend keeps costs low during development. And the Snowflake Terraform provider made infrastructure reproducibility clean. BigQuery would have been a strong alternative, but I wanted to work with a stack common in the European enterprise market.

---

**Q: How do you handle schema changes in the source data?**
> The PySpark layer enforces a canonical StructType schema. Any deviation routes the file to a schema-mismatch path and alerts via Dagster. At the dbt layer, source schema tests provide a second validation. This means schema drift is caught immediately at ingestion — not discovered days later when a downstream dashboard breaks.

---

**Q: How do you ensure data quality?**
> Multi-layer approach: PySpark validates at ingestion (range checks, null rates, Z-score outlier detection). dbt provides structural tests (not_null, unique, relationships, freshness). Custom SQL tests cover business rules. Bad records in Silver are written to `_rejected` tables with reason codes — nothing is silently dropped. Dagster asset checks validate row count ratios between Bronze and Silver.

---

**Q: How do you manage costs in a cloud project like this?**
> Snowflake warehouses auto-suspend after 60 seconds of inactivity. Dev environment uses 10% data samples and an XS warehouse. Terraform workspaces isolate dev and prod infrastructure. EMR clusters are on-demand — spun up per job, terminated after. S3 lifecycle policies move old raw files to Glacier after 90 days.

---

**Q: What would you do differently if this were a production system at a company?**
> I'd add: proper secrets management (AWS Secrets Manager instead of `.env` files), CI/CD for dbt with `state:modified` runs, a data contract layer between teams, monitoring dashboards on pipeline latency and data freshness SLAs, and a formal incident response runbook for pipeline failures.

---

**Q: How does Dagster compare to Airflow in your experience?**
> Airflow is task-centric — you define the order of operations. Dagster is asset-centric — you define what data is produced and what it depends on. For analytics engineering workloads, this maps much better to how you think about data. Lineage is automatic, backfills are partition-aware, and the UI surfaces data quality status alongside pipeline status. Airflow has a larger ecosystem and more production mileage at large scale, but for a modern data platform, Dagster's model is meaningfully better for observability.

---

**Q: What is the medallion architecture and why use it?**
> Bronze-Silver-Gold. Bronze = raw data, exactly as it arrived, never modified. Silver = cleaned, typed, deduplicated, enriched — business rules applied, bad data quarantined. Gold = aggregated, business-ready models for consumption. The separation is important: if a business rule changes, you only re-run Silver and Gold, not re-ingest from source. It also makes debugging much easier — you can pinpoint which layer introduced a data issue.

---

**Q: How do incremental dbt models work and when would you not use them?**
> Incremental models only process new or changed records since the last run, using a watermark (e.g., `_loaded_at`). You'd use them when full refreshes are too slow or expensive. You wouldn't use them when: the source data changes historically (TLC does release corrected files), the deduplication logic requires full dataset context, or when the table is small enough that a full refresh is trivially fast. For TLC data, I use incremental with `strategy='merge'` to handle late-arriving corrections.

---

*Built by Ashvak Govindarajula | [LinkedIn](https://linkedin.com/in/ash-gov)*
