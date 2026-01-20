import os
import time

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# ============================================================
# CONFIG
# ============================================================

# --- BRONZE (READ FROM S3) ---
S3_BRONZE_BUCKET = os.environ.get("S3_BRONZE_BUCKET", "")
S3_BRONZE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "nyc_taxi/yellow/2025/month=11/")

# --- SILVER (WRITE TO S3) ---
S3_SILVER_BUCKET = os.environ.get("S3_SILVER_BUCKET", "")
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver/nyc_taxi/yellow/2025-11")

# --- DLQ (WRITE TO S3) ---
S3_DLQ_BUCKET = os.environ.get("S3_DLQ_BUCKET", "")
S3_DLQ_PREFIX = os.environ.get("S3_DLQ_PREFIX", "dlq/nyc_taxi/yellow/2025-11")

# --- AWS/S3A ---
S3_REGION = os.environ.get("AWS_REGION", "eu-central-1")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")  # leave empty for AWS S3

# Small cluster friendly settings (override via env)
# NOTE: prefer fewer, larger tasks for 2 cores / 4GB
SHUFFLE_PARTITIONS = int(os.environ.get("SHUFFLE_PARTITIONS", "32"))
DEFAULT_PARALLELISM = int(os.environ.get("DEFAULT_PARALLELISM", "4"))
MAX_PARTITION_BYTES = int(os.environ.get("MAX_PARTITION_BYTES", str(128 * 1024 * 1024)))  # 128MB

# Optional knobs
SHOW_SAMPLE_ROWS = int(os.environ.get("SHOW_SAMPLE_ROWS", "0"))  # 0 disables show
COMPUTE_COUNTS = os.environ.get("COMPUTE_COUNTS", "true").lower() in ("1", "true", "yes")

# ============================================================
# DEDUP + CLEANING
# ============================================================

DEDUP_KEY_COLS = [
    "VendorID",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "PULocationID",
    "DOLocationID",
    "total_amount",
]

CRITICAL_COLS = [
    "tpep_pickup_datetime",
    "fare_amount",
    "total_amount",
    "PULocationID",
    "DOLocationID",
]

FILL_DEFAULTS = {
    "passenger_count": 1.0,
    "tip_amount": 0.0,
}

# ============================================================
# HELPERS
# ============================================================

def log(msg: str) -> None:
    print(msg, flush=True)

def any_null_condition(cols):
    cond = None
    for c in cols:
        cnd = F.col(c).isNull()
        cond = cnd if cond is None else (cond | cnd)
    return cond

def to_dlq(df_bad, error_type: str, error_message: str):
    return (
        df_bad
        .withColumn("_error_type", F.lit(error_type))
        .withColumn("_error_message", F.lit(error_message))
        .withColumn("_failed_at", F.current_timestamp())
        .withColumn("_source_file", F.input_file_name())
    )

# ============================================================
# MAIN
# ============================================================

t0 = time.time()

# IMPORTANT: set builder configs BEFORE getOrCreate() to avoid Spark 4 "CANNOT_MODIFY_CONFIG"
builder = (
    SparkSession.builder
    .config("spark.sql.shuffle.partitions", str(SHUFFLE_PARTITIONS))
    .config("spark.default.parallelism", str(DEFAULT_PARALLELISM))
    .config("spark.sql.files.maxPartitionBytes", str(MAX_PARTITION_BYTES))
    # Adaptive execution
    .config("spark.sql.adaptive.enabled", "true")
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    .config("spark.sql.adaptive.skewJoin.enabled", "true")
)

spark = builder.getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

# ---- S3A CONFIG ----
hconf = spark.sparkContext._jsc.hadoopConfiguration()
hconf.set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
hconf.set("fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain")
hconf.set("fs.s3a.endpoint.region", S3_REGION)
hconf.set("fs.s3a.fast.upload", "true")

