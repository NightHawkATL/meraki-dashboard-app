from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from .. import models, deps
from ..database import get_db

router = APIRouter(prefix="/api/admin", tags=["Admin Settings"])

@router.post("/mapbox", response_class=HTMLResponse)
def save_mapbox_key(
    mapbox_key: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Saves the Mapbox API key to the global Admin Settings."""
    if not current_user.is_admin:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; border-radius: 4px;'>Unauthorized.</article>"

    # Grab the single AdminSettings row (or create it if it doesn't exist)
    settings = db.query(models.AdminSettings).first()
    if not settings:
        settings = models.AdminSettings()
        db.add(settings)
    
    settings.mapbox_api_key = mapbox_key.strip()
    db.commit()
    
    return "<article style='background-color: #1e4620; color: white; padding: 1rem; margin-bottom: 1rem; border-radius: 4px;'>Mapbox API Key saved successfully.</article>"