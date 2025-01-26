import uuid

from fastapi_mongo_base.models import BusinessOwnedEntity
from pymongo import ASCENDING, IndexModel

from .schemas import VoucherSchema, VoucherStatus


class Voucher(VoucherSchema, BusinessOwnedEntity):
    class Settings:
        indexes = BusinessOwnedEntity.Settings.indexes + [
            IndexModel([("code", ASCENDING)], unique=True),
        ]

    @classmethod
    async def get_by_code(
        cls, business_name: str, code: str, user_id: uuid.UUID | None = None
    ) -> "Voucher":
        base_query = cls.get_queryset(
            business_name=business_name, code=code, status=VoucherStatus.ACTIVE
        )
        if user_id:
            base_query.append({"$or": [{"user_id": user_id}, {"user_id": None}]})
        return await cls.find_one(*base_query)
