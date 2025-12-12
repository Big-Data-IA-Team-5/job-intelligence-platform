"""
Cloud Function to auto-stop Composer environment at $250 budget threshold.
Cloud Run services continue running.
"""
import base64
import json
import os
from google.cloud import composer_v1
import functions_framework

@functions_framework.cloud_event
def stop_composer_on_budget(cloud_event):
    """
    Triggered by Pub/Sub message from billing budget alert.
    Stops Composer environment when budget threshold is reached.
    """
    # Decode Pub/Sub message
    pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
    budget_data = json.loads(pubsub_message)
    
    # Extract budget information
    budget_display_name = budget_data.get("budgetDisplayName", "")
    cost_amount = budget_data.get("costAmount", 0)
    budget_amount = budget_data.get("budgetAmount", 0)
    alert_threshold = budget_data.get("alertThresholdExceeded", 0)
    
    print(f"Budget Alert: {budget_display_name}")
    print(f"Cost: ${cost_amount:.2f} / ${budget_amount:.2f}")
    print(f"Threshold: {alert_threshold * 100}%")
    
    # Only stop Composer at 100% threshold
    if alert_threshold >= 1.0:
        print(f"🚨 BUDGET LIMIT REACHED! Stopping Composer environment...")
        
        try:
            # Stop Composer environment
            client = composer_v1.EnvironmentsClient()
            environment_name = "projects/job-intelligence-platform/locations/us-central1/environments/job-intel-airflow"
            
            # Delete/stop the environment
            print(f"Stopping {environment_name}...")
            operation = client.delete_environment(name=environment_name)
            
            print(f"✅ Composer environment stop initiated")
            print(f"Operation: {operation.operation.name}")
            print(f"⚠️  Cloud Run services remain running")
            
            return {"status": "composer_stopped", "cost": cost_amount}
            
        except Exception as e:
            print(f"❌ Error stopping Composer: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    else:
        print(f"ℹ️  Budget alert at {alert_threshold * 100}% - no action taken")
        return {"status": "alert_only", "threshold": alert_threshold}
