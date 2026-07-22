"""Tenant routes."""

from fastapi import Request
from fastapi_mongo_base.utils import usso_routes

from . import models, schemas


class TenantRouter(usso_routes.AbstractTenantUSSORouter):
    """Router for tenant endpoints."""

    model = models.Tenant
    schema = schemas.TenantSchema

    def config_routes(self, **kwargs: object) -> None:
        """Configure routes with update and delete disabled."""
        super().config_routes(update_route=False, delete_route=False, **kwargs)

    async def create_item(
        self,
        request: Request,
        data: schemas.TenantCreateSchema,
    ) -> models.Tenant:
        """Create a new tenant."""
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
