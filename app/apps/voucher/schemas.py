import secrets
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from fastapi_mongo_base.schemas import TenantScopedEntitySchema
from fastapi_mongo_base.utils import bsontools
from pydantic import BaseModel, Field, field_validator
from ufaas.enums import Currency


class VoucherStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    USED = "used"


class VoucherCreateSchema(BaseModel):
    code: str = Field(
        default_factory=lambda: secrets.token_urlsafe(10),
        description="Unique voucher code",
    )
    status: VoucherStatus = Field(
        default=VoucherStatus.ACTIVE, description="Current status of the voucher"
    )
    rate: Decimal = Field(
        default=Decimal(0),
        gt=0,
        le=100,
        description="Discount proportion percentage (e.g., 10% = 10)",
    )
    cap: Decimal | None = Field(
        default=None, gt=0, description="Maximum discount amount"
    )
    currency: Currency = Currency.IRR
    expired_at: datetime | None = Field(
        default=None, description="Expiration date of the voucher"
    )
    max_uses: int | None = Field(
        default=None, ge=1, description="Maximum number of uses"
    )
    user_id: str | None = None
    limited_products: list[str] | None = None
    meta_data: dict | None = None

    @field_validator("rate", mode="before")
    @classmethod
    def validate_rate(cls, value: Decimal) -> Decimal:
        return bsontools.decimal_amount(value)

    @field_validator("cap", mode="before")
    @classmethod
    def validate_cap(cls, value: Decimal) -> Decimal:
        return bsontools.decimal_amount(value)

    def calculate_discount(self, amount: Decimal) -> Decimal:
        discount_value = amount * self.rate / 100
        discount_value = (
            discount_value if self.cap is None else min(discount_value, self.cap)
        )
        return discount_value


class VoucherUpdateSchema(BaseModel):
    status: VoucherStatus | None = None
    expired_at: datetime | None = None
    limit: int | None = None


class VoucherSchema(VoucherCreateSchema, TenantScopedEntitySchema):
    redeemed: int = Field(
        default=0, ge=0, description="Number of times the voucher has been used"
    )
