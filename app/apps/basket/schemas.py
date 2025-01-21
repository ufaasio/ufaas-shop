import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

import httpx
from fastapi_mongo_base.schemas import BusinessOwnedEntitySchema
from fastapi_mongo_base.utils.aionetwork import aio_request
from fastapi_mongo_base.utils.bsontools import decimal_amount
from pydantic import BaseModel, Field, field_validator
from server.config import Settings
from ufaas.apps.saas.schemas import Bundle


class DiscountSchema(BaseModel):
    code: str
    user_id: uuid.UUID
    discount: Decimal = Field(default=Decimal(0), gt=0, description="Discount amount")

    @field_validator("discount", mode="before")
    def validate_discount(cls, value):
        return decimal_amount(value)


class ItemType(str, Enum):
    saas_package = "saas_package"
    retail_product = "retail_product"


class BasketItemCreateSchema(BaseModel):
    product_url: str
    currency: str = Settings.currency
    quantity: Decimal = Decimal(1)
    # extra_data: dict | None = None

    async def a(product_url: str):
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(product_url) as response:
                response.raise_for_status()
                data: dict = await response.json()
        return data

    def from_allowed_domain(self):
        return True

    async def get_basket_item(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.product_url, headers={"Accept-Encoding": "identity"}
            )
            response.raise_for_status()
            data: dict = response.json()
        data.update(self.model_dump(exclude_none=True))
        return BasketItemSchema(**data)


class BasketItemSchema(BasketItemCreateSchema):
    uid: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    description: str | None = None
    unit_price: Decimal
    # currency: str = Settings.currency
    # quantity: Decimal = Decimal(1)

    # Item type to distinguish between SaaS and e-commerce
    item_type: ItemType = ItemType.retail_product  # Default to e-commerce product

    # product_url: str | None = None
    webhook_url: str | None = None
    reserve_url: str | None = None
    validation_url: str | None = None

    revenue_share_id: uuid.UUID | None = None
    tax_id: str | None = None
    merchant: str | None = None
    discount: DiscountSchema | None = None

    # SaaS-specific fields
    plan_duration: int | None = None  # Only for SaaS packages
    bundles: list[Bundle] | None = None  # Optional field for SaaS packages

    variant: dict[str, str] | None = None

    # Optional additional data field for future extensions or custom data
    meta_data: dict | None = None

    @property
    def price(self):
        price = self.unit_price * self.quantity
        if self.discount:
            price -= self.discount.apply_discount(price)
        return price

    def exchange_fee(self, currency):
        if self.currency != currency:
            # TODO: Implement currency exchange
            raise NotImplementedError("Currency exchange not implemented")
        return 1

    @field_validator("unit_price", mode="before")
    def validate_price(cls, value):
        return decimal_amount(value)

    @field_validator("quantity", mode="before")
    def validate_quantity(cls, value):
        return decimal_amount(value)

    async def validate_product(self):
        if self.validation_url is None:
            raise ValueError("Validation URL is not set")

        validation_data = await aio_request(method="GET", url=self.validation_url)
        if validation_data.get("price") != self.unit_price:
            return False

        if validation_data.get("stock_quantity") is None:
            return True

        if validation_data.get("stock_quantity") < self.quantity:
            return False

        # TODO check attributes

        return True

    async def reserve_product(self):
        if self.reserve_url is None:
            return

        return await aio_request(
            method="POST", url=self.reserve_url, json=self.model_dump()
        )

    async def webhook_product(self):
        if self.webhook_url is None:
            return

        return await aio_request(
            method="POST", url=self.webhook_url, json=self.model_dump()
        )


class BasketItemChangeSchema(BaseModel):
    quantity_change: Decimal = Decimal(1)


class BasketStatusEnum(str, Enum):
    active = "active"
    locked = "locked"
    reserved = "reserved"
    paid = "paid"
    cancelled = "cancelled"
    expired = "expired"


class BasketDataSchema(BusinessOwnedEntitySchema):
    status: BasketStatusEnum = Field(
        default=BasketStatusEnum.active, description="Status of the basket"
    )
    callback_url: str | None = Field(description="Callback URL for the basket")

    currency: str = Settings.currency

    checkout_at: datetime | None = None
    payment_detail_url: str | None = None
    invoice_id: uuid.UUID | None = None

    discount: DiscountSchema | None = None

    @property
    def is_modifiable(self):
        return self.status == "active"


class BasketDetailSchema(BasketDataSchema):
    items: list[BasketItemSchema] = []
    subtotal: Decimal = Field(description="Total amount of the basket")
    amount: Decimal = Field(description="Total amount of the basket after discount")

    @field_validator("items", mode="before")
    def validate_items(cls, value):
        if isinstance(value, dict):
            return [item for item in value.values()]
        return value

    @field_validator("subtotal", mode="before")
    def validate_subtotal(cls, value):
        return decimal_amount(value)

    @field_validator("amount", mode="before")
    def validate_amount(cls, value):
        return decimal_amount(value)


class BasketCreateSchema(BaseModel):
    callback_url: str | None = None
    meta_data: dict[str, Any] | None = None


class VoucherSchema(BaseModel):
    code: str


class BasketUpdateSchema(BaseModel):
    status: Literal["active", "inactive", "paid", "reserve", "cancel"] | None = None
    items: list[BasketItemSchema] | None = None

    payment_detail_url: str | None = None
    meta_data: dict[str, Any] | None = None

    checkout_at: datetime | None = None
    invoice_id: uuid.UUID | None = None

    voucher: VoucherSchema | None = None
