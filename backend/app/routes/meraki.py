from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import meraki
from .. import models, schemas, security, deps
from ..database import get_db
from fastapi import APIRouter, Depends, Form, Response

router = APIRouter(prefix="/api/meraki", tags=["Meraki Integration"])

@router.post("/key")
def save_api_key(
    api_key: str = Form(...), 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(deps.get_current_user)
):
    clean_key = api_key.strip()
    current_user.meraki_api_key_encrypted = security.encrypt_api_key(clean_key)
    db.commit()
    return "<article style='background-color: #1e4620; color: white; padding: 1rem; margin-bottom: 1rem;'>API key saved securely.</article>"

@router.post("/sync")
def sync_meraki_data(
    response: Response, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(deps.get_current_user)
):
    if not current_user.meraki_api_key_encrypted:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem;'>No API key found. Please save one first.</article>"
    
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
        
        # HTMX Magic: Tell the browser to refresh the page to show the new lists!
        response.headers["HX-Refresh"] = "true"
        return ""
    
    except Exception as e:
        return f"<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem;'>Sync Error: {str(e)}</article>"

@router.get("/cache")
def get_meraki_cache(db: Session = Depends(get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Formats and returns the cached networks for the React UI to display."""
    cache = db.query(models.MerakiNetworkCache).filter(models.MerakiNetworkCache.user_id == current_user.id).all()
    
    orgs_dict = {}
    networks_dict = {}
    
    # Group the flat database rows into Orgs and Networks for React
    for item in cache:
        if item.org_id not in orgs_dict:
            orgs_dict[item.org_id] = {"id": item.org_id, "name": item.org_name, "netCount": 0}
            networks_dict[item.org_id] = []
        
        orgs_dict[item.org_id]["netCount"] += 1
        networks_dict[item.org_id].append({"id": item.network_id, "name": item.network_name})
    
    return {
        "orgs": list(orgs_dict.values()),
        "networks": networks_dict
    }