import pandas as pd
import os
import gcsfs

# 1. Configuration
SERVICE_ACCOUNT_KEY = r"C:\Users\Administrator\Desktop\Auth\project-d31bc18d-8d9f-48db-a77-aae985e54ca0.json"
BUCKET = "data-cycle-lake"  
BRONZE_BASE = f"gs://{BUCKET}/raw/weather"
SILVER_BASE = f"gs://{BUCKET}/processed/cleanweather"   

# Initialize GCS
try:
    fs = gcsfs.GCSFileSystem(token=SERVICE_ACCOUNT_KEY)
    print("Authenticated successfully.")
except Exception as e:
    print(f"Auth failed: {e}")
    exit()

# 2. Processing Loop
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
            try:
                with fs.open(full_path, mode='rb') as open_file:
                    chunk = pd.read_csv(
                        open_file, 
                        sep=None, 
                        engine='python', 
                        encoding='utf-8',
                        on_bad_lines='skip'
                    )
                    if not chunk.empty:
                        df_list.append(chunk)
            except Exception as read_e:
                print(f"Skipping file {f}: {read_e}")
        
        if not df_list:
            continue
            
        df = pd.concat(df_list, ignore_index=True)

        # 3. Transform & Clean
        # Mapping by index to avoid header encoding issues
        df = df.rename(columns={
            df.columns[0]: 'time',
            df.columns[1]: 'value',
            df.columns[2]: 'prediction',
            df.columns[3]: 'site',
            df.columns[4]: 'measurement',
            df.columns[5]: 'unit'
        })

        # Fix European decimals (comma to dot) and dates
        # Note: dayfirst=True is safer for European formats
        df['time_dt'] = pd.to_datetime(df['time'], dayfirst=True, errors='coerce')
        
        for col in ['value', 'prediction']:
            if col in df.columns and df[col].dtype == 'object':
                df[col] = df[col].str.replace(',', '.', regex=False)
        
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df['prediction'] = pd.to_numeric(df['prediction'], errors='coerce')

        # Filter for quality
        # Ensure dates fall within the current month folder being processed
        mask = (df['time_dt'].notna()) & (df['value'].notna()) & (df['time_dt'].dt.month == month)
        df_cleaned = df[mask].copy()

        if df_cleaned.empty:
            print(f"Month {month_str}: No valid data after filtering.")
            continue

        # Prep Final DataFrame
        df_cleaned['date_partition'] = df_cleaned['time_dt'].dt.date.astype(str)
        # Ensure time is clean string for output
        df_cleaned['time_clean'] = df_cleaned['time'].astype(str).str.strip()
        
        # Select final columns (removed the '´' typo from 'site')
        final_df = df_cleaned[['time_clean', 'value', 'prediction', 'site', 'measurement', 'unit', 'date_partition']]

        # 4. Write to Silver with Hive Partitioning
        target_dir = f"{SILVER_BASE}/{month_str}"
        
        final_df.to_parquet(
            target_dir,
            engine='pyarrow',
            index=False,
            partition_cols=['date_partition'],
            storage_options={"token": SERVICE_ACCOUNT_KEY}
        )
        print(f"Month {month_str}: Successfully processed {len(final_df)} rows.")

    except Exception as e:
        print(f"Failed to process Month {month_str}: {e}")
        
print("\n--- Silver Layer Processing Complete ---")