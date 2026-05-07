import os
import requests
import json
import sys
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# 1. Load the .env file
load_dotenv()

def trigger_knime_prediction():
    # 2. Get credentials from environment variables
    # These names must match exactly what you wrote in your .env file
    APP_ID = os.getenv("KNIME_ID")
    APP_PASSWORD = os.getenv("KNIME_PASSWORD")
    
    if not APP_ID or not APP_PASSWORD:
        print("Error: KNIME_ID or KNIME_PASSWORD not found in .env file.")
        return False

    # 3. Configuration
    DEPLOYMENT_URL = os.getenv("KNIME_DEPLOYMENT_URL")
    if not DEPLOYMENT_URL:
        print("Error: KNIME_DEPLOYMENT_URL not found in .env file.")
        return False
    
    headers = {
        'accept': 'application/vnd.mason+json',
        'Content-Type': 'application/json'
    }

    # 4. The Payload
    # Sending an empty dict avoids that 422 "Invalid input type STRING" error
    payload = {}

    try:
        print(f"Initializing KNIME Prediction for Deployment...")
        
        response = requests.post(
            DEPLOYMENT_URL, 
            headers=headers, 
            auth=HTTPBasicAuth(APP_ID, APP_PASSWORD),
            data=json.dumps(payload)
        )

        # 5. Check for Success
        if response.status_code in [200, 201]:
            job_data = response.json()
            print(f"Success! Workflow triggered.")
            print(f"Job ID: {job_data.get('id', 'Unknown')}")
            return True
        else:
            print(f"Execution failed. Status: {response.status_code}")
            print(f"Detail: {response.text}")
            return False

    except Exception as e:
        print(f"Connection Error: {e}")
        return False

if __name__ == "__main__":
    trigger_knime_prediction()