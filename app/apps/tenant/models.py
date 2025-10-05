from typing import Self

from fastapi_mongo_base.models import TenantScopedEntity

from .schemas import TenantSchema


class Tenant(TenantSchema, TenantScopedEntity):
    @classmethod
    async def get_by_tenant_id(cls, tenant_id: str) -> Self:
        return await cls.find_one({"tenant_id": tenant_id})
