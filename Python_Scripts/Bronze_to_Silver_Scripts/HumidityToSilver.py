import pandas as pd
import os
import gcsfs

# 1. Configuration
SERVICE_ACCOUNT_KEY = r"C:\Users\Administrator\Desktop\Auth\project-d31bc18d-8d9f-48db-a77-aae985e54ca0.json"
BUCKET = "data-cycle-lake"
BRONZE_BASE = f"gs://{BUCKET}/raw/bellevueconso/humidity"
SILVER_BASE = f"gs://{BUCKET}/processed/cleanbellevueconso/cleanhumidity"

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
                chunk = pd.read_csv(
                    open_file,
                    sep=None,
                    engine='python',
                    encoding='utf-16',
                    on_bad_lines='skip'
                )
                df_list.append(chunk)

        df = pd.concat(df_list, ignore_index=True)

        # 3. Transform & Clean
        # Renaming by position to handle weird encoding characters in headers
        df = df.rename(columns={
            df.columns[0]: 'raw_date',
            df.columns[1]: 'time_str',
            df.columns[2]: 'unit',
            df.columns[3]: 'val_raw',
            df.columns[4]: 'var_raw'
        })

        # Fix European decimals (comma to dot) and dates
        df['date_dt'] = pd.to_datetime(df['raw_date'], format='%d.%m.%Y', errors='coerce')
        for col in ['val_raw', 'var_raw']:
            if df[col].dtype == 'object':
                df[col] = df[col].str.replace(',', '.', regex=False)

        df['value_acquired'] = pd.to_numeric(df['val_raw'], errors='coerce')
        df['variation'] = pd.to_numeric(df['var_raw'], errors='coerce')

        # Filter for quality
        mask = (df['date_dt'].notna()) & (df['value_acquired'].notna()) & (df['date_dt'].dt.month == month)
        df_cleaned = df[mask].copy()

        # Prep Final DataFrame
        df_cleaned['date'] = df_cleaned['date_dt'].dt.date.astype(str)  # String format for partitioning
        df_cleaned['time'] = df_cleaned['time_str'].astype(str).str.strip()
        final_df = df_cleaned[['date', 'time', 'unit', 'value_acquired', 'variation']]

        # 4. Write to Silver with Hive Partitioning
        if not final_df.empty:
            target_dir = f"{SILVER_BASE}/{month_str}"

            # Using partition_cols creates daily subfolders
            # storage_options is required here for the pyarrow engine
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
