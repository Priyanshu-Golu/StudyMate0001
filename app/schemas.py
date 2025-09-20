from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserRead(BaseModel):
    id: int
    email: EmailStr

    model_config = {"from_attributes": True}

class DocumentCreate(BaseModel):
    filename: str
    user_id: int

class DocumentRead(BaseModel):
    id: int
    filename: str
    user_id: int

    model_config = {"from_attributes": True}
