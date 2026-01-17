from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType,
    IntegerType, TimestampType, DoubleType
)
from pyspark.sql import functions as F

# ============================================================
# CONFIG
# ============================================================
CSV_PATH = "/opt/spark-data/yellow_tripdata_2025-11.csv"
TIMESTAMP_FMT = "yyyy-MM-dd HH:mm:ss"
EARLIEST_ALLOWED_DATE = "2009-01-01 00:00:00"

# If you have a unique trip id column, set it here (else leave None)
TRIP_ID_COL = None  # e.g. "trip_id"

# ============================================================
# SCHEMA (matches your CSV header)
# ============================================================
schema = StructType([
    StructField("VendorID", IntegerType(), True),
    StructField("tpep_pickup_datetime", TimestampType(), True),
    StructField("tpep_dropoff_datetime", TimestampType(), True),
    StructField("passenger_count", DoubleType(), True),
    StructField("trip_distance", DoubleType(), True),
    StructField("RatecodeID", DoubleType(), True),
    StructField("store_and_fwd_flag", StringType(), True),
    StructField("PULocationID", IntegerType(), True),
    StructField("DOLocationID", IntegerType(), True),
    StructField("payment_type", IntegerType(), True),
    StructField("fare_amount", DoubleType(), True),
    StructField("extra", DoubleType(), True),
    StructField("mta_tax", DoubleType(), True),
    StructField("tip_amount", DoubleType(), True),
    StructField("tolls_amount", DoubleType(), True),
    StructField("improvement_surcharge", DoubleType(), True),
    StructField("total_amount", DoubleType(), True),
    StructField("congestion_surcharge", DoubleType(), True),
    StructField("Airport_fee", DoubleType(), True),
    StructField("cbd_congestion_fee", DoubleType(), True),
])

# ============================================================
# PART 1: NULL ANALYSIS
#   - select() + isNull() + sum()
#   - null % per column
# ============================================================
def part1_null_analysis(df, total_rows: int):
    null_counts_row = df.select([
        F.sum(F.col(c).isNull().cast("int")).alias(c)
        for c in df.columns
    ]).collect()[0].asDict()

    results = [
        (c, int(null_counts_row[c]), (null_counts_row[c] / total_rows) * 100.0)
        for c in df.columns
    ]

    null_report = (
        df.sparkSession.createDataFrame(results, ["column", "null_count", "null_percentage"])
          .orderBy(F.desc("null_percentage"))
    )

    any_null_cond = None
    for c in df.columns:
        any_null_cond = F.col(c).isNull() if any_null_cond is None else (any_null_cond | F.col(c).isNull())

    rows_with_any_null = df.where(any_null_cond).count()

    return null_report, rows_with_any_null, any_null_cond


# ============================================================
# PART 2: DUPLICATE ANALYSIS
#   - total rows
#   - distinct rows (all cols)
#   - duplicates by id (optional)
#   - show examples
# ============================================================
def part2_duplicate_analysis(df, total_rows: int):
    distinct_rows = df.distinct().count()
    duplicate_rows = total_rows - distinct_rows

    dup_examples_allcols = (
        df.groupBy(df.columns)
          .count()
          .where(F.col("count") > 1)
          .orderBy(F.desc("count"))
    )

    dup_examples_by_id = None
    if TRIP_ID_COL and TRIP_ID_COL in df.columns:
        dup_examples_by_id = (
            df.groupBy(TRIP_ID_COL)
              .count()
              .where(F.col("count") > 1)
              .orderBy(F.desc("count"))
        )

    return distinct_rows, duplicate_rows, dup_examples_allcols, dup_examples_by_id


# ============================================================
# PART 3: VALUE ANALYSIS
#   - compute counts in ONE aggregation pass
#   - show a few examples
# ============================================================
def part3_value_analysis(df):
    now_ts = F.current_timestamp()
    earliest_ts = F.to_timestamp(F.lit(EARLIEST_ALLOWED_DATE), TIMESTAMP_FMT)

    # Conditions
    cond_trip_distance_neg = F.col("trip_distance") < 0
    cond_fare_neg = F.col("fare_amount") < 0
    cond_total_neg = F.col("total_amount") < 0
    cond_tip_neg = F.col("tip_amount") < 0

    cond_trip_distance_zero = F.col("trip_distance") == 0
    cond_fare_zero = F.col("fare_amount") == 0
    cond_total_zero = F.col("total_amount") == 0

    cond_passenger_gt_10 = F.col("passenger_count") > 10

    cond_pickup_future = F.col("tpep_pickup_datetime") > now_ts
    cond_dropoff_future = F.col("tpep_dropoff_datetime") > now_ts
    cond_pickup_before = F.col("tpep_pickup_datetime") < earliest_ts
    cond_dropoff_before = F.col("tpep_dropoff_datetime") < earliest_ts

    cond_dropoff_before_pickup = (
        F.col("tpep_pickup_datetime").isNotNull() &
        F.col("tpep_dropoff_datetime").isNotNull() &
        (F.col("tpep_dropoff_datetime") < F.col("tpep_pickup_datetime"))
    )

    # One-pass aggregation for all checks
    agg_row = df.agg(
        F.sum(cond_trip_distance_neg.cast("int")).alias("trip_distance_negative"),
        F.sum(cond_fare_neg.cast("int")).alias("fare_amount_negative"),
        F.sum(cond_total_neg.cast("int")).alias("total_amount_negative"),
        F.sum(cond_tip_neg.cast("int")).alias("tip_amount_negative"),

        F.sum(cond_trip_distance_zero.cast("int")).alias("trip_distance_zero"),
        F.sum(cond_fare_zero.cast("int")).alias("fare_amount_zero"),
        F.sum(cond_total_zero.cast("int")).alias("total_amount_zero"),

        F.sum(cond_passenger_gt_10.cast("int")).alias("passenger_count_gt_10"),

        F.sum(cond_pickup_future.cast("int")).alias("pickup_in_future"),
        F.sum(cond_dropoff_future.cast("int")).alias("dropoff_in_future"),
        F.sum(cond_pickup_before.cast("int")).alias("pickup_before_cutoff"),
        F.sum(cond_dropoff_before.cast("int")).alias("dropoff_before_cutoff"),

        F.sum(cond_dropoff_before_pickup.cast("int")).alias("dropoff_before_pickup"),
    ).collect()[0].asDict()

    # Build a single "any invalid" condition for summary later
    any_invalid_cond = (
        cond_trip_distance_neg |
        cond_fare_neg |
        cond_total_neg |
        cond_tip_neg |
        cond_trip_distance_zero |
        cond_fare_zero |
        cond_total_zero |
        cond_passenger_gt_10 |
        cond_pickup_future |
        cond_dropoff_future |
        cond_pickup_before |
        cond_dropoff_before |
        cond_dropoff_before_pickup
    )

    return agg_row, any_invalid_cond


