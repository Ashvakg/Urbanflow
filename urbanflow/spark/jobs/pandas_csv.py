import pandas as pd

df = pd.read_csv("/workspaces/Urbanflow/urbanflow/spark/data/yellow_tripdata_2025-11.csv")

print(df.columns.tolist())

