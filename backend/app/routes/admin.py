import urllib.request
import urllib.error
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
    """Verifies and saves the Mapbox API key to the global Admin Settings."""
    if not current_user.is_admin:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; border-radius: 4px;'>Unauthorized.</article>"

    # Strip any accidental spaces
    clean_key = mapbox_key.strip()

    # --- VERIFY KEY WITH MAPBOX ---
    if clean_key:
        try:
            # We make a tiny request to the Mapbox Styles API to see if they accept the token
            verify_url = f"https://api.mapbox.com/styles/v1/mapbox/dark-v11?access_token={clean_key}"
            req = urllib.request.Request(verify_url, method="GET")
            
            # If this succeeds, the key is 100% valid!
            with urllib.request.urlopen(req) as response:
                pass 
                
        except urllib.error.HTTPError as e:
            # If Mapbox throws a 401 Unauthorized, we catch it and warn the user
            return f"<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem; border-radius: 4px;'>Invalid Mapbox Key: Mapbox rejected this token.</article>"
        except Exception as e:
            return f"<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem; border-radius: 4px;'>Error verifying Mapbox Key: {str(e)}</article>"

    # --- SAVE TO DATABASE ---
    settings = db.query(models.AdminSettings).first()
    if not settings:
        settings = models.AdminSettings()
        db.add(settings)
    
    settings.mapbox_api_key = clean_key
    db.commit()
    
    return "<article style='background-color: #1e4620; color: white; padding: 1rem; margin-bottom: 1rem; border-radius: 4px;'>Mapbox API Key verified and saved successfully!</article>"