from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("UrbanFlow Test").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

df = (spark.read
      .option("header", True)
      .option("inferSchema", True)
      .parquet("/opt/spark-data/yellow_tripdata_2025_merged.parquet"))

df.show()

rows = df.count()
print(f"Total records: {rows}")