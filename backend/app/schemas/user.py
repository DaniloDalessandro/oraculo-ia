from pydantic import BaseModel, EmailStr, field_validator


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


class AdminUserCreate(BaseModel):
    email: EmailStr
    senha: str
    nome: str
    setor: str
    perfil: str = "colaborador"

    @field_validator("perfil")
    @classmethod
    def perfil_valido(cls, v: str) -> str:
        if v not in ("administrador", "colaborador"):
            raise ValueError("Perfil deve ser 'administrador' ou 'colaborador'")
        return v


class AdminUserOut(BaseModel):
    id: str
    email: str
    nome: str | None
    setor: str | None
    perfil: str
    status_conta: str
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def uuid_to_str(cls, v):
        return str(v)

    @field_validator("created_at", mode="before")
    @classmethod
    def dt_to_str(cls, v):
        return v.isoformat() if v else ""


class AdminUserUpdate(BaseModel):
    nome: str | None = None
    setor: str | None = None
    perfil: str | None = None
    status_conta: str | None = None
    is_active: bool | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    nova_senha: str


class ChangePasswordRequest(BaseModel):
    senha_atual: str
    nova_senha: str


class AuditLogOut(BaseModel):
    id: str
    user_id: str | None
    acao: str
    detalhes: str | None
    ip: str | None
    created_at: str

    model_config = {"from_attributes": True}

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v):
        return str(v) if v else None

    @field_validator("created_at", mode="before")
    @classmethod
    def dt_to_str(cls, v):
        return v.isoformat() if v else ""
