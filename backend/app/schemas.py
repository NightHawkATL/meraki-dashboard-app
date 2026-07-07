from pydantic import BaseModel

# What we expect when a user logs in or is created
class UserCreate(BaseModel):
    username: str
    password: str

# What we safely return to the frontend (NO PASSWORDS)
class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool

    class Config:
        from_attributes = True

# What the login endpoint returns
class Token(BaseModel):
    access_token: str
    token_type: str

class ApiKeyUpdate(BaseModel):
    api_key: str