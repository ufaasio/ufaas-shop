from fastapi import Request
from fastapi_mongo_base.utils import usso_routes

from . import models, schemas


class TenantRouter(usso_routes.AbstractTenantUSSORouter):
    model = models.Tenant
    schema = schemas.TenantSchema

    def config_routes(self, **kwargs: object) -> None:
        super().config_routes(update_route=False, delete_route=False, **kwargs)  # type: ignore

    async def create_item(
        self,
        request: Request,
        data: schemas.TenantCreateSchema,  # type: ignore
    ) -> models.Tenant:
        user = await self.get_user(request)
        await self.authorize(
            action="create", user=user, filter_data=data.model_dump(exclude_none=True)
        )
        if data.tenant_id is None:
            data.tenant_id = user.tenant_id
        item = models.Tenant.model_validate(data.model_dump())
        await item.create()
        return item


router = TenantRouter().router
