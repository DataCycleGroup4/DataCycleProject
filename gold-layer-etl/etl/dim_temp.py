import pandas as pd, hashlib, logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table
logger = logging.getLogger(__name__)

def load_dim_temp(client, temp_df, run_date):
    if temp_df.empty:
        return {}
    records = []
    for _, row in temp_df.iterrows():
        raw = f"temp_{run_date}_{row['time']}_{row['value_acquired']}"
        records.append({"TempID": hashlib.md5(raw.encode()).hexdigest(),
            "Value": float(row["value_acquired"]), "Variation": float(row["variation"])})
    df = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimTemp"], df, "TempID")
    lookup = {}
    for i, (_, rs) in enumerate(temp_df.iterrows()):
        if i < len(df): lookup[(rs["time"], str(rs["value_acquired"]))] = df.iloc[i]["TempID"]
    return lookup
