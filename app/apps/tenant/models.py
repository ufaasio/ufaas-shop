"""Tenant models."""

from typing import Self

from fastapi_mongo_base.models import TenantScopedEntity

from .schemas import TenantSchema


class Tenant(TenantSchema, TenantScopedEntity):
    """Tenant model."""

    @classmethod
    async def get_by_tenant_id(cls, tenant_id: str) -> Self:
        """Get a tenant by its tenant_id."""
        return await cls.find_one({"tenant_id": tenant_id})
