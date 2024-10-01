import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from fastapi_mongo_base.schemas import BusinessOwnedEntitySchema
from pydantic import BaseModel, Field, field_validator

from server.config import Settings
from utils.aionetwork import aio_request
from utils.numtools import decimal_amount


class DiscountSchema(BaseModel):
    percentage: Decimal = Decimal(0)
    max_amount: Decimal | None = None
    min_amount: Decimal | None = None

    @field_validator("percentage")
    def validate_percentage(cls, value):
        return decimal_amount(value)

    @field_validator("max_amount")
    def validate_max_amount(cls, value):
        return decimal_amount(value)

    @field_validator("min_amount")
    def validate_min_amount(cls, value):
        return decimal_amount(value)

    def apply_discount(self, total: Decimal):
        if self.min_amount and total < self.min_amount:
            return total

        discount = total * self.percentage
        if self.max_amount and discount > self.max_amount:
            return self.max_amount

        return discount


class BasketItemSchema(BaseModel):
    uid: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str
    description: str | None = None
    unit_price: Decimal
    currency: str = Settings.currency
    quantity: Decimal = Decimal(1)
    variant: dict[str, str] | None = None

    product_url: str | None = None
    webhook_url: str | None = None
    reserve_url: str | None = None
    validation_url: str | None = None

    revenue_share_id: uuid.UUID | None = None
    tax_id: str | None = None
    merchant: str | None = None
    meta_data: dict[str, Any] | None = None
    discount: DiscountSchema | None = None

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

    @field_validator("unit_price")
    def validate_price(cls, value):
        return decimal_amount(value)

    @field_validator("quantity")
    def validate_quantity(cls, value):
        return decimal_amount(value)

    async def validate_product(self):
        if self.validation_url is None:
            return True

        validation_data = await aio_request(method="GET", url=self.validation_url)
        if validation_data.get("price") != self.unit_price:
            return False

        if validation_data.get("stock_quantity") is None:
            return True

        if validation_data.get("stock_quantity") < self.quantity:
            return False

        return True

    async def reserve_product(self):
        if self.reserve_url is None:
            return

        await aio_request(method="POST", url=self.reserve_url, json=self.model_dump())

    async def webhook_product(self):
        if self.webhook_url is None:
            return

        await aio_request(method="POST", url=self.webhook_url, json=self.model_dump())


class BasketItemChangeSchema(BaseModel):
    quantity_change: Decimal = Decimal(1)


class BasketDataSchema(BusinessOwnedEntitySchema):
    status: Literal["active", "inactive", "paid", "reserve", "cancel"] = Field(
        "active", description="Status of the basket"
    )
    callback_url: str = Field(description="Callback URL for the basket")

    currency: str = Settings.currency
    discount: DiscountSchema | None = None

    checkout_at: datetime | None = None
    payment_detail_url: str | None = None
    invoice_id: uuid.UUID | None = None

    @property
    def is_modifiable(self):
        return self.status == "active"


class BasketDetailSchema(BasketDataSchema):
    items: list[BasketItemSchema] = []
    total: Decimal = Field(description="Total amount of the basket")

    @field_validator("items")
    def validate_items(cls, value):
        if isinstance(value, dict):
            return [item for item in value.values()]
        return value

    @field_validator("total")
    def validate_total(cls, value):
        return decimal_amount(value)


class BasketCreateSchema(BaseModel):
    callback_url: str | None = None
    meta_data: dict[str, Any] | None = None


class BasketUpdateSchema(BaseModel):
    status: Literal["active", "inactive", "paid", "reserve", "cancel"] | None = None
    items: list[BasketItemSchema] | None = None
    discount: DiscountSchema | None = None
    payment_detail_url: str | None = None
    meta_data: dict[str, Any] | None = None

    checkout_at: datetime | None = None
    payment_detail_url: str | None = None
    invoice_id: uuid.UUID | None = None
