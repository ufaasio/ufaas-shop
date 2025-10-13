from datetime import datetime
from typing import Self

from fastapi_mongo_base.models import TenantUserEntity
from fastapi_mongo_base.utils import timezone

from .schemas import PurchaseSchema, PurchaseStatus


class Purchase(PurchaseSchema, TenantUserEntity):
    @classmethod
    async def get_purchase_by_code(cls, tenant_id: str, code: str) -> Self:
        return await cls.find_one({
            "is_deleted": False,
            "tenant_id": tenant_id,
            "code": code,
        })

    async def success(self, ref_id: int | None = None) -> Self:
        self.ref_id = ref_id
        self.status = PurchaseStatus.SUCCESS
        self.verified_at = datetime.now(timezone.tz)
        return await self.save()

    async def fail(self, failure_reason: str | None = None) -> Self:
        self.status = PurchaseStatus.FAILED
        self.failure_reason = failure_reason
        return await self.save()

    async def success_purchase(self, uid: str, *, save: bool = True) -> Self:
        purchase_trial = self.tries.get(uid)
        purchase_trial.status = PurchaseStatus.SUCCESS
        purchase_trial.verified_at = datetime.now(timezone.tz)
        if self.status == PurchaseStatus.SUCCESS:
            return self
        self.status = PurchaseStatus.SUCCESS
        self.verified_at = datetime.now(timezone.tz)
        if save:
            return await self.save()
        return self

    async def fail_purchase(self, uid: str, *, save: bool = True) -> Self:
        purchase_trial = self.tries.get(uid)
        purchase_trial.status = PurchaseStatus.FAILED
        purchase_trial.verified_at = datetime.now(timezone.tz)
        if self.is_overdue():
            self.status = PurchaseStatus.FAILED
        if save:
            return await self.save()
        return self

    @property
    def is_successful(self) -> bool:
        return self.status == PurchaseStatus.SUCCESS

    @property
    def start_purchase_url(self) -> str:
        return self.config.purchase_request_url(self.code)
