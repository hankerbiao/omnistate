"""网关服务数据模型。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

from .enums import ApiKeyStatus, EnvName, HttpMethod, LogStatus


class APIResponse(BaseModel):
    """与 DML 主后端一致的响应信封。"""

    code: int = 0
    message: str = "ok"
    data: Any = None


class UserQuota(BaseModel):
    enabled: bool = True
    monthlyLimit: int = 100000
    rpmLimit: int = 120
    concurrency: int = 10


class ConsoleUser(BaseModel):
    id: str
    username: str | None = None
    name: str
    email: str
    role: str
    team: str
    avatar: str
    allowedCapabilityIds: list[str]
    quota: UserQuota
    mustChangePassword: bool = False

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class UpdateUserPermissionsRequest(BaseModel):
    allowedCapabilityIds: list[str] = Field(default_factory=list)


class UpdateUserQuotaRequest(BaseModel):
    quota: UserQuota


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    user: ConsoleUser


class CreateConsoleUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    role: str = Field(default="developer", pattern="^(admin|developer)$")
    allowedCapabilityIds: list[str] = Field(default_factory=list)
    quota: UserQuota = Field(default_factory=UserQuota)


class ChangePasswordRequest(BaseModel):
    oldPassword: str = Field(min_length=1, max_length=128)
    newPassword: str = Field(min_length=6, max_length=128)


class ApiKey(BaseModel):
    id: str
    name: str
    prefix: str
    masked: str
    status: ApiKeyStatus
    scopes: list[str]
    createdAt: str
    lastUsedAt: str | None = None
    callsToday: int = 0
    env: EnvName
    plaintext: str | None = Field(default=None, exclude=True)
    ownerUserId: str = "user_admin"
    upstreamUserId: str | None = Field(default=None, exclude=True)
    quota: UserQuota = Field(default_factory=UserQuota, exclude=True)


class CreatedApiKey(BaseModel):
    key: ApiKey
    plaintext: str


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    env: EnvName
    scopes: list[str] = Field(default_factory=list)
    ownerUserId: str | None = None


class CapabilityParam(BaseModel):
    name: str
    type: str
    required: bool
    description: str


class Capability(BaseModel):
    id: str
    name: str
    category: str
    method: HttpMethod
    path: str
    summary: str
    description: str
    params: list[CapabilityParam]
    scope: str
    handler: Literal["proxy", "local", "aggregate"]
    upstreamPath: str | None = None
    sampleResponse: str

    @model_validator(mode="after")
    def validate_execution_contract(self) -> "Capability":
        if self.handler == "proxy" and not self.upstreamPath:
            raise ValueError("proxy capability must define upstreamPath")
        if self.handler != "proxy" and self.upstreamPath:
            raise ValueError("only proxy capability may define upstreamPath")
        return self


class CurrentUserCapabilitiesResponse(BaseModel):
    user: ConsoleUser
    capabilities: list[Capability]


class CallLog(BaseModel):
    id: str
    timestamp: str
    requestId: str
    appName: str
    keyName: str
    method: HttpMethod
    endpoint: str
    statusCode: int
    status: LogStatus
    latencyMs: int
    gatewayLatencyMs: int
    ip: str
    requestBody: str | None = None
    responseBody: str
    errorCode: str | None = None
    diagnosis: str | None = None


class OverviewStats(BaseModel):
    totalCallsToday: int
    totalCallsTrend: float
    successRate: float
    successRateTrend: float
    activeKeys: int
    quotaUsed: int
    quotaLimit: int
    daily: list[dict[str, Any]]
    topCapabilities: list[dict[str, Any]]


class DebugRequest(BaseModel):
    capabilityId: str
    keyId: str
    env: EnvName
    params: dict[str, str] = Field(default_factory=dict)


class ConsolePrincipal(BaseModel):
    user: ConsoleUser

    @property
    def user_id(self) -> str:
        return self.user.id

    @property
    def is_admin(self) -> bool:
        return self.user.is_admin

    @property
    def owner_filter(self) -> str | None:
        return None if self.is_admin else self.user.id


class DebugResponse(BaseModel):
    requestId: str
    statusCode: int
    latencyMs: int
    requestUrl: str
    responseBody: str


class WebhookRegistration(BaseModel):
    url: HttpUrl
    events: list[str]
    secret: str | None = None


class WebhookRecord(BaseModel):
    id: str
    ownerUserId: str
    url: str
    events: list[str]
    status: str = "active"
    createdAt: str


class AuthenticatedKey(BaseModel):
    key: ApiKey
    presented_token: str
