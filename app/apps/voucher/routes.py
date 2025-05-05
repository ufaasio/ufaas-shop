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

    async def list_items(
        self,
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=0, le=Settings.page_max_limit),
        created_at_from: datetime | None = None,
        created_at_to: datetime | None = None,
    ):
        auth = await self.get_auth(request)
        return await self._list_items(
            request=request,
            offset=offset,
            limit=limit,
            user_id=auth.user_id if auth.issuer_type == "User" else None,
            business_name=auth.business.name,
            created_at_from=created_at_from,
            created_at_to=created_at_to,
        )

    async def create_item(self, request: Request, data: VoucherCreateSchema):
        auth = await self.get_auth(request)

        item = self.model(
            business_name=auth.business.name,
            **data.model_dump(),
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
