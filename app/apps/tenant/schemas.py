from fastapi_mongo_base.schemas import TenantScopedEntitySchema
from pydantic import BaseModel, Field


class TenantCreateSchema(BaseModel):
    tenant_id: str | None = None
    name: str
    description: str | None = None
    ipgs: list[str] = Field(default_factory=list)
    wallet_id: str


class TenantSchema(TenantCreateSchema, TenantScopedEntitySchema):
    pass
