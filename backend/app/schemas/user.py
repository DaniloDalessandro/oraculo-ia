from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    senha: str


class UserOut(BaseModel):
    id: str
    email: str
    is_active: bool

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerifyLoginTokenRequest(BaseModel):
    token: str
    email: EmailStr
    senha: str


class VerifyLoginTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    message: str
