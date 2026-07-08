from fastapi import APIRouter, Depends, Form, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from .. import models, deps
from ..database import get_db
from ..tasks import run_meraki_script_task

router = APIRouter(prefix="/api/scripts", tags=["Scripts"])

@router.post("/run", response_class=HTMLResponse)
def run_script(
    response: Response,
    script_id: str = Form(...),
    org_id: str = Form(...),
    network_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Creates a job record and queues the Celery task."""
    
    # 1. Save the initial "Pending" job to the database
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

    # 2. Tell the Celery Worker to start!
    run_meraki_script_task.delay(new_job.id, script_id, org_id, network_id)

    # 3. Instantly redirect the browser to the History page so the user can watch it run
    response.headers["HX-Redirect"] = "/history"
    return ""