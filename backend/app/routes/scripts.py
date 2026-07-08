from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .. import models, deps
from ..database import get_db
from ..tasks import run_meraki_script_task

router = APIRouter(prefix="/api/scripts", tags=["Scripts"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/run", response_class=HTMLResponse)
def run_script(
    request: Request,
    script_id: str = Form(...),
    org_id: str = Form(...),
    network_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Creates a job record, triggers Celery, and returns the live progress terminal."""
    new_job = models.JobHistory(
        user_id=current_user.id,
        script_name=script_id,
        target_network_id=network_id,
        status="Pending",
        progress_log=[{"step": "Job queued. Waiting for worker...", "status": "info"}]
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Queue the Celery task!
    run_meraki_script_task.delay(new_job.id, script_id, org_id, network_id)

    # Return the progress box HTML!
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
    
    # Look up the org_id from the cache since the job only stores network_id
    cache_entry = db.query(models.MerakiNetworkCache).filter(models.MerakiNetworkCache.network_id == old_job.target_network_id).first()
    org_id = cache_entry.org_id if cache_entry else "unknown"

    # Create a fresh job identical to the old one
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