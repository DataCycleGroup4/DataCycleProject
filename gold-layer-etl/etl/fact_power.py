import pandas as pd
import hashlib
import logging
from config import TABLE_REF
from utils.bq_writer import append_fact_table

logger = logging.getLogger(__name__)

def load_power_fact(client, production_df, consumption_df, run_date,
                    time_lookup, consumption_lookup, inverter_lookup, error_lookup):
    if production_df.empty:
        return 0
    y, m, d = (int(x) for x in run_date.split("-"))

    # Pre-calculate EOD totals and running percentages
    total_prod_eod_w = production_df["daysum"].astype(float).max()
    running = production_df.groupby("time").apply(
        lambda g: (g["pac"].astype(float) > 0).sum() / len(g)).to_dict()

    records = []
    for _, row in production_df.iterrows():
        t = row["time"]
        h, mi, s = (int(x) for x in t.split(":"))

        # 1. Standardize Lookups
        time_id = time_lookup.get((y, m, d, h, mi, s), "")
        inv_key = inverter_lookup.get((t, str(row["inv_id"])), "")
        err_id = error_lookup.get((t, str(row["inv_id"])), "")

        # Finding the consumption record for this specific time
        cons_val = 0.0
        cons_id = ""
        match_cons = consumption_df[consumption_df["time"] == t]
        if not match_cons.empty:
            cons_val = float(match_cons.iloc[0]["value_acquired"])
            cons_id = consumption_lookup.get((t, str(cons_val)), "")

        # 2. Convert Watts to kW
        prod_kw = float(row["pac"]) / 1000.0
        diff_kw = prod_kw - (cons_val / 1000.0)

        # 3. Create Fact Record
        fid = hashlib.md5(f"pf_{run_date}_{t}_{row['inv_id']}".encode()).hexdigest()

        records.append({
            "FactID": fid,
            "TimeID": time_id,
            "InverterKey": inv_key,
            "ConsumptionID": cons_id,
            "ErrorID": err_id,
            "Prod_vs_Consumption_Diff": diff_kw,
            "Total_Production_End_of_Day": total_prod_eod_w / 1000,
            "Pct_Inverters_Running": running.get(t, 0.0),
            "partition_date": run_date
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df["partition_date"] = pd.to_datetime(df["partition_date"]).dt.date

    return append_fact_table(client, TABLE_REF["Power_FactTable"], df, run_date)