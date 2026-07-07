from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import meraki
from .. import models, schemas, security, deps
from ..database import get_db

router = APIRouter(prefix="/api/meraki", tags=["Meraki Integration"])

@router.post("/key")
def save_api_key(data: schemas.ApiKeyUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Encrypts and saves the Meraki API key to the user's profile."""
    encrypted_key = security.encrypt_api_key(data.api_key)
    current_user.meraki_api_key_encrypted = encrypted_key
    db.commit()
    return {"status": "success", "message": "API key saved securely."}

@router.post("/sync")
def sync_meraki_data(db: Session = Depends(get_db), current_user: models.User = Depends(deps.get_current_user)):
    """Logs into Meraki, fetches all Orgs and Networks, and caches them in PostgreSQL."""
    if not current_user.meraki_api_key_encrypted:
        raise HTTPException(status_code=400, detail="No API key found. Please save one first.")
    
    # Decrypt the key in memory just for this function
    api_key = security.decrypt_api_key(current_user.meraki_api_key_encrypted)
    
    try:
        # Initialize Meraki SDK (suppressing logs so it doesn't spam your Docker console)
        dashboard = meraki.DashboardAPI(api_key=api_key, print_console=False, suppress_logging=True)
        
        # 1. Get all Organizations
        orgs = dashboard.organizations.getOrganizations()
        
        # 2. Clear out the user's old cached networks
        db.query(models.MerakiNetworkCache).filter(models.MerakiNetworkCache.user_id == current_user.id).delete()
        
        new_cache_entries = []
        
        # 3. Fetch networks for each organization
        for org in orgs:
            try:
                networks = dashboard.organizations.getOrganizationNetworks(org['id'])
                for net in networks:
                    entry = models.MerakiNetworkCache(
                        user_id=current_user.id,
                        org_id=org['id'],
                        org_name=org['name'],
                        network_id=net['id'],
                        network_name=net['name']
                    )
                    new_cache_entries.append(entry)
            except meraki.APIError:
                # Some users have read-only org access where API is disabled. We just skip them safely.
                continue
        
        # 4. Save to the database
        if new_cache_entries:
            db.bulk_save_objects(new_cache_entries)
        db.commit()
        
        return {"status": "success", "message": f"Successfully synced {len(orgs)} orgs and {len(new_cache_entries)} networks."}
    
    except meraki.APIError as e:
        raise HTTPException(status_code=400, detail=f"Meraki API Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred during sync.")

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