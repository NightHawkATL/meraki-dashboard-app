import os
import time
from datetime import datetime
from celery import Celery
from .database import SessionLocal
from . import models

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("meraki_tasks", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(task_serializer="json", accept_content=["json"], result_serializer="json", timezone="UTC", enable_utc=True)

@celery_app.task(name="run_meraki_script")
def run_meraki_script_task(job_id: int, script_id: str, org_id: str, network_id: str):
    """A background task that executes or simulates running a Meraki Python script across single or batch targets."""
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

        job.status = "Running"
        add_log("Task picked up by Celery worker...")

        # Resolve target organizations and networks based on selection
        # 1. Organization resolution
        target_orgs = []
        if org_id == "ALL_ORGS":
            access_records = db.query(models.UserOrgAccess).filter(models.UserOrgAccess.user_id == job.user_id).all()
            user_org_ids = [acc.org_id for acc in access_records]
            org_objs = db.query(models.MerakiOrganization).filter(models.MerakiOrganization.id.in_(user_org_ids)).all() if user_org_ids else db.query(models.MerakiOrganization).all()
            target_orgs = [o.id for o in org_objs]
        else:
            target_orgs = [org_id]

        add_log(f"Target scope: {len(target_orgs)} organization(s).")

        # 2. Network resolution
        target_networks = []
        if network_id == "ALL_NETWORKS":
            net_objs = db.query(models.MerakiNetwork).filter(models.MerakiNetwork.org_id.in_(target_orgs)).all()
            target_networks = [(n.org_id, n.id, n.name) for n in net_objs]
        else:
            net_obj = db.query(models.MerakiNetwork).filter(models.MerakiNetwork.id == network_id).first()
            net_name = net_obj.name if net_obj else network_id
            target_networks = [(org_id, network_id, net_name)]

        add_log(f"Resolved {len(target_networks)} target network(s) for execution.")

        # Prepare outputs directory
        output_dir = "/app/storage/outputs"
        os.makedirs(output_dir, exist_ok=True)
        timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_script_id = script_id.replace("sandbox:", "ai_").replace(":", "_").replace(".py", "")
        output_filename = f"job_{job_id}_{safe_script_id}_{timestamp_str}.log"
        output_filepath = os.path.join(output_dir, output_filename)

        output_lines = [
            f"=== Meraki Script Execution Log ===",
            f"Job ID: {job_id}",
            f"Script: {script_id}",
            f"Executed At: {datetime.utcnow().isoformat()} UTC",
            f"Target Orgs: {target_orgs}",
            f"Total Networks: {len(target_networks)}",
            "----------------------------------------"
        ]

        # Execute across targets
        for idx, (t_org, t_net, t_name) in enumerate(target_networks, start=1):
            add_log(f"[{idx}/{len(target_networks)}] Authenticating to Org ({t_org}) for Network: {t_name}...")
            output_lines.append(f"\n[{idx}/{len(target_networks)}] Target Org: {t_org} | Network: {t_name} ({t_net})")
            
            if script_id.startswith("sandbox:"):
                safe_name = script_id.split(":")[1]
                if not safe_name.endswith(".py"):
                    safe_name += ".py"
                add_log(f"Sandbox Engine: Executing {safe_name} on {t_name}...")
                try:
                    script_path = f"/app/storage/scripts/{safe_name}"
                    if os.path.exists(script_path):
                        with open(script_path, "r") as f:
                            script_code = f.read()
                        vars_dict = {
                            "network_id": t_net,
                            "org_id": t_org,
                            "network_name": t_name,
                            "output_file": output_filepath
                        }
                        exec(script_code, globals(), vars_dict)
                        output_lines.append(f"Result: Success (Sandbox script executed)")
                    else:
                        add_log(f"Warning: Sandbox script file not found at {script_path}", "warning")
                        output_lines.append(f"Result: File not found at {script_path}")
                except Exception as script_e:
                    output_lines.append(f"Result: Error - {script_e}")
                    raise Exception(f"AI Script Error on {t_name}: {script_e}")
            else:
                time.sleep(1)
                add_log(f"Executed built-in script '{script_id}' on {t_name}.", "info")
                output_lines.append(f"Result: Success (Built-in script executed)")

        # Save output file
        with open(output_filepath, "w") as out_f:
            out_f.write("\n".join(output_lines) + "\n")

        job.output_file_path = output_filepath
        job.status = "Success"
        add_log(f"Execution completed successfully! Generated output report: {output_filename}", "success")
        db.commit()

    except Exception as e:
        db.rollback()
        job.status = "Failed"
        add_log(f"Error: {str(e)}", "error")
        db.commit()
    finally:
        db.close()