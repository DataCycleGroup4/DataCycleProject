import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table

logger = logging.getLogger(__name__)

def load_dim_production_prediction_daysum(client, weather_df, run_date):
    """
    Loads data into DimProductionPredictionDaysum.
    Expected columns in SQL: Prod_PredictionID, pred_date, pred_hour, pred_daysum, daysum
    """
    if weather_df.empty:
        logger.info("Weather dataframe is empty. Skipping load.")
        return pd.DataFrame()

    # Grouping by time to get average prediction
    grouped = weather_df.groupby("time").agg({"prediction": "mean"}).reset_index()
    
    records = []
    for _, row in grouped.iterrows():
        # raw string for deterministic UUID generation
        raw = f"ppred_daysum_{run_date}_{row['time']}"
        
        # Extracting hour from the 'time' column if it's a datetime object or string
        # Assuming row['time'] is something like '14:00' or a full timestamp
        try:
            hour = pd.to_datetime(row['time']).hour
        except:
            hour = 0 # Fallback

        records.append({
            "Prod_PredictionID": hashlib.md5(raw.encode()).hexdigest(),
            "pred_date": run_date,
            "pred_hour": hour,
            "pred_daysum": float(row["prediction"]),
            "daysum": 0  # Placeholder: actual production 'daysum' usually comes from Fact/Inverter data
        })

    df = pd.DataFrame(records)
    
    # Casting types to match BigQuery DDL
    df['pred_date'] = pd.to_datetime(df['pred_date']).dt.date
    
    upsert_dim_table(client, TABLE_REF["DimProductionPredictionDaysum"], df, "Prod_PredictionID")
    return df