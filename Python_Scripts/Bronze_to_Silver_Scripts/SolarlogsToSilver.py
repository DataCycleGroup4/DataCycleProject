import pandas as pd
import os

storage_options = {
    "key": os.environ['HMAC_ACCESS_KEY'],
    "secret": os.environ['HMAC_SECRET_KEY'],
    "client_kwargs": {'endpoint_url': 'https://storage.googleapis.com'}
}

bronze_base = "s3://data-cycle-lake/raw/solarlogs"
silver_base_history = "s3://data-cycle-lake/processed/cleansolarlogs/cleanproductionhistory"
silver_base_production = "s3://data-cycle-lake/processed/cleansolarlogs/cleanproduction"



for month in range(1, 13):
    month_str = str(month).zfill(2)
    bronze_path = f"{bronze_base}/{month_str}/*.csv"
    silver_path = f"{silver_base_history}/{month_str}/data.parquet"

    #code for historical data

    try:

        df = pd.read_csv(
            bronze_path,
            sep=';',
            storage_options=storage_options,
            on_bad_lines='skip'
        )

        #convert date
        df['date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y', errors='coerce').dt.date

        #convert time
        df['time'] = pd.to_datetime(df['Heure'], format='%H:%M%S', errors='coerce').dt.date

        # clean unit and cast values
        df['unit'] = df['Unité affichage'].str.strip()
        df['value_acquired'] = pd.to_numeric(df['Valeur Acquisition'], errors='coerce')
        df['variation'] = pd.to_numeric(df['Variation'], errors='coerce')

        df = df[df['date'].notna() & df['value_acquired'].notna()]
        df = df[pd.to_datetime(df['date']).dt.month == month]

        final_df = df[['date', 'time', 'value_acquired', 'variation']]

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
print(f"Moving solar panel production history to silver layer is done yo")

    #code for current data COMING SOON TO A THEATRE NEAR YOU
