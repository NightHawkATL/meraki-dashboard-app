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
        
        for org in orgs:
            org_id_str = str(org['id'])
            
            # 1. Upsert Organization to Global List
            db.merge(models.MerakiOrganization(id=org_id_str, name=org['name']))
            db.flush() # Force Postgres to create the Org immediately!
            
            # 2. Grant this user access to this Org
            db.merge(models.UserOrgAccess(user_id=current_user.id, org_id=org_id_str))
            
            # 3. Fetch and Upsert Networks to Global List
            try:
                networks = dashboard.organizations.getOrganizationNetworks(org['id'])
                for net in networks:
                    db.merge(models.MerakiNetwork(id=str(net['id']), org_id=org_id_str, name=net['name']))
                db.flush()
            except meraki.APIError:
                continue
        
        db.commit() # Finalize the entire transaction
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
    """Fetches the physical address, coordinates, and phone number of a network/hotel."""
    import re
    import urllib.request
    import urllib.parse
    import json

    net_record = db.query(models.MerakiNetwork).filter(models.MerakiNetwork.id == network_id).first()
    settings = db.query(models.AdminSettings).first()
    google_places_key = getattr(settings, 'google_places_api_key', None) or os.environ.get("GOOGLE_PLACES_API_KEY")

    if not current_user.meraki_api_key_encrypted:
        raise HTTPException(status_code=400, detail="No API key found.")
    
    api_key = security.decrypt_api_key(current_user.meraki_api_key_encrypted)
    
    try:
        dashboard = meraki.DashboardAPI(api_key=api_key, print_console=False, suppress_logging=True)

        network_info = {}
        try:
            network_info = dashboard.networks.getNetwork(network_id)
        except Exception:
            pass

        net_name = network_info.get("name") or (net_record.name if net_record else "Hotel Site")
        net_notes = network_info.get("notes") or ""

        devices = dashboard.networks.getNetworkDevices(network_id)
        
        address = None
        lat = None
        lng = None
        model = "Unknown Device"
        phone = getattr(net_record, 'phone', None) if net_record else None

        for dev in devices:
            if not address and dev.get('address'):
                address = dev.get('address')
            if lat is None and dev.get('lat') and dev.get('lng'):
                lat = dev.get('lat')
                lng = dev.get('lng')
            if model == "Unknown Device" and dev.get('model'):
                model = dev.get('model')
            
            # Check device notes or tags for phone
            dev_notes = dev.get('notes') or ""
            if not phone and dev_notes:
                match = re.search(r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})', dev_notes)
                if match:
                    phone = match.group(0)

        # Also inspect network notes for phone
        if not phone and net_notes:
            match = re.search(r'(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})', net_notes)
            if match:
                phone = match.group(0)

        # Google Places API Lookup if phone is missing
        if not phone and google_places_key and (net_name or address):
            try:
                search_query = f"{net_name} {address or ''}".strip()
                find_url = (
                    f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
                    f"?input={urllib.parse.quote(search_query)}&inputtype=textquery&fields=place_id,name,formatted_address&key={google_places_key}"
                )
                req = urllib.request.Request(find_url, headers={"User-Agent": "ParityMerakiApp/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    p_data = json.loads(resp.read().decode())
                    candidates = p_data.get("candidates", [])
                    if candidates:
                        place_id = candidates[0].get("place_id")
                        details_url = (
                            f"https://maps.googleapis.com/maps/api/place/details/json"
                            f"?place_id={place_id}&fields=formatted_phone_number,international_phone_number,formatted_address,geometry&key={google_places_key}"
                        )
                        with urllib.request.urlopen(urllib.request.Request(details_url), timeout=5) as d_resp:
                            details = json.loads(d_resp.read().decode()).get("result", {})
                            phone = details.get("formatted_phone_number") or details.get("international_phone_number")
                            if not address and details.get("formatted_address"):
                                address = details.get("formatted_address")
                            if lat is None and details.get("geometry", {}).get("location"):
                                lat = details["geometry"]["location"].get("lat")
                                lng = details["geometry"]["location"].get("lng")
            except Exception as e:
                print(f"Google Places lookup error: {e}")

        # OpenStreetMap Nominatim reverse/search lookup fallback
        if not phone and (lat and lng):
            try:
                osm_url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json&extratags=1"
                req = urllib.request.Request(osm_url, headers={"User-Agent": "ParityMerakiApp/1.0 (internal-dashboard)"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    osm_data = json.loads(resp.read().decode())
                    tags = osm_data.get("extratags", {}) or {}
                    phone = tags.get("phone") or tags.get("contact:phone")
            except Exception:
                pass

        # Update cache in MerakiNetwork
        if net_record:
            if address:
                net_record.address = address
            if phone:
                net_record.phone = phone
            if lat is not None:
                net_record.lat = lat
                net_record.lng = lng
            db.commit()

        if address or (lat and lng) or phone:
            return {
                "status": "success",
                "name": net_name,
                "address": address or "Address not set in Meraki",
                "phone": phone or "No phone number listed",
                "lat": lat,
                "lng": lng,
                "model": model
            }
                
        return {"status": "not_found", "message": "No location data found on devices in this network."}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))