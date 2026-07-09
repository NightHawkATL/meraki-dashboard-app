from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import meraki
from .. import models, deps, security
from ..database import get_db
from ..tasks import run_meraki_script_task

router = APIRouter(prefix="/api/scripts", tags=["Scripts"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/build-form", response_class=HTMLResponse)
def build_dynamic_form(
    request: Request,
    script_id: str,
    network_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Evaluates the script requirements and returns dynamic HTML inputs."""
    template_data = {"request": request, "script_id": script_id}
    
    # 1. BOUNCE PORT SCRIPT: Requires fetching live switches from Meraki!
    if script_id == "port_bounce":
        api_key = security.decrypt_api_key(current_user.meraki_api_key_encrypted)
        try:
            dashboard = meraki.DashboardAPI(api_key=api_key, print_console=False, suppress_logging=True)
            devices = dashboard.networks.getNetworkDevices(network_id)
            # Filter the devices so only Switches (Models starting with "MS") appear in the dropdown
            template_data["switches"] = [d for d in devices if d.get("model", "").startswith("MS")]
        except Exception:
            template_data["switches"] = []
            
    # Return the rendered form fields
    return templates.TemplateResponse("script_form.html", template_data)


@router.post("/run", response_class=HTMLResponse)
async def run_script(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Creates a job record with dynamic variables and triggers Celery."""
    # We use await request.form() so we can capture ANY dynamic variables submitted!
    form_data = await request.form()
    
    script_id = form_data.get("script_id")
    org_id = form_data.get("org_id")
    network_id = form_data.get("network_id")
    
    # Extract only the dynamic variables by ignoring the standard IDs
    dynamic_vars = {key: val for key, val in form_data.items() if key not in ["script_id", "org_id", "network_id"]}
    
    # Format a nice log message showing what variables we captured
    log_msg = f"Job queued with parameters: {dynamic_vars}" if dynamic_vars else "Job queued. Waiting for worker..."

    new_job = models.JobHistory(
        user_id=current_user.id,
        script_name=script_id,
        target_network_id=network_id,
        status="Pending",
        progress_log=[{"step": log_msg, "status": "info"}]
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Queue the Celery task
    run_meraki_script_task.delay(new_job.id, script_id, org_id, network_id)

    return templates.TemplateResponse("progress.html", {"request": request, "job": new_job})


@router.get("/progress/{job_id}", response_class=HTMLResponse)
def get_progress(job_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(deps.get_current_user)):
    """An endpoint HTMX polls every second to update the terminal."""
    job = db.query(models.JobHistory).filter(models.JobHistory.id == job_id).first()
    return templates.TemplateResponse("progress.html", {"request": request, "job": job})


@router.post("/retry/{job_id}", response_class=HTMLResponse)
def retry_job(job_id: int, response: Response, db: Session = Depends(get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Duplicates a failed job and runs it again."""
    old_job = db.query(models.JobHistory).filter(models.JobHistory.id == job_id).first()
    net_entry = db.query(models.MerakiNetwork).filter(models.MerakiNetwork.id == old_job.target_network_id).first()
    org_id = net_entry.org_id if net_entry else "unknown"

    new_job = models.JobHistory(
        user_id=current_user.id, script_name=old_job.script_name,
        target_network_id=old_job.target_network_id, status="Pending",
        progress_log=[{"step": "Retry queued. Waiting for worker...", "status": "info"}]
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    run_meraki_script_task.delay(new_job.id, old_job.script_name, org_id, old_job.target_network_id)
    response.headers["HX-Refresh"] = "true"
    return ""