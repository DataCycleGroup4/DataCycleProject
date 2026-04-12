import pandas as pd, hashlib, logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table
logger = logging.getLogger(__name__)

def load_dim_forecast(client, weather_df, run_date):
    if weather_df.empty:
        return {}
    records = []
    for _, row in weather_df.iterrows():
        raw = f"fc_{run_date}_{row['time']}_{row['site']}_{row['measurement']}"
        records.append({"ForecastID": hashlib.md5(raw.encode()).hexdigest(),
            "Site": str(row["site"]), "Measurement": str(row["measurement"]),
            "Value": float(row["value"]), "Prediction": float(row["prediction"]),
            "Unit": str(row["unit"])})
    df = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimForecast"], df, "ForecastID")
    lookup = {}
    for i, (_, rs) in enumerate(weather_df.iterrows()):
        if i < len(df): lookup[(rs["time"], rs["site"], rs["measurement"])] = df.iloc[i]["ForecastID"]
    return lookup
