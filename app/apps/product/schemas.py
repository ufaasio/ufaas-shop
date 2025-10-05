from decimal import Decimal
from enum import StrEnum

from fastapi_mongo_base.schemas import TenantUserEntitySchema
from fastapi_mongo_base.utils.bsontools import decimal_amount
from pydantic import BaseModel, ConfigDict, field_validator

from server.config import Settings
from utils.saas import Bundle


class ItemType(StrEnum):
    saas_package = "saas_package"
    retail_product = "retail_product"


class ProductStatus(StrEnum):
    active = "active"
    inactive = "inactive"
    expired = "expired"
    deleted = "deleted"
    trial = "trial"


class ProductCreateSchema(BaseModel):
    name: str
    description: str | None = None
    unit_price: Decimal
    currency: str = Settings.currency
    stock_quantity: Decimal | None = None

    item_type: ItemType = ItemType.saas_package  # Default to e-commerce product

    revenue_share_id: str | None = None
    tax_id: str | None = None
    merchant: str | None = None

    # SaaS-specific fields
    plan_duration: int | None = None  # Only for SaaS packages
    bundles: list[Bundle] | None = None  # Optional field for SaaS packages
    variant: str | None = None

    meta_data: dict[str, object] | None = None

    @field_validator("unit_price", mode="before")
    @classmethod
    def validate_price(cls, value: Decimal) -> Decimal:
        return decimal_amount(value)

    @field_validator("stock_quantity", mode="before")
    @classmethod
    def validate_quantity(cls, value: Decimal) -> Decimal:
        return decimal_amount(value)


class ProductSchema(ProductCreateSchema, TenantUserEntitySchema):
    status: ProductStatus = ProductStatus.active

    model_config = ConfigDict(allow_inf_nan=True)


class ProductUpdateSchema(BaseModel):
    name: str | None = None
    description: str | None = None
    unit_price: Decimal | None = None
    currency: str | None = None
    quantity: Decimal | None = None

    variant: str | None = None

    webhook_url: str | None = None

    revenue_share_id: str | None = None
    tax_id: str | None = None
    merchant: str | None = None

    # SaaS-specific fields
    plan_duration: int | None = None  # Only for SaaS packages
    bundles: list[Bundle] | None = None  # Optional field for SaaS packages

    meta_data: dict[str, object] | None = None
