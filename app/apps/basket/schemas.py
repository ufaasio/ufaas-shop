"""Basket schemas."""

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
    """Discount schema."""

    code: str
    user_id: str
    discount: Decimal = Field(default=Decimal(0), description="Discount amount")

    @field_validator("discount", mode="before")
    @classmethod
    def validate_discount(cls, value: Decimal) -> Decimal:
        """Validate discount."""
        return decimal_amount(value)


class VoucherSchema(BaseModel):
    """Voucher schema."""

    code: str | None


class BasketItemCreateSchema(BaseModel):
    """Basket item create schema."""

    uid: str
    currency: str = Settings.currency
    quantity: Decimal = Decimal(1)

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, value: Decimal) -> Decimal:
        """Validate quantity."""
        return decimal_amount(value)

    async def get_basket_item(self) -> Self:
        """Get basket item from product."""
        product = await Product.get_by_uid(self.uid)
        if product is None:
            raise ValueError
        return BasketItemSchema.model_validate(product.model_dump())


class BasketItemSchema(BasketItemCreateSchema):
    """Basket item schema."""

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
        """Calculate price."""
        price = self.unit_price * self.quantity
        if self.discount:
            price -= self.discount.discount
        return price

    def exchange_fee(self, currency: str) -> int:
        """Calculate exchange fee."""
        if self.currency != currency:
            # TODO: Implement currency exchange
            raise NotImplementedError("Currency exchange not implemented")
        return 1

    @field_validator("unit_price", mode="before")
    @classmethod
    def validate_price(cls, value: Decimal) -> Decimal:
        """Validate unit price."""
        return decimal_amount(value)

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, value: Decimal) -> Decimal:
        """Validate quantity."""
        return decimal_amount(value)

    async def reserve_product(self) -> None:
        """Reserve product."""
        return

    async def buy_product(self) -> None:
        """Buy product."""
        return

    async def release_product(self) -> None:
        """Release product."""
        return


class QuantityChangeRequiredError(ValueError):
    """Quantity change required error."""

    def __init__(self) -> None:
        """Initialize error."""
        super().__init__("Either quantity_change or new_quantity must be provided")


class QuantityConflictError(ValueError):
    """Quantity conflict error."""

    def __init__(self) -> None:
        """Initialize error."""
        super().__init__("Only one of quantity_change or new_quantity can be provided")


class BasketItemChangeSchema(BaseModel):
    """Basket item change schema."""

    quantity_change: Decimal | None = None
    new_quantity: Decimal | None = None

    @model_validator(mode="after")
    def validate_quantity(self) -> Self:
        """Validate quantity change."""
        if self.quantity_change is None and self.new_quantity is None:
            raise QuantityChangeRequiredError()
        if self.quantity_change is not None and self.new_quantity is not None:
            raise QuantityConflictError()
        return self


class BasketStatusEnum(StrEnum):
    """Basket status enum."""

    active = "active"
    locked = "locked"
    reserved = "reserved"
    validated = "validated"
    paid = "paid"
    cancelled = "cancelled"
    expired = "expired"


class BasketDataSchema(TenantUserEntitySchema):
    """Basket data schema."""

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
        """Check if basket is modifiable."""
        return self.status == "active"

    @property
    def purchase_detail_url(self) -> str | None:
        """Purchase detail URL."""
        if not self.purchase_id:
            return None
        return f"{Settings.root_url}{Settings.base_path}/purchases/{self.purchase_id}"


class BasketDetailSchema(BasketDataSchema):
    """Basket detail schema."""

    items: list[BasketItemSchema] = Field(default_factory=list)
    subtotal: Decimal = Field(description="Total amount of the basket")
    amount: Decimal = Field(description="Total amount of the basket after discount")

    @field_validator("items", mode="before")
    @classmethod
    def validate_items(cls, value: dict) -> list[BasketItemSchema]:
        """Validate items format."""
        if isinstance(value, dict):
            return list(value.values())
        return value

    @field_validator("subtotal", mode="before")
    @classmethod
    def validate_subtotal(cls, value: Decimal) -> Decimal:
        """Validate subtotal."""
        return decimal_amount(value)

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        """Validate amount."""
        return decimal_amount(value)


class BasketCreateSchema(BaseModel):
    """Basket create schema."""

    user_id: str | None = None
    callback_url: str | None = None
    meta_data: dict[str, object] | None = None


class BasketUpdateSchema(BaseModel):
    """Basket update schema."""

    status: Literal["active", "inactive", "paid", "reserve", "cancel"] | None = None
    items: list[BasketItemSchema] | None = None

    purchase_detail_url: str | None = None
    meta_data: dict[str, object] | None = None

    checkout_at: datetime | None = None
    invoice_id: str | None = None

    voucher: VoucherSchema | None = None
