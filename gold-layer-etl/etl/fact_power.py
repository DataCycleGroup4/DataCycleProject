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

    # 1. TOTALS CALCULATION
    total_prod_eod_w = production_df["daysum"].astype(float).max()
    
    total_cons_eod_w = 0.0
    if not consumption_df.empty:
        # UPDATED: Sum of the variation column for the daily total
        # (Assuming your column name is 'variation' or 'consumption')
        variation_col = "variation" if "variation" in consumption_df.columns else "value_acquired"
        total_cons_eod_w = consumption_df[variation_col].astype(float).sum()

    # Calculate % of inverters running per time interval
    running_pct_dict = {}
    if "pac" in production_df.columns:
        running_pct_dict = production_df.groupby("time").apply(
            lambda g: (g["pac"].astype(float) > 0).sum() / len(g) * 100).to_dict()

    records = []
    for _, row in production_df.iterrows():
        t = row["time"]
        h, mi, s = (int(x) for x in t.split(":"))

        # 2. Lookups
        time_id = time_lookup.get((y, m, d, h, mi, s), "")
        inv_key = inverter_lookup.get((t, str(row["inv_id"])), "")
        err_id = error_lookup.get((t, str(row["inv_id"])), "")

        # 3. Consumption Match (Using Variation for the specific interval)
        cons_interval_val = 0.0
        cons_id = ""
        if not consumption_df.empty:
            match_cons = consumption_df[consumption_df["time"] == t]
            if not match_cons.empty:
                # We pull the variation for THIS specific timestamp
                cons_interval_val = float(match_cons.iloc[0].get(variation_col, 0))
                # Note: consumption_lookup should use the value used to create DimConsumption
                cons_id = consumption_lookup.get((t, str(cons_interval_val)), "")

        # 4. Power Balance Calculation (Watts to kW)
        prod_w = float(row.get("pac", 0))
        prod_kw = prod_w / 1000.0
        cons_kw = cons_interval_val / 1000.0
        diff_kw = prod_kw - cons_kw

        # 5. Create Fact Record
        fid = hashlib.md5(f"pf_{run_date}_{t}_{row['inv_id']}".encode()).hexdigest()
        
        records.append({
            "FactID": fid,
            "TimeID": time_id,
            "InverterKey": inv_key,
            "ConsumptionID": cons_id,
            "ErrorID": err_id,
            "Status": str(row.get("status", "Unknown")), 
            "PAC": prod_w,
            "Daysum": float(row.get("daysum", 0)),
            "PDC1": float(row.get("pdc1", 0)),
            "UDC1": float(row.get("udc1", 0)),
            "PDC2": float(row.get("pdc2", 0)), 
            "UDC2": float(row.get("udc2", 0)),
            "Prod_vs_Consumption_Diff": diff_kw,
            "Total_Production_End_of_Day": total_prod_eod_w / 1000.0,
            "Total_Consumption_End_of_day": total_cons_eod_w / 1000.0,
            "Pct_Inverters_Running": running_pct_dict.get(t, 0.0),
            "partition_date": run_date
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df["partition_date"] = pd.to_datetime(df["partition_date"]).dt.date

    return append_fact_table(client, TABLE_REF["Power_FactTable"], df, run_date)