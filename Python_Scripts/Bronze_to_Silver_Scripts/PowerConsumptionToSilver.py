import pandas as pd
import os

# Configuration for GCS via S3-interoperability
storage_options = {
    "key": os.environ['HMAC_ACCESS_KEY'],
    "secret": os.environ['HMAC_SECRET_KEY'],
    "client_kwargs": {'endpoint_url': 'https://storage.googleapis.com'}
}

bronze_base = "s3://data-cycle-lake/raw/bellevueconso/powerconsumption"
silver_base = "s3://data-cycle-lake/processed/cleanbellevueconso/cleanpowerconsumption"

for month in range(1, 13):
    month_str = str(month).zfill(2)
    bronze_path = f"{bronze_base}/{month_str}/*.csv"
    silver_path = f"{silver_base}/{month_str}/data.parquet"

    try:
        # 1. Read Raw Data (Using glob pattern support in modern pandas/fsspec)
        df = pd.read_csv(
            bronze_path, 
            sep=';', 
            storage_options=storage_options,
            on_bad_lines='skip'
        )

        # 2. Transform & Clean (Silver Layer)
        # Convert Date
        df['date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y', errors='coerce').dt.date
        
        # Convert Time
        df['time'] = pd.to_datetime(df['Heure'], format='%H:%M:%S', errors='coerce').dt.time
        
        # Clean Unit and Cast Values
        df['unit'] = df['Unité affichage'].str.strip()
        df['value_acquired'] = pd.to_numeric(df['Valeur Acquisition'], errors='coerce')
        df['variation'] = pd.to_numeric(df['Variation'], errors='coerce')

        # Filter: Remove nulls and ensure month matches (as per your DuckDB logic)
        df = df[df['date'].notna() & df['value_acquired'].notna()]
        df = df[pd.to_datetime(df['date']).dt.month == month]

        # Select only the cleaned columns
        final_df = df[['date', 'time', 'unit', 'value_acquired', 'variation']]

        # 3. Write to Parquet
        if not final_df.empty:
            final_df.to_parquet(
                silver_path,
                storage_options=storage_options,
                engine='pyarrow',
                compression='snappy',
                index=False
            )
            print(f"Month {month_str} processed and uploaded.")
        else:
            print(f"Month {month_str} skipped (no valid data).")

    except Exception as e:
        print(f"Error processing month {month_str}: {e}")

print("Medallion Silver layer update complete.")