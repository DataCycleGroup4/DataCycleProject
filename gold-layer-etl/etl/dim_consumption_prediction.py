import pandas as pd, hashlib, logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table
logger = logging.getLogger(__name__)

def load_dim_consumption_prediction(client, consumption_df, run_date):
    if consumption_df.empty:
        return {}
    records = []
    for _, row in consumption_df.iterrows():
        raw = f"cpred_{run_date}_{row['time']}"
        records.append({"Cons_PredictionID": hashlib.md5(raw.encode()).hexdigest(),
            "Prediction": float(row["value_acquired"])})
    df = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimConsumptionPrediction"], df, "Cons_PredictionID")
    lookup = {}
    for i, (_, rs) in enumerate(consumption_df.iterrows()):
        if i < len(df): lookup[rs["time"]] = df.iloc[i]["Cons_PredictionID"]
    return lookup
