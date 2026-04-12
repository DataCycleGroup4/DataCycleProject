import pandas as pd, hashlib, logging
from config import TABLE_REF
from utils.bq_writer import upsert_dim_table
logger = logging.getLogger(__name__)

def load_dim_errors(client, production_df, run_date):
    if production_df.empty:
        return {}
    records, seen = [], set()
    for _, row in production_df.iterrows():
        error_val = str(row.get("error", "0"))
        raw = f"err_{error_val}_{run_date}_{row['time']}_{row['inv_id']}"
        eid = hashlib.md5(raw.encode()).hexdigest()
        if eid not in seen:
            seen.add(eid)
            records.append({"ErrorID": eid, "Error_info": error_val if error_val != "0" else None})
    df = pd.DataFrame(records)
    upsert_dim_table(client, TABLE_REF["DimErrors"], df, "ErrorID")
    lookup = {}
    for _, rs in production_df.iterrows():
        raw = f"err_{str(rs.get('error','0'))}_{run_date}_{rs['time']}_{rs['inv_id']}"
        lookup[(rs["time"], str(rs["inv_id"]))] = hashlib.md5(raw.encode()).hexdigest()
    return lookup
