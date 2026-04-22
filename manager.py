import os
import subprocess
import requests
from google.cloud import pubsub_v1
from google.oauth2 import service_account  # NEW IMPORT
import google.auth.transport.requests      # NEW IMPORT

# Settings
ROOT_DIR = r"C:\Users\Administrator\Desktop\DataCycleProject" 
PROJECT_ID = "project-d31bc18d-8d9f-48db-a77"
# PATH TO YOUR JSON KEY
KEY_PATH = r"C:\Users\Administrator\Desktop\Auth\project-d31bc18d-8d9f-48db-a77-aae985e54ca0.json"

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(PROJECT_ID, "vm-sub")

def get_access_token():
    """Generates an OAuth 2.0 Access Token for Google APIs"""
    # The crucial change: We request the 'cloud-platform' scope instead of an audience
    SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
    creds = service_account.Credentials.from_service_account_file(
        KEY_PATH, scopes=SCOPES)
    
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token

def callback(message):
    rel_path = message.attributes.get("script_path")
    
    # NEW: This fixes the slash issue regardless of how the YAML sent it
    rel_path = os.path.normpath(rel_path) 
    
    cb_url = message.attributes.get("callback_url")
    full_path = os.path.join(ROOT_DIR, rel_path)
    
    print(f"--- Starting: {rel_path} ---")
    
    try:
        # 1. Run the script
        cmd = ["powershell.exe", "-File", full_path] if full_path.endswith(".ps1") else ["py", full_path]
        subprocess.run(cmd, check=True, cwd=os.path.dirname(full_path))
        
        # 2. SUCCESS: Generate token and hit the callback
        if cb_url:
            print(f"Generating identity token for: {cb_url}")
            token = get_access_token()
            
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.post(cb_url, json={"status": "success"}, headers=headers, timeout=10)
            print(f"Cloud Callback Response: {resp.status_code}")
        
        message.ack()
        print(f"Successfully finished and ACK'd {rel_path}")

    except Exception as e:
        print(f"FAILED: {rel_path} | Error: {e}")
        message.ack() 

print(f"Monitoring {ROOT_DIR} for commands...")
streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

with subscriber:
    streaming_pull_future.result()