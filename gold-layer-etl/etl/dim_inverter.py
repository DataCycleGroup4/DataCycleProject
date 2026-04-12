import pandas as pd, hashlib, logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table
logger = logging.getLogger(__name__)

def load_dim_inverter(client, production_df, run_date):
    if production_df.empty:
        return {}
    records = []
    for _, row in production_df.iterrows():
        raw = f"inv_{run_date}_{row['time']}_{row['inv_id']}"
        records.append({"InverterKey": hashlib.md5(raw.encode()).hexdigest(),
            "InverterID": int(row["inv_id"]), "PAC": float(row["pac"]),
            "Daysum": float(row["daysum"]), "PDC1": float(row["pdc1"]),
            "PDC2": float(row["pdc2"]), "UDC1": float(row["udc1"]),
            "UDC2": float(row["udc2"]), "Status": str(row["status"])})
    df = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimInverter"], df, "InverterKey")
    lookup = {}
    for i, (_, rs) in enumerate(production_df.iterrows()):
        if i < len(df): lookup[(rs["time"], str(rs["inv_id"]))] = df.iloc[i]["InverterKey"]
    return lookup
