from pydantic import BaseModel, Field


class UserConfigOut(BaseModel):
    bot_ativo: bool
    limite_diario: int
    idioma: str
    nome_assistente: str
    # Sprint 3
    ia_ativa: bool
    limite_ia_diario: int
    nivel_detalhe: str

    model_config = {"from_attributes": True}


class UserConfigUpdate(BaseModel):
    bot_ativo: bool | None = None
    limite_diario: int | None = Field(None, ge=1, le=10000)
    idioma: str | None = None
    nome_assistente: str | None = Field(None, max_length=100)
    # Sprint 3
    ia_ativa: bool | None = None
    limite_ia_diario: int | None = Field(None, ge=1, le=10000)
    nivel_detalhe: str | None = Field(None, pattern="^(resumido|normal|detalhado)$")


class UserProfileOut(BaseModel):
    id: str
    email: str
    nome: str | None
    perfil: str
    status_conta: str
    telefone_vinculado: str | None
    config: UserConfigOut | None

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    nome: str | None = Field(None, max_length=100)
