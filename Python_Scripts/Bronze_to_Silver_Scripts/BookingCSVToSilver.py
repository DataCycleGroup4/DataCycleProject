import pandas as pd
import gcsfs
import csv

# 1. Configuration
SERVICE_ACCOUNT_KEY = r"C:\Users\Administrator\Desktop\Auth\project-d31bc18d-8d9f-48db-a77-aae985e54ca0.json"
BUCKET = "data-cycle-lake"
BRONZE_BASE = f"gs://{BUCKET}/raw/bellevuebooking/csv"
SILVER_BASE = f"gs://{BUCKET}/processed/cleanbellevuebooking"

french_months = {
    'janv.': 'Jan', 'févr.': 'Feb', 'mars': 'Mar', 'avr.': 'Apr',
    'mai': 'May', 'juin': 'Jun', 'juil.': 'Jul', 'août': 'Aug',
    'sept.': 'Sep', 'oct.': 'Oct', 'nov.': 'Nov', 'déc.': 'Dec'
}

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
        
        print(f"--- Processing Month {month_str} ---")

        df_list = []
        for f in files:
            full_path = f if f.startswith('gs://') else f"gs://{f}"
            with fs.open(full_path, mode='rb') as open_file:
                # FIX: Use quoting=csv.QUOTE_NONE (or 3) 
                # This tells Pandas to treat the " as a normal character so it can see the tabs (\t)
                chunk = pd.read_csv(
                    open_file, 
                    sep='\t', 
                    engine='python',
                    quoting=csv.QUOTE_NONE,
                    encoding='utf-8-sig', 
                    on_bad_lines='skip'
                )
                
                # CLEANUP: Remove the leftover " characters from column names and cell values
                chunk.columns = [c.strip().replace('"', '') for c in chunk.columns]
                chunk = chunk.apply(lambda x: x.astype(str).str.replace('"', '') if x.dtype == "object" else x)
                
                df_list.append(chunk)
        
        if not df_list:
            continue
            
        df = pd.concat(df_list, ignore_index=True)

        # 2. Rename Columns (Now that "Nom" and "Date" are clean)
        df = df.rename(columns={
            'Nom': 'room_id', #string
            'Date': 'raw_date', #date
            'Date de début': 'start_time', #time
            'Date de fin': 'end_time', #time
            'Rés.-no': 'reservation_id', #string
            'Type de réservation': 'reservation_type', #string
            'Codes': 'reservation_code', #string
            'Nom de l\'utilisateur': 'reserved_by', #string
            'Sigle de salle remplacée': 'alt_room_id', #string
            'Classe': 'class', #string
            'Activité': 'activity_type', #string
            'Professeur': 'instructor', #string
            'Division': 'department', #string
            'Poste de dépenses': 'expense_category', #string
            'Remarque': 'remarks', #string
            'Annotation': 'comments' #string
        })

        if 'raw_date' not in df.columns:
            print(f"  ! Skip: 'Date' column still not found. Headers: {df.columns.tolist()[:3]}")
            continue

        # 3. Handle Placeholders
        cols_to_fill = ['room_id', 'instructor', 'department', 'activity_type', 'reservation_type', 'reservation_code', 'reserved_by', 'alt_room_id', 'class', 'expense_category', 'remarks', 'comments']
        for col in cols_to_fill:
            if col in df.columns:
                df[col] = df[col].replace(['nan', 'None', ''], "EMPTY").fillna("EMPTY")

        # 4. Date Transformation
        df['raw_date'] = df['raw_date'].astype(str).str.strip()
        for fr, en in french_months.items():
            df['raw_date'] = df['raw_date'].str.replace(fr, en, regex=False)
        
        df['date_dt'] = pd.to_datetime(df['raw_date'], format='%d %b %Y', errors='coerce')
        
        # Placeholder for failed dates
        df['date_dt'] = df['date_dt'].fillna(pd.Timestamp('1900-01-01'))
        df['date'] = df['date_dt'].dt.date.astype(str)

        # 5. Select and Write
        cols_to_keep = ['date', 'room_id', 'start_time', 'end_time', 'reservation_id', 'reservation_type', 'reservation_code', 'reserved_by', 'alt_room_id', 'activity_type', 'instructor', 'department', 'class', 'expense_category', 'remarks', 'comments']
        existing_cols = [c for c in cols_to_keep if c in df.columns]
        final_df = df[existing_cols].copy()

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
            print(f"  + Month {month_str} processed successfully.")
            
    except Exception as e:
        print(f"  !! Fatal Error in Month {month_str}: {e}")

print("\n--- Process Complete ---")