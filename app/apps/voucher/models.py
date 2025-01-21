from fastapi_mongo_base.models import BusinessOwnedEntity
from pymongo import ASCENDING, IndexModel

from .schemas import VoucherSchema, VoucherStatus


class Voucher(VoucherSchema, BusinessOwnedEntity):
    class Settings:
        indexes = BusinessOwnedEntity.Settings.indexes + [
            IndexModel([("wallet_id", ASCENDING)], unique=True),
        ]

    @classmethod
    async def get_by_code(cls, business_name: str, code: str) -> "Voucher":
        query = cls.get_query(
            business_name=business_name, code=code, status=VoucherStatus.ACTIVE
        )
        return await query.first()