import urllib.request
import urllib.error
import re
from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from .. import models, deps, security
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

    clean_key = mapbox_key.strip()
    if clean_key:
        try:
            verify_url = f"https://api.mapbox.com/styles/v1/mapbox/dark-v11?access_token={clean_key}"
            req = urllib.request.Request(verify_url, method="GET")
            with urllib.request.urlopen(req) as response:
                pass 
        except urllib.error.HTTPError as e:
            return f"<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem; border-radius: 4px;'>Invalid Mapbox Key: Mapbox rejected this token.</article>"
        except Exception as e:
            return f"<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem; border-radius: 4px;'>Error verifying Mapbox Key: {str(e)}</article>"

    settings = db.query(models.AdminSettings).first()
    if not settings:
        settings = models.AdminSettings()
        db.add(settings)
    
    settings.mapbox_api_key = clean_key
    db.commit()
    
    return "<article style='background-color: #1e4620; color: white; padding: 1rem; margin-bottom: 1rem; border-radius: 4px;'>Mapbox API Key verified and saved successfully!</article>"

@router.post("/users", response_class=HTMLResponse)
def create_user(
    username: str = Form(...),
    password: str = Form(...),
    is_admin: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Creates a new user (Admin only)"""
    if not current_user.is_admin:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; border-radius: 4px;'>Unauthorized.</article>"

    email_regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if not re.match(email_regex, username):
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem;'>Invalid email address format.</article>"

    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem;'>User already exists.</article>"

    hashed_password = security.get_password_hash(password)
    new_user = models.User(username=username, password_hash=hashed_password, is_admin=is_admin)
    db.add(new_user)
    db.commit()

    return f"<article style='background-color: #1e4620; color: white; padding: 1rem; margin-bottom: 1rem;'>User {username} created successfully!</article>"
