import uuid

from fastapi import Request, Query
from ufaas_fastapi_business.routes import AbstractAuthRouter

from .models import Voucher
from .schemas import VoucherCreateSchema, VoucherSchema, VoucherUpdateSchema

from server.config import Settings
from datetime import datetime


class VoucherRouter(AbstractAuthRouter[Voucher, VoucherSchema]):
    def __init__(self):
        super().__init__(model=Voucher, schema=VoucherSchema, auth_policy="user_read")

    async def create_item(self, request: Request, data: VoucherCreateSchema):
        auth = await self.get_auth(request)
        item = self.model(
            business_name=auth.business.name,
            user_id=auth.user_id if auth.user_id else auth.user.uid,
            **data.model_dump(exclude=["user_id"]),
        )
        await item.save()
        return item  # self.create_response_schema(**item.model_dump())

    async def update_item(
        self, request: Request, uid: uuid.UUID, data: VoucherUpdateSchema
    ):
        return await super().update_item(
            request, uid, data.model_dump(exclude_none=True, exclude_unset=True)
        )


router = VoucherRouter().router