# numeric-only values (avoid suffix parsing surprises)
hconf.set("fs.s3a.connection.timeout", "60000")
hconf.set("fs.s3a.connection.establish.timeout", "60000")
hconf.set("fs.s3a.socket.timeout", "60000")
hconf.set("fs.s3a.retry.interval", "500")
hconf.set("fs.s3a.retry.throttle.interval", "100")
hconf.set("fs.s3a.connection.ttl", "300000")
hconf.set("fs.s3a.multipart.purge.age", "86400000")
hconf.set("fs.s3a.assumed.role.session.duration", "1800000")
hconf.set("fs.s3a.threads.keepalivetime", "60")

if S3_ENDPOINT:
    hconf.set("fs.s3a.endpoint", S3_ENDPOINT)
    hconf.set("fs.s3a.path.style.access", "true")

# ---- Validate required env vars ----
if not S3_BRONZE_BUCKET:
    raise ValueError("Missing S3_BRONZE_BUCKET.")
if not S3_SILVER_BUCKET:
    raise ValueError("Missing S3_SILVER_BUCKET.")
if not S3_DLQ_BUCKET:
    raise ValueError("Missing S3_DLQ_BUCKET (needed to write DLQ).")

S3_BRONZE_INPUT = f"s3a://{S3_BRONZE_BUCKET}/{S3_BRONZE_PREFIX}".rstrip("/") + "/"
S3_SILVER_OUTPUT = f"s3a://{S3_SILVER_BUCKET}/{S3_SILVER_PREFIX}".rstrip("/") + "/"
S3_DLQ_OUTPUT = f"s3a://{S3_DLQ_BUCKET}/{S3_DLQ_PREFIX}".rstrip("/") + "/"

# ============================================================
# READ BRONZE + NORMALIZE TYPES
# ============================================================

log(f"Reading Bronze from: {S3_BRONZE_INPUT}")
df = spark.read.parquet(S3_BRONZE_INPUT)

df = (
    df
    .withColumn("tpep_pickup_datetime", F.col("tpep_pickup_datetime").cast("timestamp"))
    .withColumn("tpep_dropoff_datetime", F.col("tpep_dropoff_datetime").cast("timestamp"))
    .withColumn("passenger_count", F.col("passenger_count").cast("double"))
    .withColumn("trip_distance", F.col("trip_distance").cast("double"))
    .withColumn("RatecodeID", F.col("RatecodeID").cast("double"))
    .withColumn("fare_amount", F.col("fare_amount").cast("double"))
    .withColumn("extra", F.col("extra").cast("double"))
    .withColumn("mta_tax", F.col("mta_tax").cast("double"))
    .withColumn("tip_amount", F.col("tip_amount").cast("double"))
    .withColumn("tolls_amount", F.col("tolls_amount").cast("double"))
    .withColumn("improvement_surcharge", F.col("improvement_surcharge").cast("double"))
    .withColumn("total_amount", F.col("total_amount").cast("double"))
    .withColumn("congestion_surcharge", F.col("congestion_surcharge").cast("double"))
    .withColumn("Airport_fee", F.col("Airport_fee").cast("double"))
    .withColumn("cbd_congestion_fee", F.col("cbd_congestion_fee").cast("double"))
)

# ============================================================
# CLEANING PIPELINE (GOOD -> SILVER, BAD -> DLQ)
# ============================================================

# Dedup (wide shuffle, but keep it simple; avoid explicit repartition on tiny cluster)
df_dedup = df.dropDuplicates(DEDUP_KEY_COLS)

# Critical nulls -> DLQ
crit_null_cond = any_null_condition(CRITICAL_COLS)

df_null_critical = to_dlq(
    df_dedup.where(crit_null_cond),
    error_type="missing_critical_column",
    error_message="Null in one or more critical columns",
)

df_nonull = df_dedup.where(~crit_null_cond)

# Fill defaults (only if columns exist)
fill_cols_present = {k: v for k, v in FILL_DEFAULTS.items() if k in df_nonull.columns}
df_filled = df_nonull.fillna(fill_cols_present)
log(f"Nulls filled: {len(fill_cols_present)} columns -> {list(fill_cols_present.keys())}")

