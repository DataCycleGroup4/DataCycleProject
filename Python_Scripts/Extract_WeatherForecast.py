import os
import paramiko
from google.cloud import storage
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# --- SFTP Config ---
SFTP_HOST = os.environ["SFTP_HOST"]
SFTP_USER = os.environ["SFTP_USER"]
SFTP_PASS = os.environ["SFTP_PASS"]
SOURCE_FOLDERS = ["/Meteo/"]

# --- GCS Config ---
BUCKET_NAME        = os.environ["GCS_BUCKET"]
BASE_PREFIX        = "raw/weather/"
SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

def sync_sftp_to_lake():
    gcs_client = storage.Client.from_service_account_json(SERVICE_ACCOUNT_JSON)
    bucket = gcs_client.bucket(BUCKET_NAME)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SFTP_HOST, port=22, username=SFTP_USER, password=SFTP_PASS)
    sftp = ssh.open_sftp()

    try:
        # Index the whole weatherforecast folder to see what's already in there
        print(f"Indexing Data Lake: {BASE_PREFIX}...")
        existing_blobs = set(blob.name for blob in gcs_client.list_blobs(BUCKET_NAME, prefix=BASE_PREFIX))

        for folder in SOURCE_FOLDERS:
            print(f"\nChecking SFTP folder: {folder}")
            try:
                remote_files = [f for f in sftp.listdir(folder) if f.startswith("Pred_")]
                
                for filename in remote_files:
                    try:
                        # Extract month from format: Pred_YYYY-MM-DD_HHMM
                        # Split 1: ['Pred', '2026-03-04', '1200']
                        date_part = filename.split('_')[1] 
                        # Split 2: ['2026', '03', '04']
                        month = date_part.split('-')[1] 
                        
                        # Build target path: raw/weatherforecast/03/Pred_...
                        gcs_path = f"{BASE_PREFIX}{month}/{filename}"

                        if gcs_path not in existing_blobs:
                            print(f"Uploading to Month {month}: {filename}")
                            remote_full_path = f"{folder}{filename}"
                            
                            with sftp.open(remote_full_path, 'rb') as f:
                                f.prefetch()
                                blob = bucket.blob(gcs_path)
                                blob.upload_from_file(f)
                        else:
                            # Optional: uncomment to see skipped files
                            # print(f"Already exists: {filename}")
                            pass
                            
                    except IndexError:
                        print(f"Skipping {filename}: Filename format doesn't match expected date.")
            
            except IOError:
                print(f"Could not list folder {folder}")

    finally:
        sftp.close()
        ssh.close()
        print("\n--- Sync Complete ---")

if __name__ == "__main__":
    sync_sftp_to_lake()
