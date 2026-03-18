import pandas as pd
import os
import gcsfs

# 1. Configuration
SERVICE_ACCOUNT_KEY = r"C:\Users\Administrator\Desktop\Auth\project-d31bc18d-8d9f-48db-a77-aae985e54ca0.json"
BUCKET = "data-cycle-lake"
BRONZE_BASE = f"gs://{BUCKET}/raw/solarlogs/production"
SILVER_BASE = f"gs://{BUCKET}/processed/cleansolarlogs/cleanproduction"

# Column names for each inverter block (11 cols per inverter)
INV_COLS = ['inv_id', 'pac', 'daysum', 'status', 'error', 'pdc1', 'pdc2', 'udc1', 'udc2', 'temp', 'uac']

# Initialize GCS
try:
    fs = gcsfs.GCSFileSystem(token=SERVICE_ACCOUNT_KEY)
    print("Authenticated successfully.")
except Exception as e:
    print(f"Auth failed: {e}")
    exit()

for month in range(1, 13):
    month_str = str(month).zfill(2)
    bronze_glob = f"{BRONZE_BASE}/{month_str}/*.csv*"

    try:
        files = fs.glob(bronze_glob)
        if not files:
            continue

        df_list = []
        for f in files:
            full_path = f if f.startswith('gs://') else f"gs://{f}"
            with fs.open(full_path, mode='rb') as open_file:
                raw = pd.read_csv(
                    open_file,
                    sep=None,
                    engine='python',
                    encoding='utf-16',
                    on_bad_lines='skip'
                )

            # Shared timestamp columns (col 0 = #Date, col 1 = Time)
            date_col = raw.iloc[:, 0]
            time_col = raw.iloc[:, 1]

            # Unpivot wide format: 5 inverter blocks starting at col 2, each 11 cols wide
            # Layout: [#Date, Time] + [INV,Pac,DaySum,Status,Error,Pdc1,Pdc2,Udc1,Udc2,Temp,Uac] * 5
            frames = []
            for i in range(5):
                start = 2 + i * 11
                block = raw.iloc[:, start:start + 11].copy()
                block.columns = INV_COLS
                block['raw_date'] = date_col.values
                block['time_str'] = time_col.values
                frames.append(block)

            df_long = pd.concat(frames, ignore_index=True)
            df_list.append(df_long)

        df = pd.concat(df_list, ignore_index=True)

        # Parse date — format is DD.MM.YY (e.g. 01.03.23)
        df['date_dt'] = pd.to_datetime(df['raw_date'], format='%d.%m.%y', errors='coerce')

        # Filter for quality: valid date, correct month
        mask = (df['date_dt'].notna()) & (df['date_dt'].dt.month == month)
        df_cleaned = df[mask].copy()

        # Prep final DataFrame
        df_cleaned['date'] = df_cleaned['date_dt'].dt.date.astype(str)
        df_cleaned['time'] = df_cleaned['time_str'].astype(str).str.strip()

        # Cast numeric columns
        for col in ['inv_id', 'pac', 'daysum', 'status', 'error', 'pdc1', 'pdc2', 'udc1', 'udc2', 'temp', 'uac']:
            df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')

        final_df = df_cleaned[['date', 'time', 'inv_id', 'pac', 'daysum', 'status', 'error',
                                'pdc1', 'pdc2', 'udc1', 'udc2', 'temp', 'uac']]

        # Sort chronologically
        final_df = final_df.sort_values(['date', 'time', 'inv_id']).reset_index(drop=True)

        # 4. Write to Silver with Hive Partitioning
        if not final_df.empty:
            target_dir = f"{SILVER_BASE}/{month_str}"
            if fs.exists(target_dir):
                # recursive=True is critical to wipe sub-folders (like date=2024-01-01)
                fs.rm(target_dir, recursive=True)
            final_df.to_parquet(
                target_dir,
                engine='pyarrow',
                index=False,
                partition_cols=['date'],
                storage_options={"token": SERVICE_ACCOUNT_KEY}
            )
            print(f"Month {month_str}: Successfully written as daily partitions.")
        else:
            print(f"Month {month_str}: No valid data.")

    except Exception as e:
        print(f"Error in Month {month_str}: {e}")

print("\n--- Silver Layer Complete ---")