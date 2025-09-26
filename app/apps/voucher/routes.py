from datetime import datetime

from fastapi import Query, Request
from fastapi_mongo_base.schemas import PaginatedResponse
from fastapi_mongo_base.utils import usso_routes

from server.config import Settings

from .models import Voucher
from .schemas import VoucherCreateSchema, VoucherSchema, VoucherUpdateSchema


class VoucherRouter(usso_routes.AbstractTenantUSSORouter):
    model = Voucher
    schema = VoucherSchema

    async def list_items(
        self,
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=0, le=Settings.page_max_limit),
        created_at_from: datetime | None = None,
        created_at_to: datetime | None = None,
    ) -> PaginatedResponse[VoucherSchema]:
        user = await self.get_user(request)
        return await self._list_items(
            request=request,
            offset=offset,
            limit=limit,
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            created_at_from=created_at_from,
            created_at_to=created_at_to,
        )

    async def create_item(self, request: Request, data: VoucherCreateSchema) -> Voucher:
        user = await self.get_user(request)
        item = self.model(
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            **data.model_dump(),
        )
        await item.save()
        return item  # self.create_response_schema(**item.model_dump())

    async def update_item(
        self, request: Request, uid: str, data: VoucherUpdateSchema
    ) -> Voucher:
        return await super().update_item(
            request, uid, data.model_dump(exclude_none=True, exclude_unset=True)
        )


router = VoucherRouter().router
