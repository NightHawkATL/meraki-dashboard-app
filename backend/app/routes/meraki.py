from fastapi import APIRouter, Depends, Form, Response
from fastapi.responses import HTMLResponse # <--- NEW IMPORT
from sqlalchemy.orm import Session
import meraki
from .. import models, security, deps
from ..database import get_db

router = APIRouter(prefix="/api/meraki", tags=["Meraki Integration"])

# Notice we added response_class=HTMLResponse here!
@router.post("/key", response_class=HTMLResponse)
def save_api_key(
    api_key: str = Form(...), 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(deps.get_current_user)
):
    """Encrypts and saves the Meraki API key to the user's profile."""
    # Aggressively clean the key (removes spaces, newlines, and accidental quotes)
    clean_key = api_key.strip().strip('"').strip("'")
    
    current_user.meraki_api_key_encrypted = security.encrypt_api_key(clean_key)
    db.commit()
    
    return "<article style='background-color: #1e4620; color: white; padding: 1rem; margin-bottom: 1rem; border-radius: 4px;'>API key saved securely.</article>"

@router.post("/sync", response_class=HTMLResponse)
def sync_meraki_data(
    response: Response, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(deps.get_current_user)
):
    """Logs into Meraki, fetches Orgs and Networks, and caches them."""
    if not current_user.meraki_api_key_encrypted:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem; border-radius: 4px;'>No API key found. Please save one first.</article>"
    
    api_key = security.decrypt_api_key(current_user.meraki_api_key_encrypted)
    
    try:
        dashboard = meraki.DashboardAPI(api_key=api_key, print_console=False, suppress_logging=True)
        orgs = dashboard.organizations.getOrganizations()
        
        db.query(models.MerakiNetworkCache).filter(models.MerakiNetworkCache.user_id == current_user.id).delete()
        new_cache_entries = []
        
        for org in orgs:
            try:
                networks = dashboard.organizations.getOrganizationNetworks(org['id'])
                for net in networks:
                    new_cache_entries.append(models.MerakiNetworkCache(
                        user_id=current_user.id, org_id=org['id'], org_name=org['name'], 
                        network_id=net['id'], network_name=net['name']
                    ))
            except meraki.APIError:
                continue
        
        if new_cache_entries:
            db.bulk_save_objects(new_cache_entries)
        db.commit()
        
        response.headers["HX-Refresh"] = "true"
        return ""
    
    except Exception as e:
        return f"<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem; border-radius: 4px;'>Sync Error: {str(e)}</article>"