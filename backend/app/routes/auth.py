from fastapi.responses import HTMLResponse
from .. import deps
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

@router.post("/logout")
def logout(response: Response):
    """Deletes the secure cookie and redirects to the login page."""
    response.delete_cookie("access_token")
    response.headers["HX-Redirect"] = "/"
    return ""
@router.post("/password")
def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_new_password: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Changes the current user's password."""
    if not security.verify_password(current_password, current_user.password_hash):
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem;'>Current password is incorrect.</article>"
    
    if new_password != confirm_new_password:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem;'>New passwords do not match.</article>"
    
    # We should really check password requirements here, but let's implement the basic change for now
    if len(new_password) < 8:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem;'>Password must be at least 8 characters long.</article>"

    current_user.password_hash = security.get_password_hash(new_password)
    db.commit()

    return "<article style='background-color: #1e4620; color: white; padding: 1rem; margin-bottom: 1rem;'>Password changed successfully.</article>"

import pyotp
import qrcode
import io
import base64

@router.get("/2fa/setup", response_class=Response)
def setup_2fa_get(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Generates the TOTP secret and returns an inline SVG QR Code."""
    if not current_user.two_factor_secret:
        # Generate a new base32 secret
        secret = pyotp.random_base32()
        current_user.two_factor_secret = secret
        db.commit()
    else:
        secret = current_user.two_factor_secret
        
    # Build provision URI for Authenticator apps
    totp = pyotp.TOTP(secret)
    provision_uri = totp.provisioning_uri(name=current_user.username, issuer_name="Meraki Dashboard")
    
    # Generate SVG QR Code
    import qrcode.image.svg
    factory = qrcode.image.svg.SvgPathImage
    qr = qrcode.make(provision_uri, image_factory=factory)
    
    stream = io.BytesIO()
    qr.save(stream)
    svg_data = stream.getvalue().decode('utf-8')
    
    html = f"""
    <div style="text-align: center; margin-bottom: 16px;">
        {svg_data}
    </div>
    <p style="font-size: 0.85rem; color: #aaa; text-align: center; margin-bottom: 16px;">
        Scan this QR Code with Google Authenticator or Authy.
    </p>
    <form hx-post="/api/auth/2fa/verify" hx-target="#two-factor-alerts" hx-swap="innerHTML" style="max-width: 300px; margin: 0 auto;">
        <input type="text" name="token" class="mui-input" style="width: 100%; margin-bottom: 12px; text-align: center; letter-spacing: 4px;" placeholder="000000" maxlength="6" required>
        <button type="submit" class="mui-btn" style="width: 100%; background: #1976d2; border: none; color: white;">Verify & Enable 2FA</button>
    </form>
    """
    return Response(content=html, media_type="text/html")


@router.post("/2fa/verify", response_class=Response)
def verify_2fa(
    token: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Verifies a token and permanently enables 2FA for the user."""
    if not current_user.two_factor_secret:
        return Response(content="<article style='background-color: #721c24; color: white; padding: 1rem; border-radius: 4px;'>Secret not found. Please reload.</article>")
        
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if totp.verify(token):
        current_user.two_factor_enabled = True
        db.commit()
        return Response(content="""
        <article style='background-color: #1e4620; color: white; padding: 1rem; border-radius: 4px; margin-bottom: 16px;'>Two-Factor Authentication is now ENABLED.</article>
        <script>
            // Tell HTMX to swap the wrapper area back to a 'success' state or reload
            setTimeout(() => { window.location.reload(); }, 2000);
        </script>
        """)
    else:
        return Response(content="<article style='background-color: #721c24; color: white; padding: 1rem; border-radius: 4px;'>Invalid token. Please try again.</article>")


@router.post("/2fa/disable", response_class=Response)
def disable_2fa(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """Disables 2FA by removing the secret."""
    
    settings = db.query(models.AdminSettings).first()
    if settings and settings.require_2fa_all_users and not current_user.is_admin:
        return Response(content="<article style='background-color: #721c24; color: white; padding: 1rem; border-radius: 4px;'>The global policy requires 2FA to be enabled.</article>")
        
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    db.commit()
    
    return Response(content="""
    <article style='background-color: #1e4620; color: white; padding: 1rem; border-radius: 4px; margin-bottom: 16px;'>Two-Factor Authentication is now DISABLED.</article>
    <script>
        setTimeout(() => { window.location.reload(); }, 1500);
    </script>
    """)
@router.post("/ai", response_class=HTMLResponse)
def update_user_ai(
    user_ai_provider: str = Form(""), # Blank means use Global Default
    user_ai_api_key: str = Form(""),
    user_ai_custom_url: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    current_user.user_ai_provider = user_ai_provider if user_ai_provider else None
    
    if user_ai_api_key and user_ai_api_key.strip():
        current_user.user_ai_api_key = user_ai_api_key.strip()
    
    # We allow blanking out the custom URL
    current_user.user_ai_custom_url = user_ai_custom_url.strip() if user_ai_custom_url.strip() else None
        
    db.commit()

    return "<article style='background-color: #1e4620; color: white; padding: 1rem; margin-bottom: 1rem;'>Personal AI Configuration saved successfully.</article>"
