from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("ParquetToCSV").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

df = spark.read.parquet("/opt/spark-data/yellow_tripdata_2025-11.parquet")

out = "/tmp/yellow_tripdata_2025-11-csv"
df.write.mode("overwrite").option("header", "true").csv(out)

print(f"Wrote CSV to {out}")
spark.stop()
