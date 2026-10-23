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

def generate_compliant_password(settings=None) -> str:
    """Generates a random password strictly complying with AdminSettings policy."""
    import secrets
    import string

    min_length = getattr(settings, 'pwd_min_length', 12) if settings else 12
    length = max(12, int(min_length or 12))

    req_upper = getattr(settings, 'pwd_require_upper', True) if settings else True
    req_lower = getattr(settings, 'pwd_require_lower', True) if settings else True
    req_number = getattr(settings, 'pwd_require_number', True) if settings else True
    req_special = getattr(settings, 'pwd_require_special', True) if settings else True

    special_chars = "!@#$%^&*"
    chars = string.ascii_letters + string.digits + special_chars

    while True:
        pwd_chars = []
        if req_upper:
            pwd_chars.append(secrets.choice(string.ascii_uppercase))
        if req_lower:
            pwd_chars.append(secrets.choice(string.ascii_lowercase))
        if req_number:
            pwd_chars.append(secrets.choice(string.digits))
        if req_special:
            pwd_chars.append(secrets.choice(special_chars))

        remaining = length - len(pwd_chars)
        for _ in range(max(0, remaining)):
            pwd_chars.append(secrets.choice(chars))

        secrets.SystemRandom().shuffle(pwd_chars)
        pwd = ''.join(pwd_chars)

        if req_upper and not any(c.isupper() for c in pwd):
            continue
        if req_lower and not any(c.islower() for c in pwd):
            continue
        if req_number and not any(c.isdigit() for c in pwd):
            continue
        if req_special and not any(c in special_chars for c in pwd):
            continue
        return pwd

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