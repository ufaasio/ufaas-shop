from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

import httpx
import uuid6
from fastapi_mongo_base.schemas import TenantUserEntitySchema
from fastapi_mongo_base.utils.bsontools import decimal_amount
from pydantic import BaseModel, Field, field_validator, model_validator

from server.config import Settings


class DiscountSchema(BaseModel):
    code: str
    user_id: str
    discount: Decimal = Decimal(
        0
    )  # Field(default=Decimal(0), gt=0, description="Discount amount")

    @field_validator("discount", mode="before")
    @classmethod
    def validate_discount(cls, value: Decimal) -> Decimal:
        return decimal_amount(value)


class ItemType(StrEnum):
    saas_package = "saas_package"
    retail_product = "retail_product"


class BasketItemCreateSchema(BaseModel):
    product_url: str
    currency: str = Settings.currency
    quantity: Decimal = Decimal(1)
    # extra_data: dict | None = None

    def from_allowed_domain(self) -> bool:
        return True

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, value: Decimal) -> Decimal:
        return decimal_amount(value)

    async def get_basket_item(self) -> "BasketItemSchema":
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.product_url, headers={"Accept-Encoding": "identity"}
            )
            response.raise_for_status()
            data: dict = response.json()
        data.update(self.model_dump(exclude_none=True))
        return BasketItemSchema(**data)


class BasketItemSchema(BasketItemCreateSchema):
    uid: str = Field(default_factory=lambda: str(uuid6.uuid7()))
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

    revenue_share_id: str | None = None
    tax_id: str | None = None
    merchant: str | None = None
    discount: DiscountSchema | None = None

    # SaaS-specific fields
    plan_duration: int | None = None  # Only for SaaS packages
    bundles: list | None = None  # Optional field for SaaS packages

    variant: dict[str, str] | None = None

    # Optional additional data field for future extensions or custom data
    meta_data: dict | None = None

    @property
    def price(self) -> Decimal:
        price = self.unit_price * self.quantity
        if self.discount:
            price -= self.discount.discount
        return price

    def exchange_fee(self, currency: str) -> int:
        if self.currency != currency:
            # TODO: Implement currency exchange
            raise NotImplementedError("Currency exchange not implemented")
        return 1

    @field_validator("unit_price", mode="before")
    @classmethod
    def validate_price(cls, value: Decimal) -> Decimal:
        return decimal_amount(value)

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, value: Decimal) -> Decimal:
        return decimal_amount(value)

    async def validate_product(self) -> bool:
        if self.validation_url is None:
            raise ValueError("Validation URL is not set")

        async with httpx.AsyncClient() as client:
            response = await client.get(self.validation_url)
            response.raise_for_status()
            validation_data: dict = response.json()
        if validation_data.get("price") != self.unit_price:
            return False

        if validation_data.get("stock_quantity") is None:
            return True

        # TODO check attributes

        return validation_data.get("stock_quantity", 0) >= self.quantity

    async def reserve_product(self) -> dict | None:
        if self.reserve_url is None:
            return

        async with httpx.AsyncClient() as client:
            response = await client.post(self.reserve_url, json=self.model_dump())
            response.raise_for_status()
            return response.json()

    async def webhook_product(self) -> dict | None:
        if self.webhook_url is None:
            return

        async with httpx.AsyncClient() as client:
            response = await client.post(self.webhook_url, json=self.model_dump())
            response.raise_for_status()
            return response.json()


class BasketItemChangeSchema(BaseModel):
    quantity_change: Decimal | None = None
    new_quantity: Decimal | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_quantity(cls, values: dict) -> dict:
        if values.get("quantity_change") is None and values.get("new_quantity") is None:
            raise ValueError("Either quantity_change or new_quantity must be provided")
        if (
            values.get("quantity_change") is not None
            and values.get("new_quantity") is not None
        ):
            raise ValueError(
                "Only one of quantity_change or new_quantity can be provided"
            )
        return values


class BasketStatusEnum(StrEnum):
    active = "active"
    locked = "locked"
    reserved = "reserved"
    paid = "paid"
    cancelled = "cancelled"
    expired = "expired"


class BasketDataSchema(TenantUserEntitySchema):
    status: BasketStatusEnum = Field(
        default=BasketStatusEnum.active, description="Status of the basket"
    )
    callback_url: str | None = Field(description="Callback URL for the basket")

    currency: str = Settings.currency

    checkout_at: datetime | None = None
    payment_detail_url: str | None = None
    invoice_id: str | None = None

    discount: DiscountSchema | None = None

    @property
    def is_modifiable(self) -> bool:
        return self.status == "active"


class BasketDetailSchema(BasketDataSchema):
    items: list[BasketItemSchema] = Field(default_factory=list)
    subtotal: Decimal = Field(description="Total amount of the basket")
    amount: Decimal = Field(description="Total amount of the basket after discount")

    @field_validator("items", mode="before")
    @classmethod
    def validate_items(cls, value: dict) -> list[BasketItemSchema]:
        if isinstance(value, dict):
            return list(value.values())
        return value

    @field_validator("subtotal", mode="before")
    @classmethod
    def validate_subtotal(cls, value: Decimal) -> Decimal:
        return decimal_amount(value)

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        return decimal_amount(value)


class BasketCreateSchema(BaseModel):
    callback_url: str | None = None
    meta_data: dict[str, Any] | None = None


class VoucherSchema(BaseModel):
    code: str | None


class BasketUpdateSchema(BaseModel):
    status: Literal["active", "inactive", "paid", "reserve", "cancel"] | None = None
    items: list[BasketItemSchema] | None = None

    payment_detail_url: str | None = None
    meta_data: dict[str, Any] | None = None

    checkout_at: datetime | None = None
    invoice_id: str | None = None

    voucher: VoucherSchema | None = None
