from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
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

    # Relationships map the user to their cached networks and history
    networks = relationship("MerakiNetworkCache", back_populates="owner")
    jobs = relationship("JobHistory", back_populates="owner")

class AdminSettings(Base):
    __tablename__ = "admin_settings"
    
    # We will enforce that only row ID 1 exists for global settings
    id = Column(Integer, primary_key=True, index=True)
    mapbox_api_key = Column(String, nullable=True)
    google_places_api_key = Column(String, nullable=True)
    require_2fa_all_users = Column(Boolean, default=False)
    meraki_auto_refresh_days = Column(Integer, default=7)
    
    # Password Policies
    pwd_min_length = Column(Integer, default=12)
    pwd_require_special = Column(Boolean, default=True)
    pwd_require_upper = Column(Boolean, default=True)
    pwd_require_lower = Column(Boolean, default=True)
    pwd_require_number = Column(Boolean, default=True)

class MerakiNetworkCache(Base):
    __tablename__ = "meraki_network_cache"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    org_id = Column(String, index=True)
    org_name = Column(String)
    network_id = Column(String, index=True)
    network_name = Column(String)
    last_synced = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="networks")

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