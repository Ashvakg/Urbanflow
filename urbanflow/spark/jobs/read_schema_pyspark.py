from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DecimalType, TimestampType, DoubleType
)
import time

t0 = time.perf_counter()

nyc_taxi_schema = StructType([
    StructField("VendorID", IntegerType(), False),
    StructField("tpep_pickup_datetime", TimestampType(), False),
    StructField("tpep_dropoff_datetime", TimestampType(), False),
    StructField("passenger_count", IntegerType(), True),
    StructField("trip_distance", DoubleType(), True),
    StructField("RatecodeID", IntegerType(), True),
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
])

spark = SparkSession.builder.appName("ReadSchema").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

df = (spark.read
     .schema(nyc_taxi_schema)
     .option("header",True)
     .option("timestampFormat", "yyyy-MM-dd HH:mm:ss")
     .csv("/opt/spark-data/yellow_tripdata_2025-11.csv"))

df.show(10, truncate=False)

# ACTION 2 (this will scan the whole dataset)
rows = df.count()

t1 = time.perf_counter()

print("Rows:", rows)
print(f"Execution time: {t1 - t0:.2f} seconds")

spark.stop()