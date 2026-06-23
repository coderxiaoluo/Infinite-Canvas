from pydantic import BaseModel, Field


class AuthStatusResponse(BaseModel):
    auth_mode: str = Field(description="off | required")
    auth_required: bool
    database_configured: bool
    database_connected: bool
    database_error: str | None = None
    bootstrap_complete: bool
    jwt_access_expire_minutes: int
    jwt_refresh_expire_days: int
    has_users: bool = False
    has_owner: bool = False


class AuthCredentialsRequest(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=6, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(default="", max_length=512)


class UserPublic(BaseModel):
    id: str
    tenant_id: str
    username: str
    account_type: str
    role: str
    status: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class MeResponse(BaseModel):
    auth_required: bool
    user: UserPublic | None = None
    is_owner: bool = False
    can_manage_providers: bool = False
    can_manage_members: bool = False


class LogoutResponse(BaseModel):
    ok: bool = True


class OkResponse(BaseModel):
    ok: bool = True


class MemberPublic(BaseModel):
    id: str
    username: str
    account_type: str
    role: str
    status: str
    created_at: int = 0
    last_login_at: int = 0


class MemberCreateRequest(BaseModel):
    username: str = Field(min_length=4, max_length=80, pattern=r"^[a-zA-Z0-9]+$")
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(default="editor", pattern="^(editor|viewer)$")


class MemberUpdateRequest(BaseModel):
    role: str | None = None
    status: str | None = None


class MemberResetPasswordRequest(BaseModel):
    password: str = Field(min_length=6, max_length=128)


class MemberListResponse(BaseModel):
    members: list[MemberPublic]
