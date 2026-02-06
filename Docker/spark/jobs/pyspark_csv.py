import time
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("CSVTest").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

t0 = time.perf_counter()

df = (spark.read
      .option("header", True)
      .option("inferSchema", True)
      .csv("/opt/spark-data/yellow_tripdata_2025-11.csv"))

# ACTION 1
df.show(10, truncate=False)

# ACTION 2 (this will scan the whole dataset)
rows = df.count()

t1 = time.perf_counter()

print("Rows:", rows)
print(f"Execution time: {t1 - t0:.2f} seconds")

spark.stop()
