import os
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt
from cryptography.fernet import Fernet

# Get keys from the .env file
SECRET_KEY = os.environ.get("SECRET_KEY", "fallback_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600 # 10 hours for a work day

# Initialize Fernet for Meraki Key Encryption
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
fernet = Fernet(ENCRYPTION_KEY.encode()) if ENCRYPTION_KEY else None

# Initialize Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def encrypt_api_key(api_key: str) -> str:
    if not fernet: 
        return api_key
    return fernet.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    if not fernet: 
        return encrypted_key
    return fernet.decrypt(encrypted_key.encode()).decode()