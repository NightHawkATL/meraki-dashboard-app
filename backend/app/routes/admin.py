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
@router.post("/users/reset", response_class=HTMLResponse)
def reset_user_password(
    username: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Resets a user's password to a generated secure string."""
    if not current_user.is_admin:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; border-radius: 4px;'>Unauthorized.</article>"

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem;'>User not found.</article>"

    import secrets
    import string
    
    settings = db.query(models.AdminSettings).first()
    min_length = settings.pwd_min_length if settings else 12
    
    # Generate password matching requirements
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    new_password = ''.join(secrets.choice(chars) for _ in range(max(12, min_length)))
    
    user.password_hash = security.get_password_hash(new_password)
    db.commit()

    return f"<article style='background-color: #1e4620; color: white; padding: 1rem; margin-bottom: 1rem;'>Password for {username} reset successfully to: <strong>{new_password}</strong> (Please copy this now, it won't be shown again)</article>"

@router.post("/policy", response_class=HTMLResponse)
def update_password_policy(
    pwd_min_length: int = Form(12),
    pwd_require_special: bool = Form(False),
    pwd_require_upper: bool = Form(False),
    pwd_require_lower: bool = Form(False),
    pwd_require_number: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    if not current_user.is_admin:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; border-radius: 4px;'>Unauthorized.</article>"

    settings = db.query(models.AdminSettings).first()
    if not settings:
        settings = models.AdminSettings()
        db.add(settings)
        
    settings.pwd_min_length = pwd_min_length
    settings.pwd_require_special = pwd_require_special
    settings.pwd_require_upper = pwd_require_upper
    settings.pwd_require_lower = pwd_require_lower
    settings.pwd_require_number = pwd_require_number
    db.commit()

    return "<article style='background-color: #1e4620; color: white; padding: 1rem; margin-bottom: 1rem;'>Password policy updated successfully.</article>"
    
@router.post("/users/search", response_class=HTMLResponse)
def search_users(
    query: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Searches for users and returns HTML list directly for HTMX"""
    if not current_user.is_admin:
        return ""
        
    if query:
        users = db.query(models.User).filter(models.User.username.contains(query)).limit(20).all()
    else:
        users = db.query(models.User).limit(20).all()
        
    if not users:
        return "<tr><td colspan='3' style='text-align:center;'>No users found.</td></tr>"
        
    html = ""
    for u in users:
        role = "Admin" if u.is_admin else "User"
        html += f"""
        <tr>
            <td style="padding: 8px;"><input type="checkbox" name="usernames" value="{u.username}" class="user-select-checkbox"></td>
            <td>{u.username}</td>
            <td>{role}</td>
            <td>
                <form hx-post="/api/admin/users/delete" hx-target="#user-alerts" hx-swap="innerHTML" hx-confirm="Are you sure you want to delete {u.username}?" style="margin: 0; padding: 0; display: inline-block;">
                    <input type="hidden" name="usernames" value="{u.username}">
                    <button type="submit" class="mui-btn" style="padding: 4px 8px; font-size: 0.8rem; background: #c62828; border: none; margin-right: 4px;">Delete</button>
                </form>
                <form hx-post="/api/admin/users/reset" hx-target="#user-alerts" hx-swap="innerHTML" style="margin: 0; padding: 0;">
                    <input type="hidden" name="username" value="{u.username}">
                    <button type="submit" class="mui-btn" style="padding: 4px 8px; font-size: 0.8rem; background: #e53935; border: none;">Reset Pwd</button>
                </form>
            </td>
        </tr>
        """
    return html
@router.post("/users/delete", response_class=HTMLResponse)
def delete_users(
    usernames: list[str] = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Deletes one or more users."""
    if not current_user.is_admin:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; border-radius: 4px;'>Unauthorized.</article>"

    # Prevent admin from deleting themselves
    if current_user.username in usernames:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem;'>You cannot delete your own account.</article>"

    users_to_delete = db.query(models.User).filter(models.User.username.in_(usernames)).all()
    
    if not users_to_delete:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem;'>No matching users found to delete.</article>"

    count = len(users_to_delete)
    for user in users_to_delete:
        # Delete dependencies first (UserOrgAccess and JobHistory)
        db.query(models.UserOrgAccess).filter(models.UserOrgAccess.user_id == user.id).delete()
        db.query(models.JobHistory).filter(models.JobHistory.user_id == user.id).delete()
        db.delete(user)
        
    db.commit()

    # Trigger a refresh of the user table by returning an out-of-band swap, plus the alert
    return f"""
    <script>document.getElementById("user-search-input").dispatchEvent(new Event("keyup"));</script>
    <article style='background-color: #1e4620; color: white; padding: 1rem; margin-bottom: 1rem;'>Successfully deleted {count} user(s).</article>
    """
