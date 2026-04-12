import pandas as pd, hashlib, logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table
logger = logging.getLogger(__name__)

def load_dim_production_prediction(client, weather_df, run_date):
    if weather_df.empty:
        return pd.DataFrame()
    grouped = weather_df.groupby("time").agg({"prediction": "mean"}).reset_index()
    records = []
    for _, row in grouped.iterrows():
        raw = f"ppred_{run_date}_{row['time']}"
        records.append({"Prod_PredictionID": hashlib.md5(raw.encode()).hexdigest(),
            "Prediction": float(row["prediction"])})
    df = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimProductionPrediction"], df, "Prod_PredictionID")
    return df
