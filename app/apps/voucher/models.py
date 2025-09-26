from typing import Self

from fastapi_mongo_base.models import TenantUserEntity

from .schemas import VoucherSchema, VoucherStatus


class Voucher(VoucherSchema, TenantUserEntity):
    @classmethod
    async def get_by_code(
        cls, tenant_id: str, code: str, user_id: str | None = None
    ) -> Self | None:
        base_query = cls.get_queryset(
            tenant_id=tenant_id, code=code, status=VoucherStatus.ACTIVE
        )
        if user_id:
            base_query["$or"] = [{"user_id": user_id}, {"user_id": None}]
        return await cls.find_one(base_query)
