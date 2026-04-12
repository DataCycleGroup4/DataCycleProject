import pandas as pd, hashlib, logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table
logger = logging.getLogger(__name__)

def load_dim_humidity(client, humidity_df, run_date):
    if humidity_df.empty:
        return {}
    records = []
    for _, row in humidity_df.iterrows():
        raw = f"hum_{run_date}_{row['time']}_{row['value_acquired']}"
        records.append({"HumidityID": hashlib.md5(raw.encode()).hexdigest(),
            "Value": float(row["value_acquired"]), "Variation": float(row["variation"])})
    df = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimHumidity"], df, "HumidityID")
    lookup = {}
    for i, (_, rs) in enumerate(humidity_df.iterrows()):
        if i < len(df): lookup[(rs["time"], str(rs["value_acquired"]))] = df.iloc[i]["HumidityID"]
    return lookup
