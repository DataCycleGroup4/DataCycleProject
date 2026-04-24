import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table

logger = logging.getLogger(__name__)

def load_dim_errors(client, production_df, run_date):
    if production_df.empty:
        return {}

    # SAFETY NET: If the 'error' column is entirely missing from the Silver file, create it
    if "error" not in production_df.columns:
        production_df["error"] = "0"

    # 1. Deduplicate to get only unique error messages/codes
    error_series = production_df["error"].astype(str).unique()

    records = []
    for error_val in error_series:
        eid = hashlib.md5(f"err_{error_val}".encode()).hexdigest()
        
        records.append({
            "ErrorID": eid,
            "Error_info": error_val if error_val not in ["0", "None", "nan"] else "No Error"
        })

    df_to_load = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimErrors"], df_to_load, "ErrorID")

    # 2. Build the Lookup dictionary for fact_power.py
    lookup = {}
    for _, row in production_df.iterrows():
        error_val = str(row.get("error", "0"))
        eid = hashlib.md5(f"err_{error_val}".encode()).hexdigest()
        lookup[(row["time"], str(row["inv_id"]))] = eid

    return lookup