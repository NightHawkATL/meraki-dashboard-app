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