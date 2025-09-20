from datetime import datetime
from pydantic import BaseModel, EmailStr

# User
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    model_config = {"from_attributes": True}

# Token
class Token(BaseModel):
    access_token: str
    token_type: str

# Document
class DocumentOut(BaseModel):
    id: int
    filename: str
    storage_path: str
    uploaded_at: str

    model_config = {"from_attributes": True}
