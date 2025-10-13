from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Self

from fastapi_mongo_base.schemas import TenantUserEntitySchema
from fastapi_mongo_base.utils.bsontools import decimal_amount
from pydantic import BaseModel, Field, field_validator, model_validator

from apps.product.models import Product
from apps.product.schemas import ItemType
from server.config import Settings
from utils.currency import Currency


class DiscountSchema(BaseModel):
    code: str
    user_id: str
    discount: Decimal = Field(default=Decimal(0), description="Discount amount")

    @field_validator("discount", mode="before")
    @classmethod
    def validate_discount(cls, value: Decimal) -> Decimal:
        return decimal_amount(value)


class VoucherSchema(BaseModel):
    code: str | None


class BasketItemCreateSchema(BaseModel):
    uid: str
    currency: str = Settings.currency
    quantity: Decimal = Decimal(1)

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, value: Decimal) -> Decimal:
        return decimal_amount(value)

    async def get_basket_item(self) -> Self:
        product = await Product.get_by_uid(self.uid)
        if product is None:
            raise ValueError(f"Product with id {self.uid} not found")
        return BasketItemSchema.model_validate(product.model_dump())


class BasketItemSchema(BasketItemCreateSchema):
    name: str
    description: str | None = None
    unit_price: Decimal
    currency: str = Settings.currency
    quantity: Decimal = Decimal(1)

    # Item type to distinguish between SaaS and e-commerce
    item_type: ItemType = ItemType.saas_package  # Default to e-commerce product

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

    async def reserve_product(self) -> None:
        return

    async def buy_product(self) -> None:
        return

    async def release_product(self) -> None:
        return


class BasketItemChangeSchema(BaseModel):
    quantity_change: Decimal | None = None
    new_quantity: Decimal | None = None

    @model_validator(mode="after")
    def validate_quantity(self) -> Self:
        if self.quantity_change is None and self.new_quantity is None:
            raise ValueError("Either quantity_change or new_quantity must be provided")
        if self.quantity_change is not None and self.new_quantity is not None:
            raise ValueError(
                "Only one of quantity_change or new_quantity can be provided"
            )
        return self


class BasketStatusEnum(StrEnum):
    active = "active"
    locked = "locked"
    reserved = "reserved"
    validated = "validated"
    paid = "paid"
    cancelled = "cancelled"
    expired = "expired"


class BasketDataSchema(TenantUserEntitySchema):
    status: BasketStatusEnum = Field(
        default=BasketStatusEnum.active, description="Status of the basket"
    )
    callback_url: str | None = Field(None, description="Callback URL for the basket")

    currency: Currency = Currency(Settings.currency)

    checkout_at: datetime | None = None
    purchase_id: str | None = None
    invoice_id: str | None = None

    discount: DiscountSchema | None = None
    voucher: VoucherSchema | None = None

    @property
    def is_modifiable(self) -> bool:
        return self.status == "active"

    @property
    def purchase_detail_url(self) -> str | None:
        if not self.purchase_id:
            return None
        return f"{Settings.core_url}{Settings.base_path}/purchases/{self.purchase_id}"


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
    user_id: str | None = None
    callback_url: str | None = None
    meta_data: dict[str, object] | None = None


class BasketUpdateSchema(BaseModel):
    status: Literal["active", "inactive", "paid", "reserve", "cancel"] | None = None
    items: list[BasketItemSchema] | None = None

    purchase_detail_url: str | None = None
    meta_data: dict[str, object] | None = None

    checkout_at: datetime | None = None
    invoice_id: str | None = None

    voucher: VoucherSchema | None = None
