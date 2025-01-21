import uuid

from fastapi import Request
from ufaas_fastapi_business.routes import AbstractAuthRouter

from .models import Voucher
from .schemas import VoucherCreateSchema, VoucherSchema, VoucherUpdateSchema


class VoucherRouter(AbstractAuthRouter[Voucher, VoucherSchema]):
    def __init__(self):
        super().__init__(model=Voucher, schema=VoucherSchema, user_dependency=None)

    def config_schemas(self, schema, **kwargs):
        super().config_schemas(schema)

    def config_routes(self, **kwargs):
        super().config_routes(delete_route=False, **kwargs)

    async def create_item(self, request: Request, data: VoucherCreateSchema):
        return await super().create_item(request, data.model_dump())

    async def update_item(
        self, request: Request, uid: uuid.UUID, data: VoucherUpdateSchema
    ):
        return await super().update_item(
            request, uid, data.model_dump(exclude_none=True, exclude_unset=True)
        )


router = VoucherRouter().router
