import re
from fastapi import APIRouter, Depends, Form, Response
from sqlalchemy.orm import Session
from .. import models, security
from ..database import get_db

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/setup")
def setup_admin(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Creates the initial Admin user using HTMX Form Data."""
    
    # 1. Enforce Email Format securely on the backend
    email_regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if not re.match(email_regex, username):
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem;'>Invalid email address.</article>"

    # 2. Check if Passwords Match
    if password != confirm_password:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem;'>Passwords do not match.</article>"

    # 3. Ensure no admin already exists
    admin_exists = db.query(models.User).filter(models.User.is_admin == True).first()
    if admin_exists:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem;'>Admin already exists.</article>"
    
    # Success! Save the new admin
    hashed_password = security.get_password_hash(password)
    new_user = models.User(username=username, password_hash=hashed_password, is_admin=True)
    db.add(new_user)
    db.commit()

    settings = models.AdminSettings()
    db.add(settings)
    db.commit()

    # HTMX Magic: Tell the browser to instantly refresh the page to show the Login screen!
    response.headers["HX-Refresh"] = "true"
    return ""


@router.post("/login")
def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Authenticates a user and sets a Secure Cookie."""
    db_user = db.query(models.User).filter(models.User.username == username).first()
    
    if not db_user or not security.verify_password(password, db_user.password_hash):
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem;'>Invalid email or password.</article>"
    
    # Generate the JWT Token
    access_token = security.create_access_token(data={"sub": db_user.username})
    
    # Set the token as a Secure HTTP-Only Cookie (un-hackable by Javascript!)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True later when you have an HTTPS domain!
        max_age=security.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    # HTMX Magic: Redirect the user to the Main Dashboard
    response.headers["HX-Redirect"] = "/dashboard"
    return ""