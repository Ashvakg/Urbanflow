import os
import time

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark import StorageLevel

# ============================================================
# CONFIG
# ============================================================

# --- BRONZE (READ FROM S3) ---
S3_BRONZE_BUCKET = os.environ.get("S3_BRONZE_BUCKET", "")
S3_BRONZE_PREFIX = os.environ.get("S3_BRONZE_PREFIX", "nyc_taxi/yellow/2025/month=11/")

# --- SILVER (WRITE TO S3) ---
S3_SILVER_BUCKET = os.environ.get("S3_SILVER_BUCKET", "")
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver/nyc_taxi/yellow/2025-11")

# --- AWS/S3A ---
S3_REGION = os.environ.get("AWS_REGION", "eu-central-1")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")  # leave empty for AWS S3

# Small cluster friendly settings (override via env)
SHUFFLE_PARTITIONS = int(os.environ.get("SHUFFLE_PARTITIONS", "64"))
DEFAULT_PARALLELISM = int(os.environ.get("DEFAULT_PARALLELISM", "64"))
MAX_PARTITION_BYTES = int(os.environ.get("MAX_PARTITION_BYTES", str(64 * 1024 * 1024)))  # 64MB

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

# ============================================================
# MAIN
# ============================================================

t0 = time.time()

spark = SparkSession.builder.getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

# Spark execution tuning for small clusters
spark.conf.set("spark.sql.shuffle.partitions", str(SHUFFLE_PARTITIONS))
spark.conf.set("spark.default.parallelism", str(DEFAULT_PARALLELISM))
spark.conf.set("spark.sql.files.maxPartitionBytes", str(MAX_PARTITION_BYTES))

# Adaptive execution (helps with partition coalescing/skew)
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")

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

S3_BRONZE_INPUT = f"s3a://{S3_BRONZE_BUCKET}/{S3_BRONZE_PREFIX}".rstrip("/") + "/"
S3_SILVER_OUTPUT = f"s3a://{S3_SILVER_BUCKET}/{S3_SILVER_PREFIX}".rstrip("/") + "/"

# ============================================================
# READ BRONZE + NORMALIZE TYPES
# ============================================================

log(f"Reading Bronze from: {S3_BRONZE_INPUT}")
df = spark.read.parquet(S3_BRONZE_INPUT)

# Normalize numeric/timestamp types
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
# CLEANING PIPELINE
# ============================================================

# Dedup: repartition by keys to reduce skew / giant partitions
df_dedup = (
    df
    .repartition(SHUFFLE_PARTITIONS, *[F.col(c) for c in DEDUP_KEY_COLS])
    .dropDuplicates(DEDUP_KEY_COLS)
)

# Remove rows with nulls in critical columns
crit_null_cond = any_null_condition(CRITICAL_COLS)
df_nonull = df_dedup.where(~crit_null_cond)

# Fill defaults (only if columns exist)
fill_cols_present = {k: v for k, v in FILL_DEFAULTS.items() if k in df_nonull.columns}
df_filled = df_nonull.fillna(fill_cols_present)
log(f"Nulls filled: {len(fill_cols_present)} columns -> {list(fill_cols_present.keys())}")

# Filter invalid rows
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
df_valid = df_filled.where(~invalid_cond)

# Data quality score
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
# MATERIALIZE ONCE (avoid re-running lineage 3-4 times)
# ============================================================

df_clean.persist(StorageLevel.DISK_ONLY)

# Trigger materialization early (cheaper than multiple actions later)
# This is the safest pattern on small clusters.
clean_rows = df_clean.count()

log("\nSample of clean data:")
df_clean.limit(10).show(truncate=False)

log("\nFinal statistics:")
log(f"- Clean rows: {clean_rows:,}")
log(f"- Writing to SILVER: {S3_SILVER_OUTPUT}")

# ============================================================
# WRITE SILVER
# ============================================================

(
    df_clean.write
    .mode("overwrite")
    .parquet(S3_SILVER_OUTPUT)
)

df_clean.unpersist()

# ============================================================
# SUMMARY
# ============================================================

duration_sec = time.time() - t0
duration_min = duration_sec / 60.0

print("\n================ PIPELINE SUMMARY ================\n")
print(f"✅ Total rows (clean): {clean_rows / 1_000_000:.2f} million")
print(f"✅ Processing time: {duration_min:.2f} minutes")
print("✅ Silver write complete.")
print("\n==================================================\n")

spark.stop()
