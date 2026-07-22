from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    is_admin = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String, nullable=True)
    meraki_api_key_encrypted = Column(String, nullable=True)
    
    # User-specific AI overrides
    user_ai_provider = Column(String, nullable=True) # gemini, groq, ollama
    user_ai_api_key = Column(String, nullable=True)
    user_ai_custom_url = Column(String, nullable=True) # For Ollama/Custom endpoints

    jobs = relationship("JobHistory", back_populates="owner")

class AdminSettings(Base):
    __tablename__ = "admin_settings"
    
    # We will enforce that only row ID 1 exists for global settings
    id = Column(Integer, primary_key=True, index=True)
    mapbox_api_key = Column(String, nullable=True)
    google_places_api_key = Column(String, nullable=True)
    require_2fa_all_users = Column(Boolean, default=False)
    meraki_auto_refresh_days = Column(Integer, default=7)
    
    # AI Fallback Settings (Gemini)
    global_ai_enabled = Column(Boolean, default=False)
    global_gemini_api_key = Column(String, nullable=True)

    
    # Password Policies
    pwd_min_length = Column(Integer, default=12)
    pwd_require_special = Column(Boolean, default=True)
    pwd_require_upper = Column(Boolean, default=True)
    pwd_require_lower = Column(Boolean, default=True)
    pwd_require_number = Column(Boolean, default=True)

class MerakiOrganization(Base):
    __tablename__ = "meraki_organizations"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)

class MerakiNetwork(Base):
    __tablename__ = "meraki_networks"
    id = Column(String, primary_key=True, index=True)
    org_id = Column(String, ForeignKey("meraki_organizations.id"))
    name = Column(String)

class MerakiDevice(Base):
    __tablename__ = "meraki_devices"
    serial = Column(String, primary_key=True, index=True)
    network_id = Column(String, ForeignKey("meraki_networks.id"))
    name = Column(String, nullable=True)
    mac = Column(String, nullable=True)
    model = Column(String, nullable=True)
    address = Column(String, nullable=True)
    lat = Column(Float, nullable=True)  # <--- Make sure you import Float at the top of models.py!
    lng = Column(Float, nullable=True)

class UserOrgAccess(Base):
    __tablename__ = "user_org_access"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    org_id = Column(String, ForeignKey("meraki_organizations.id"), primary_key=True)

class JobHistory(Base):
    __tablename__ = "job_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    script_name = Column(String)
    target_network_id = Column(String)
    status = Column(String) # Pending, Running, Success, Failed
    progress_log = Column(JSON, default=[]) # Stores step-by-step logs
    output_file_path = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="jobs")