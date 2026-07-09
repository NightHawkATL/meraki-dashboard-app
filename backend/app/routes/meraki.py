from fastapi import APIRouter, Depends, Form, Response, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import meraki
from .. import models, security, deps
from ..database import get_db

router = APIRouter(prefix="/api/meraki", tags=["Meraki Integration"])

@router.post("/key", response_class=HTMLResponse)
def save_api_key(
    api_key: str = Form(...), 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(deps.get_current_user)
):
    """Encrypts and saves the Meraki API key to the user's profile."""
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
    """Logs into Meraki, upserts Orgs/Networks into Global Inventory, and maps access."""
    if not current_user.meraki_api_key_encrypted:
        return "<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem; border-radius: 4px;'>No API key found.</article>"
    
    api_key = security.decrypt_api_key(current_user.meraki_api_key_encrypted)
    
    try:
        dashboard = meraki.DashboardAPI(api_key=api_key, print_console=False, suppress_logging=True)
        orgs = dashboard.organizations.getOrganizations()
        
        # Clear out this specific user's old access map
        db.query(models.UserOrgAccess).filter(models.UserOrgAccess.user_id == current_user.id).delete()
        
        network_count = 0
        
        for org in orgs:
            # 1. Upsert Organization to Global List
            db.merge(models.MerakiOrganization(id=org['id'], name=org['name']))
            
            # 2. Grant this user access to this Org
            db.merge(models.UserOrgAccess(user_id=current_user.id, org_id=org['id']))
            
            # 3. Fetch and Upsert Networks to Global List
            try:
                networks = dashboard.organizations.getOrganizationNetworks(org['id'])
                for net in networks:
                    db.merge(models.MerakiNetwork(id=net['id'], org_id=org['id'], name=net['name']))
                    network_count += 1
            except meraki.APIError:
                continue
        
        db.commit()
        response.headers["HX-Refresh"] = "true"
        return ""
    
    except Exception as e:
        return f"<article style='background-color: #721c24; color: white; padding: 1rem; margin-bottom: 1rem; border-radius: 4px;'>Sync Error: {str(e)}</article>"

@router.get("/network/{network_id}/location")
def get_network_location(
    network_id: str,
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(deps.get_current_user)
):
    """Fetches the physical address and coordinates of devices in a specific network."""
    if not current_user.meraki_api_key_encrypted:
        raise HTTPException(status_code=400, detail="No API key found.")
    
    api_key = security.decrypt_api_key(current_user.meraki_api_key_encrypted)
    
    try:
        dashboard = meraki.DashboardAPI(api_key=api_key, print_console=False, suppress_logging=True)
        devices = dashboard.networks.getNetworkDevices(network_id)
        
        for dev in devices:
            if dev.get('address') or (dev.get('lat') and dev.get('lng')):
                return {
                    "status": "success",
                    "address": dev.get('address', 'Address not set in Meraki'),
                    "lat": dev.get('lat'),
                    "lng": dev.get('lng'),
                    "model": dev.get('model', 'Unknown Device')
                }
                
        return {"status": "not_found", "message": "No location data found on devices in this network."}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))