from fastapi import Depends, HTTPException, status, Request
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from . import models, security, database

def get_current_user(request: Request, db: Session = Depends(database.get_db)):
    """Reads the secure HTTP-only cookie to identify the user."""
    token = request.cookies.get("access_token")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated"
    )
    
    if not token:
        raise credentials_exception
        
    # Remove the "Bearer " prefix from the cookie string
    if token.startswith("Bearer "):
        token = token[7:]
        
    try:
        # Decode the JWT token to find the username
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    # Find the user in the database
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
        
    return user