# ============================================================
# PART 4: SUMMARY REPORT
# ============================================================
def part4_summary(df, total_rows: int, any_null_cond, any_invalid_cond, duplicate_rows: int):
    rows_with_any_null = df.where(any_null_cond).count()
    rows_with_any_invalid = df.where(any_invalid_cond).count()
    bad_rows = df.where(any_null_cond | any_invalid_cond).count()
    clean_rows_est = total_rows - bad_rows

    print(f"Total rows: {total_rows}")
    print(f"Rows with any null: {rows_with_any_null}")
    print(f"Duplicate rows (all columns): {duplicate_rows}")
    print(f"Rows with any invalid value: {rows_with_any_invalid}")
    print(f"Bad rows (null OR invalid): {bad_rows}")
    print(f"Estimated clean rows after removing bad data: {clean_rows_est}")


def main():
    # ----------------------------------------------------
    # Create SparkSession + Read CSV
    # ----------------------------------------------------
    spark = SparkSession.builder.appName("DataQualityReport").getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")

    df = (
        spark.read
            .schema(schema)
            .option("header", True)
            .option("timestampFormat", TIMESTAMP_FMT)
            .csv(CSV_PATH)
    )

    # Cache BEFORE first action (we do many actions)
    df.cache()

    # ====================================================
    # PART 2 needs total rows first
    # ====================================================
    total_rows = df.count()

    # ====================================================
    # PART 1: NULL ANALYSIS
    # ====================================================
    print("\n" + "=" * 70)
    print("PART 1: NULL ANALYSIS")
    print("=" * 70)

    null_report, rows_with_any_null, any_null_cond = part1_null_analysis(df, total_rows)
    null_report.show(200, truncate=False)
    print(f"Rows with any NULL: {rows_with_any_null}")

    # ====================================================
    # PART 2: DUPLICATE ANALYSIS
    # ====================================================
    print("\n" + "=" * 70)
    print("PART 2: DUPLICATE ANALYSIS")
    print("=" * 70)

    distinct_rows, duplicate_rows, dup_examples_allcols, dup_examples_by_id = part2_duplicate_analysis(df, total_rows)

    print(f"Total rows: {total_rows}")
    print(f"Distinct rows (all columns): {distinct_rows}")
    print(f"Duplicate rows (all columns): {duplicate_rows}")

    print("\nTop duplicate examples (all columns):")
    dup_examples_allcols.show(10, truncate=False)

    if TRIP_ID_COL and TRIP_ID_COL in df.columns:
        print(f"\nTop duplicates by {TRIP_ID_COL}:")
        dup_examples_by_id.show(10, truncate=False)
    else:
        print("\nDuplicates on specific trip id column: SKIPPED (set TRIP_ID_COL if you have one)")

    # ====================================================
    # PART 3: VALUE ANALYSIS
    # ====================================================
    print("\n" + "=" * 70)
    print("PART 3: VALUE ANALYSIS")
    print("=" * 70)

    value_counts, any_invalid_cond = part3_value_analysis(df)
    for k in sorted(value_counts.keys()):
        print(f"{k}: {value_counts[k]}")

    # Show a few examples
    print("\nExamples: negative fare_amount")
    df.where(F.col("fare_amount") < 0).show(10, truncate=False)

    print("\nExamples: trip_distance == 0")
    df.where(F.col("trip_distance") == 0).show(10, truncate=False)

    print("\nExamples: dropoff_before_pickup")
    df.where(
        (F.col("tpep_pickup_datetime").isNotNull()) &
        (F.col("tpep_dropoff_datetime").isNotNull()) &
        (F.col("tpep_dropoff_datetime") < F.col("tpep_pickup_datetime"))
    ).show(10, truncate=False)

    # ====================================================
    # PART 4: SUMMARY REPORT
    # ====================================================
    print("\n" + "=" * 70)
    print("PART 4: SUMMARY REPORT")
    print("=" * 70)

    part4_summary(df, total_rows, any_null_cond, any_invalid_cond, duplicate_rows)

    spark.stop()


if __name__ == "__main__":
    main()