from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas, security
from ..database import get_db
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/setup", response_model=schemas.UserResponse)
def setup_admin(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Creates the initial Admin user. Fails if an admin already exists."""
    admin_exists = db.query(models.User).filter(models.User.is_admin == True).first()
    if admin_exists:
        raise HTTPException(status_code=400, detail="Admin user already exists.")
    
    hashed_password = security.get_password_hash(user.password)
    new_user = models.User(
        username=user.username,
        password_hash=hashed_password,
        is_admin=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Initialize the Global Admin Settings row
    settings = models.AdminSettings()
    db.add(settings)
    db.commit()

    return new_user

@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticates a user and returns a secure JWT token."""
    # Notice we now use form_data.username instead of user.username
    db_user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    if not db_user or not security.verify_password(form_data.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid username or password"
        )
    
    # Generate the JWT Token
    access_token = security.create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}
    
@router.get("/status")
def get_system_status(db: Session = Depends(get_db)):
    """Checks if the system has been initialized with an admin user."""
    admin_exists = db.query(models.User).filter(models.User.is_admin == True).first() is not None
    return {"admin_exists": admin_exists}