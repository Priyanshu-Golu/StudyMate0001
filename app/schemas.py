from pydantic import BaseModel

# User schemas
class UserCreate(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    email: str

    model_config = {
        "from_attributes": True  # Pydantic V2
    }

# Token schema
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
