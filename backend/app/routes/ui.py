from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models

router = APIRouter(tags=["User Interface"])

# Point FastAPI to your new templates folder
templates = Jinja2Templates(directory="app/templates")

@router.get("/")
def render_home_or_login(request: Request, db: Session = Depends(get_db)):
    """Checks the database and serves the correct HTML page."""
    
    # Check if an admin exists
    admin_exists = db.query(models.User).filter(models.User.is_admin == True).first() is not None
    
    # Render the auth page, passing the admin_exists variable to Jinja2!
    return templates.TemplateResponse(
        "auth.html", 
        {"request": request, "admin_exists": admin_exists}
    )