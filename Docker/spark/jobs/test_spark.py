from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("UrbanFlow Test").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

# Sample in-memory data
data = [
    {"trip_id": 1, "fare": 8.5,  "passenger_count": 1},
    {"trip_id": 2, "fare": 12.0, "passenger_count": 2},
    {"trip_id": 3, "fare": 25.3, "passenger_count": 1},
    {"trip_id": 4, "fare": 6.0,  "passenger_count": 3},
]

# Create DataFrame
df = spark.createDataFrame(data)

print("=== Original Data ===")
df.show()

# Filter fares > 10
filtered_df = df.filter("fare > 10")

print("=== Filtered Data (fare > 10) ===")
filtered_df.show()

# Count rows
total = df.count()
print(f"Total records: {total}")

print("Test successful!")

spark.stop()
