import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table

logger = logging.getLogger(__name__)

def load_dim_production_prediction_pac(client, weather_df, run_date):
    """
    Loads data into DimProductionPredictionPac.
    Expected columns in SQL: Prod_PredictionID, pred_date, pred_hour, pred_sum_pac, sum_pac
    """
    if weather_df.empty:
        logger.info("Weather dataframe is empty. Skipping load.")
        return pd.DataFrame()

    grouped = weather_df.groupby("time").agg({"prediction": "mean"}).reset_index()
    
    records = []
    for _, row in grouped.iterrows():
        raw = f"ppred_pac_{run_date}_{row['time']}"
        
        try:
            hour = pd.to_datetime(row['time']).hour
        except:
            hour = 0

        records.append({
            "Prod_PredictionID": hashlib.md5(raw.encode()).hexdigest(),
            "pred_date": run_date,
            "pred_hour": hour,
            "pred_sum_pac": float(row["prediction"]),
            "sum_pac": 0  # Placeholder: actual sum_pac would be aggregated from DimInverter/Fact
        })

    df = pd.DataFrame(records)
    
    # Ensure date objects are used for BQ DATE type
    df['pred_date'] = pd.to_datetime(df['pred_date']).dt.date
    
    upsert_dim_table(client, TABLE_REF["DimProductionPredictionPac"], df, "Prod_PredictionID")
    return df