# Invalid rules
now_ts = F.current_timestamp()
invalid_cond = (
    (F.col("fare_amount") < 0) |
    (F.col("trip_distance") < 0) |
    (F.col("total_amount") < 0) |
    (F.col("tip_amount") < 0) |
    (F.col("passenger_count") <= 0) |
    (F.col("passenger_count") > 10) |
    (F.col("tpep_pickup_datetime") > now_ts) |
    (F.col("tpep_dropoff_datetime") > now_ts) |
    (
        F.col("tpep_dropoff_datetime").isNotNull() &
        (F.col("tpep_dropoff_datetime") < F.col("tpep_pickup_datetime"))
    )
)

df_invalid_rules = to_dlq(
    df_filled.where(invalid_cond),
    error_type="business_rule_failed",
    error_message="Failed validation: negative values, invalid passenger_count, or invalid timestamps",
)

df_valid = df_filled.where(~invalid_cond)

# Combine DLQ sets
df_dlq = df_null_critical.unionByName(df_invalid_rules, allowMissingColumns=True)

# Data quality score (your logic)
had_fill_nulls = F.lit(False)
if fill_cols_present:
    had_fill_nulls = any_null_condition(list(fill_cols_present.keys()))

data_quality_score = (
    F.lit(100)
    - F.when(had_fill_nulls, F.lit(10)).otherwise(F.lit(0))
    - F.when(F.col("trip_distance") == 0, F.lit(5)).otherwise(F.lit(0))
    - F.when(F.col("fare_amount") == 0, F.lit(5)).otherwise(F.lit(0))
).cast("int")

df_clean = (
    df_valid
    .withColumn("processing_timestamp", F.current_timestamp())
    .withColumn("data_quality_score", data_quality_score)
)

# ============================================================
# WRITE SILVER + DLQ
# ============================================================

log(f"Writing to SILVER: {S3_SILVER_OUTPUT}")
df_clean.write.mode("overwrite").parquet(S3_SILVER_OUTPUT)

log(f"Writing to DLQ: {S3_DLQ_OUTPUT}")
df_dlq.write.mode("overwrite").parquet(S3_DLQ_OUTPUT)

if SHOW_SAMPLE_ROWS > 0:
    log("\nSample of clean data:")
    df_clean.limit(SHOW_SAMPLE_ROWS).show(truncate=False)

# ============================================================
# SUMMARY / METRICS
# ============================================================

total_input_rows = 0
clean_rows = 0
dlq_rows = 0
failure_rate = 0.0

if COMPUTE_COUNTS:
    # Do counts from stored parquet outputs (isolates cost and avoids re-running pipeline actions)
    try:
        total_input_rows = spark.read.parquet(S3_BRONZE_INPUT).count()
        clean_rows = spark.read.parquet(S3_SILVER_OUTPUT).count()
        dlq_rows = spark.read.parquet(S3_DLQ_OUTPUT).count()
        failure_rate = (dlq_rows / total_input_rows * 100.0) if total_input_rows else 0.0
    except Exception as e:
        log(f"WARNING: Could not compute counts. Error: {e}")

duration_sec = time.time() - t0
duration_min = duration_sec / 60.0

print("\n================ PIPELINE SUMMARY ================\n")
if COMPUTE_COUNTS and total_input_rows:
    print(f"✅ Total input rows: {total_input_rows / 1_000_000:.2f} million")
    print(f"✅ Silver rows (good): {clean_rows / 1_000_000:.2f} million")
    print(f"❌ DLQ rows (bad): {dlq_rows / 1_000_000:.2f} million")
    print(f"📉 Failure rate: {failure_rate:.2f}%")
else:
    print("✅ Counts disabled or not computed (set COMPUTE_COUNTS=true to enable).")
print(f"✅ Processing time: {duration_min:.2f} minutes")
print("✅ Silver + DLQ write complete.")
print("\n==================================================\n")

spark.stop()
