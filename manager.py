import os
import subprocess
import requests
from google.cloud import pubsub_v1

# Update these two!
ROOT_DIR = r"C:\Users\Administrator\Desktop\DataCycleProject" 
PROJECT_ID = "project-d31bc18d-8d9f-48db-a77"

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(PROJECT_ID, "vm-sub")

def callback(message):
    rel_path = message.attributes.get("script_path")
    cb_url = message.attributes.get("callback_url")
    full_path = os.path.join(ROOT_DIR, rel_path)
    
    print(f"--- Starting: {rel_path} ---")
    
    try:
        # Determine execution type
        if full_path.endswith(".ps1"):
            cmd = ["powershell.exe", "-File", full_path]
        else:
            cmd = ["py", full_path]

        # Run script and wait for it to finish
        subprocess.run(cmd, check=True, cwd=os.path.dirname(full_path))
        
        # SUCCESS: Tell Google to move to the next step
        if cb_url:
            requests.post(cb_url, json={"status": "success"})
        
        print(f"Successfully finished {rel_path}")
        message.ack()

    except Exception as e:
        print(f"FAILED: {rel_path} | Error: {e}")
        # We don't hit the callback here so the Workflow will 
        # eventually time out and show as a Failure in the Console.

print(f"Monitoring {ROOT_DIR} for commands...")
streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

with subscriber:
    streaming_pull_future.result()