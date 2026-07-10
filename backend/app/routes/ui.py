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
    return templates.TemplateResponse("auth.html", {"request": request, "admin_exists": admin_exists})

@router.get("/dashboard")
def render_dashboard(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user) 
):
    """Renders the main layout with cached networks for script execution."""
    
    # 1. Find all Orgs this user is allowed to see
    access_records = db.query(models.UserOrgAccess).filter(models.UserOrgAccess.user_id == current_user.id).all()
    org_ids = [acc.org_id for acc in access_records]
    
    # 2. Query the Global Tables for those specific Orgs and Networks
    orgs = db.query(models.MerakiOrganization).filter(models.MerakiOrganization.id.in_(org_ids)).all()
    networks = db.query(models.MerakiNetwork).filter(models.MerakiNetwork.org_id.in_(org_ids)).all()

    # 3. Map them to dictionaries so our HTML templates still work perfectly
    unique_orgs = {org.id: {"id": org.id, "name": org.name} for org in orgs}
    mapped_networks = [{"network_id": net.id, "org_id": net.org_id, "network_name": net.name} for net in networks]
    
    scripts = [
        {"id": "port_bounce", "name": "Bounce Switch Ports"},
        {"id": "vlan_update", "name": "Update Guest VLANs"},
        {"id": "device_status", "name": "Get Device Status Report"}
    ]

    all_users = []
    if current_user.is_admin:
        all_users = db.query(models.User).limit(20).all()
    settings_row = db.query(models.AdminSettings).first()
    mapbox_key = settings_row.mapbox_api_key if settings_row and settings_row.mapbox_api_key else ""

    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "current_user": current_user,
            "scripts": scripts,
            "orgs": list(unique_orgs.values()),
            "networks": mapped_networks,   # <--- FIX: Using mapped_networks instead of cache!
            "mapbox_key": mapbox_key,
            "admin_settings": settings_row,
            "all_users": all_users
        }
    )

@router.get("/settings")
def render_settings(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Renders the settings page with live Meraki cache data."""
    
    # Same Global Inventory fetch for Settings!
    access_records = db.query(models.UserOrgAccess).filter(models.UserOrgAccess.user_id == current_user.id).all()
    org_ids = [acc.org_id for acc in access_records]
    
    orgs = db.query(models.MerakiOrganization).filter(models.MerakiOrganization.id.in_(org_ids)).all()
    networks = db.query(models.MerakiNetwork).filter(models.MerakiNetwork.org_id.in_(org_ids)).all()

    unique_orgs = {org.id: {"id": org.id, "name": org.name} for org in orgs}
    mapped_networks = [{"network_id": net.id, "org_id": net.org_id, "network_name": net.name} for net in networks]
    
    all_users = []
    if current_user.is_admin:
        all_users = db.query(models.User).limit(20).all()
    settings_row = db.query(models.AdminSettings).first()
    mapbox_key = settings_row.mapbox_api_key if settings_row and settings_row.mapbox_api_key else ""

    return templates.TemplateResponse(
        "settings.html", 
        {
            "request": request, 
            "current_user": current_user,
            "orgs": list(unique_orgs.values()),
            "networks": mapped_networks,   # <--- FIX: Using mapped_networks instead of cache!
            "mapbox_key": mapbox_key,
            "admin_settings": settings_row,
            "all_users": all_users
        }
    )

@router.get("/history")
def render_history(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Renders the Recent History page."""
    if current_user.is_admin:
        jobs = db.query(models.JobHistory).order_by(models.JobHistory.id.desc()).all()
    else:
        jobs = db.query(models.JobHistory).filter(models.JobHistory.user_id == current_user.id).order_by(models.JobHistory.id.desc()).all()

    has_running_jobs = any(job.status in ["Pending", "Running"] for job in jobs)
    
    # Grab the Global Networks table to map Network IDs to Network Names!
    all_networks = db.query(models.MerakiNetwork).all()
    network_names = {net.id: net.name for net in all_networks}

    return templates.TemplateResponse(
        "history.html", 
        {
            "request": request, 
            "current_user": current_user, 
            "jobs": jobs, 
            "has_running_jobs": has_running_jobs,
            "network_names": network_names 
        }
    )