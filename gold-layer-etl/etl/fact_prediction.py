import pandas as pd, hashlib, logging
from config import TABLE_REF
from utils.bq_writer import append_fact_table
logger = logging.getLogger(__name__)

def load_prediction_fact(client, run_date, time_lookup, cons_pred_lookup,
                         prod_pred_df, consumption_df):
    if prod_pred_df.empty and not cons_pred_lookup:
        return 0
    y, m, d = (int(x) for x in run_date.split("-"))
    records = []
    times_done = set()
    for _, row in consumption_df.iterrows():
        t = row["time"]
        if t in times_done:
            continue
        times_done.add(t)
        h, mi, s = (int(x) for x in t.split(":"))
        time_id = time_lookup.get((y, m, d, h, mi, s), "")
        cpred_id = cons_pred_lookup.get(t, "")
        ppred_id = ""
        ppred_val = None
        for _, pr in prod_pred_df.iterrows():
            ppred_id = pr["Prod_PredictionID"]
            ppred_val = pr["Prediction"]
            break
        fid = hashlib.md5(f"predf_{run_date}_{t}".encode()).hexdigest()
        records.append({
            "FactID": fid, "TimeID": time_id,
            "Cons_PredictionID": cpred_id, "Prod_PredictionID": ppred_id,
            "Predicted_Production": ppred_val,
            "Predicted_Consumption": float(row["value_acquired"]),
            "partition_date": run_date,
        })
    df = pd.DataFrame(records)
    if not df.empty:
        df["partition_date"] = pd.to_datetime(df["partition_date"]).dt.date
    return append_fact_table(client, TABLE_REF["Prediction_FactTable"], df, run_date)
