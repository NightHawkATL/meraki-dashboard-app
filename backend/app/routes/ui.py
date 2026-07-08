from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from ..deps import get_current_user

router = APIRouter(tags=["User Interface"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
def render_home_or_login(request: Request, db: Session = Depends(get_db)):
    """Checks the database and serves the correct HTML page."""
    admin_exists = db.query(models.User).filter(models.User.is_admin == True).first() is not None
    return templates.TemplateResponse(
        "auth.html", 
        {"request": request, "admin_exists": admin_exists}
    )

@router.get("/dashboard")
def render_dashboard(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) 
):
    """Renders the main layout with cached networks for script execution."""
    cache = db.query(models.MerakiNetworkCache).filter(models.MerakiNetworkCache.user_id == current_user.id).all()
    unique_orgs = {item.org_id: {"id": item.org_id, "name": item.org_name} for item in cache}
    
    scripts = [
        {"id": "port_bounce", "name": "Bounce Switch Ports"},
        {"id": "vlan_update", "name": "Update Guest VLANs"},
        {"id": "device_status", "name": "Get Device Status Report"}
    ]

    settings_row = db.query(models.AdminSettings).first()
    mapbox_key = settings_row.mapbox_api_key if settings_row else ""

    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "current_user": current_user,
            "scripts": scripts,
            "orgs": list(unique_orgs.values()),
            "networks": cache,
            "mapbox_key": mapbox_key
        }
    )

@router.get("/settings")
def render_settings(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Renders the settings page with live Meraki cache data."""
    cache = db.query(models.MerakiNetworkCache).filter(models.MerakiNetworkCache.user_id == current_user.id).all()
    unique_orgs = {item.org_id: {"id": item.org_id, "name": item.org_name} for item in cache}
    
    settings_row = db.query(models.AdminSettings).first()
    mapbox_key = settings_row.mapbox_api_key if settings_row and settings_row.mapbox_api_key else ""

    return templates.TemplateResponse(
        "settings.html", 
        {
            "request": request, 
            "current_user": current_user,
            "orgs": list(unique_orgs.values()),
            "networks": cache,
            "mapbox_key": mapbox_key
        }
    )

@router.get("/history")
def render_history(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.is_admin:
        jobs = db.query(models.JobHistory).order_by(models.JobHistory.id.desc()).all()
    else:
        jobs = db.query(models.JobHistory).filter(models.JobHistory.user_id == current_user.id).order_by(models.JobHistory.id.desc()).all()

    has_running_jobs = any(job.status in ["Pending", "Running"] for job in jobs)
    
    # Grab the cache to map network IDs to Network Names!
    cache = db.query(models.MerakiNetworkCache).all()
    network_names = {item.network_id: item.network_name for item in cache}

    return templates.TemplateResponse(
        "history.html", 
        {
            "request": request, "current_user": current_user, 
            "jobs": jobs, "has_running_jobs": has_running_jobs,
            "network_names": network_names # <--- Pass it to HTML
        }
    )