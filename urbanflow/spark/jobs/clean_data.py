import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# ============================================================
# CONFIG
# ============================================================

PARQUET_PATH = os.environ.get(
    "PARQUET_PATH",
    "/opt/spark-data/yellow_tripdata_2025-11.parquet"
)

S3_SILVER_BUCKET = os.environ.get("S3_SILVER_BUCKET", "")
S3_SILVER_PREFIX = os.environ.get("S3_SILVER_PREFIX", "silver/nyc_taxi/yellow/2025-11")

S3_REGION = os.environ.get("AWS_REGION", "eu-central-1")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")  # leave empty for AWS S3

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

CRITICAL_COLS = ["tpep_pickup_datetime", "fare_amount", "total_amount", "PULocationID", "DOLocationID"]

FILL_DEFAULTS = {
    "passenger_count": 1.0,
    "tip_amount": 0.0,
}

# ============================================================
# HELPERS
# ============================================================

def log(msg: str) -> None:
    print(msg)

def any_null_condition(cols):
    cond = None
    for c in cols:
        cnd = F.col(c).isNull()
        cond = cnd if cond is None else (cond | cnd)
    return cond

# ============================================================
# MAIN
# ============================================================

spark = SparkSession.builder.getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

# Small cluster (2 cores / 4GB total) friendly settings
spark.conf.set("spark.sql.shuffle.partitions", "8")
spark.conf.set("spark.default.parallelism", "8")
spark.conf.set("spark.sql.files.maxPartitionBytes", str(64 * 1024 * 1024))  # 64MB

# ---- S3A CONFIG ----
hconf = spark.sparkContext._jsc.hadoopConfiguration()

hconf.set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
hconf.set("fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain")
hconf.set("fs.s3a.endpoint.region", S3_REGION)
hconf.set("fs.s3a.fast.upload", "true")

# IMPORTANT: this environment has fs.s3a.* values like "24h", "5m", "500ms" which can crash
# NumberFormatException in some Hadoop/S3A builds. Force numeric-only values.
hconf.set("fs.s3a.connection.timeout", "60000")
hconf.set("fs.s3a.connection.establish.timeout", "60000")
hconf.set("fs.s3a.socket.timeout", "60000")

hconf.set("fs.s3a.retry.interval", "500")              # 500ms -> 500
hconf.set("fs.s3a.retry.throttle.interval", "100")     # 100ms -> 100
hconf.set("fs.s3a.connection.ttl", "300000")           # 5m -> 300000 ms
hconf.set("fs.s3a.multipart.purge.age", "86400000")    # 24h -> 86400000 ms
hconf.set("fs.s3a.assumed.role.session.duration", "1800000")  # 30m -> 1800000 ms (safe even if unused)

# keepalivetime is commonly seconds; force numeric seconds (avoid "60s")
hconf.set("fs.s3a.threads.keepalivetime", "60")

if S3_ENDPOINT:
    hconf.set("fs.s3a.endpoint", S3_ENDPOINT)
    hconf.set("fs.s3a.path.style.access", "true")

if not S3_SILVER_BUCKET:
    raise ValueError("Missing S3_SILVER_BUCKET. Set it in your .env and restart docker compose.")

S3_SILVER_OUTPUT = f"s3a://{S3_SILVER_BUCKET}/{S3_SILVER_PREFIX}".rstrip("/") + "/"

# ============================================================
# READ PARQUET + NORMALIZE TYPES
# ============================================================

df = spark.read.parquet(PARQUET_PATH)

# Normalize numeric/timestamp types (Spark 4 can be strict about Parquet physical types)
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

# (Optional) Keep ONE count on small clusters; comment out if you want it faster
raw_rows = df.count()
log(f"Raw data: {raw_rows} rows")

# Dedup (heavy shuffle)
df_dedup = df.repartition(8).dropDuplicates(DEDUP_KEY_COLS)

# Drop critical nulls
crit_null_cond = any_null_condition(CRITICAL_COLS)
df_nonull = df_dedup.where(~crit_null_cond)

# Fill non-critical nulls
fill_cols_present = {k: v for k, v in FILL_DEFAULTS.items() if k in df_nonull.columns}
df_filled = df_nonull.fillna(fill_cols_present)
log(f"Nulls filled: {len(fill_cols_present)} columns -> {list(fill_cols_present.keys())}")

# Business-rule validation
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

# Metadata columns
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

log("\nSample of clean data:")
df_clean.show(10, truncate=False)

clean_rows = df_clean.count()
log("\nFinal statistics:")
log(f"- Raw rows: {raw_rows}")
log(f"- Clean rows: {clean_rows}")
log(f"- Writing to SILVER: {S3_SILVER_OUTPUT}")

# Debug: show remaining fs.s3a.* configs that still have suffixes (should be none)
print("\n=== DEBUG: fs.s3a.* configs with time suffix (ms/s/m/h/d) ===")
it = hconf.iterator()
found = False
while it.hasNext():
    e = it.next()
    k = str(e.getKey())
    v = str(e.getValue())
    if k.startswith("fs.s3a.") and v.endswith(("ms", "s", "m", "h", "d")):
        found = True
        print(f"{k} = {v}")
if not found:
    print("None found ✅")

# WRITE SILVER
(
    df_clean.write
    .mode("overwrite")
    .parquet(S3_SILVER_OUTPUT)
)

log("Silver write complete.")
spark.stop()
