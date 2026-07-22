"""Product routes."""

from fastapi import Request
from fastapi_mongo_base.utils import usso_routes
from usso import UserData

import utils.usso

from .models import Product
from .schemas import ProductCreateSchema, ProductSchema, ProductUpdateSchema


class ProductsRouter(usso_routes.AbstractTenantUSSORouter):
    """Products router."""

    model = Product
    schema = ProductSchema

    async def get_user(self, request: Request, **kwargs: object) -> UserData:
        """Get the current user."""
        usso = utils.usso.get_usso()
        return usso(request)

    async def retrieve_item(self, request: Request, uid: str) -> Product:
        """Retrieve a product by UID."""
        item = await self.get_item(uid=uid)
        return item

    async def create_item(self, request: Request, data: ProductCreateSchema) -> Product:
        """Create a new product."""
        return await super().create_item(request, data.model_dump())

    async def update_item(
        self, request: Request, uid: str, data: ProductUpdateSchema
    ) -> Product:
        """Update an existing product."""
        return await super().update_item(
            request, uid, data.model_dump(exclude_none=True)
        )


router = ProductsRouter().router
