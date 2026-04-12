import pandas as pd, hashlib, logging
from config import TABLE_REF
from utils.bq_writer import append_fact_table
logger = logging.getLogger(__name__)

def load_power_fact(client, production_df, consumption_df, run_date,
                    time_lookup, consumption_lookup, inverter_lookup, error_lookup):
    if production_df.empty:
        return 0
    y, m, d = (int(x) for x in run_date.split("-"))
    cons_by_time = {}
    for _, r in consumption_df.iterrows():
        cons_by_time[r["time"]] = float(r["value_acquired"])
    total_prod_eod = production_df["daysum"].astype(float).max()
    running = production_df.groupby("time").apply(
        lambda g: (g["pac"].astype(float) > 0).sum() / len(g)).to_dict()
    records = []
    for _, row in production_df.iterrows():
        t = row["time"]; h, mi, s = (int(x) for x in t.split(":"))
        time_id = time_lookup.get((y, m, d, h, mi, s), "")
        cons_id = ""
        for k, v in consumption_lookup.items():
            if k[0] == t: cons_id = v; break
        inv_key = inverter_lookup.get((t, str(row["inv_id"])), "")
        err_id = error_lookup.get((t, str(row["inv_id"])))
        diff = float(row["pac"]) - cons_by_time.get(t, 0)
        fid = hashlib.md5(f"pf_{run_date}_{t}_{row['inv_id']}".encode()).hexdigest()
        records.append({"FactID": fid, "TimeID": time_id, "ConsumptionID": cons_id,
            "InverterKey": inv_key, "ErrorID": err_id,
            "Prod_vs_Consumption_Diff": diff, "Total_Production_End_of_Day": total_prod_eod,
            "Pct_Inverters_Running": running.get(t, 0.0), "partition_date": run_date})
    df = pd.DataFrame(records)
    df["partition_date"] = pd.to_datetime(df["partition_date"]).dt.date
    return append_fact_table(client, TABLE_REF["Power_FactTable"], df, run_date)
