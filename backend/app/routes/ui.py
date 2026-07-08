from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from ..deps import get_current_user # <--- Import the security dependency

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
    # Fetch cached networks for the dropdowns
    cache = db.query(models.MerakiNetworkCache).filter(models.MerakiNetworkCache.user_id == current_user.id).all()
    unique_orgs = {item.org_id: {"id": item.org_id, "name": item.org_name} for item in cache}
    
    # Mock scripts (we will replace this with GitHub files later!)
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
            "networks": cache
        }
    )

@router.get("/settings")
def render_settings(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Renders the settings page with live Meraki cache data."""
    # Fetch cached networks for this user
    cache = db.query(models.MerakiNetworkCache).filter(models.MerakiNetworkCache.user_id == current_user.id).all()
    
    # Get unique orgs
    unique_orgs = {item.org_id: {"id": item.org_id, "name": item.org_name} for item in cache}
    
    settings_row = db.query(models.AdminSettings).first()
    mapbox_key = settings_row.mapbox_api_key if settings_row else ""
    
    return templates.TemplateResponse(
        "settings.html", 
        {
            "request": request, 
            "current_user": current_user,
            "orgs": list(unique_orgs.values()),
            "networks": cache
            "mapbox_key": mapbox_key
        }
    )