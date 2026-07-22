import os
import time
from celery import Celery
from .database import SessionLocal
from . import models

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("meraki_tasks", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(task_serializer="json", accept_content=["json"], result_serializer="json", timezone="UTC", enable_utc=True)

@celery_app.task(name="run_meraki_script")
def run_meraki_script_task(job_id: int, script_id: str, org_id: str, network_id: str):
    """A background task that simulates running a Meraki Python script."""
    db = SessionLocal()
    try:
        job = db.query(models.JobHistory).filter(models.JobHistory.id == job_id).first()
        if not job:
            return

        def add_log(step: str, status: str = "info"):
            # SQLAlchemy needs us to create a new list for JSON updates to trigger saves
            current_logs = list(job.progress_log) if job.progress_log else []
            current_logs.append({"step": step, "status": status})
            job.progress_log = current_logs
            db.commit()

        # --- SIMULATE SCRIPT EXECUTION ---
        job.status = "Running"
        add_log("Task picked up by Celery worker...")
        
        time.sleep(2)
        add_log(f"Authenticating to Organization ({org_id})...")
        
        if script_id.startswith("sandbox:"):
            safe_name = script_id.split(":")[1] + ".py"
            add_log(f"Sandbox Engine: Injecting Python Context for {safe_name}...")
            time.sleep(1)
            try:
                with open(f"/app/storage/scripts/{safe_name}", "r") as f:
                    script_code = f.read()
                vars_dict = {"network_id": network_id, "org_id": org_id}
                exec(script_code, globals(), vars_dict)
            except Exception as script_e:
                raise Exception(f"AI Script Error: {script_e}")
        else:
            time.sleep(3)
        add_log(f"Executing '{script_id}' on Network ({network_id})...")
        
        time.sleep(2)
        job.status = "Success"
        add_log("Script completed successfully!", "success")

    except Exception as e:
        db.rollback()
        job.status = "Failed"
        add_log(f"Error: {str(e)}", "error")
    finally:
        db.close()