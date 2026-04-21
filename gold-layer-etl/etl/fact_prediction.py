import pandas as pd, hashlib, logging
from config import TABLE_REF
from utils.bq_writer import append_fact_table

logger = logging.getLogger(__name__)

def load_prediction_fact(client, run_date, time_lookup, cons_pred_lookup,
                         prod_pred_pac_df, prod_pred_daysum_df, consumption_df):
    
    if prod_pred_pac_df.empty and prod_pred_daysum_df.empty and not cons_pred_lookup:
        return 0

    y, m, d = (int(x) for x in run_date.split("-"))
    records = []
    times_done = set()

    # Get IDs from the dimensions (matching the DDL Prod_PredictionID column)
    pac_id = prod_pred_pac_df.iloc[0]['Prod_PredictionID'] if not prod_pred_pac_df.empty else ""
    daysum_id = prod_pred_daysum_df.iloc[0]['Prod_PredictionID'] if not prod_pred_daysum_df.empty else ""
    
    # Get values for measures
    pac_val = prod_pred_pac_df.iloc[0]['pred_sum_pac'] if not prod_pred_pac_df.empty else None
    daysum_val = prod_pred_daysum_df.iloc[0]['pred_daysum'] if not prod_pred_daysum_df.empty else None

    for _, row in consumption_df.iterrows():
        t = row["time"]
        if t in times_done:
            continue
        times_done.add(t)

        h, mi, s = (int(x) for x in t.split(":"))
        time_id = time_lookup.get((y, m, d, h, mi, s), "")
        cpred_id = cons_pred_lookup.get(t, "")

        fid = hashlib.md5(f"predf_{run_date}_{t}".encode()).hexdigest()

        # EVERY KEY HERE MUST MATCH THE DDL EXACTLY
        records.append({
            "FactID": fid, 
            "TimeID": time_id,
            "Cons_PredictionID": cpred_id,
            "Prod_PredictionIDPac": pac_id,      # Exact DDL match
            "Prod_PredictionIDDaysum": daysum_id, # Exact DDL match
            "Predicted_ProductionPac": pac_val,   # Exact DDL match
            "Predicted_ProductionDaysum": daysum_val, # Exact DDL match
            "Predicted_Consumption": float(row["value_acquired"]),
            "partition_date": run_date,
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df["partition_date"] = pd.to_datetime(df["partition_date"]).dt.date
        
    return append_fact_table(client, TABLE_REF["Prediction_FactTable"], df, run_date)