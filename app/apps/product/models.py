from fastapi_mongo_base.models import TenantUserEntity

from .schemas import ProductSchema


class Product(ProductSchema, TenantUserEntity):
    pass
