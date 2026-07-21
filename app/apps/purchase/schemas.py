"""schemas module."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal, Self

from fastapi_mongo_base.schemas import (
    TenantUserEntitySchema,
)
from fastapi_mongo_base.utils import bsontools, timezone
from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)
from ufaas.wallet import WalletSchema

from utils.currency import Currency
from utils.ipg import PaymentSchema, PaymentStatus

PurchaseStatus = PaymentStatus


class PurchaseCreateSchema(BaseModel):
    """PurchaseCreateSchema."""

    user_id: str  # | None = None
    wallet_id: str  # | None = None
    basket_id: str | None = None
    amount: Decimal
    currency: Currency = Currency.IRR

    description: str

    callback_url: str

    available_ipgs: list[str] | None = None
    accept_wallet: bool = True
    voucher_code: str | None = None

    @model_validator(mode="after")
    def validate_user_wallet(self) -> Self:
        """validate_user_wallet."""
        if not self.user_id and not self.wallet_id:
            raise ValueError("user_id or wallet_id should be set")
        return self

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        """validate_amount."""
        return bsontools.decimal_amount(value)

    @field_validator("callback_url", mode="before")
    @classmethod
    def validate_callback_url(cls, value: str) -> str:
        """validate_callback_url."""
        from utils.texttools import is_valid_url

        if not is_valid_url(value):
            raise ValueError(f"Invalid URL {value}")
        return value


class PurchaseUpdateSchema(BaseModel):
    """PurchaseUpdateSchema."""

    voucher_code: str | None = None


class PurchaseSchema(PurchaseCreateSchema, TenantUserEntitySchema):
    """PurchaseSchema."""

    status: PurchaseStatus = PurchaseStatus.INIT
    tries: dict[str, PaymentSchema] = Field(default_factory=dict)
    verified_at: datetime | None = None

    original_amount: Decimal = Decimal(0)

    duration: int = 60 * 60  # in seconds

    def is_overdue(self) -> bool:
        """is_overdue."""
        created_at = self.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.tz)
        now = datetime.now(timezone.tz)
        return created_at + timedelta(seconds=self.duration) < now

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        """validate_amount."""
        return bsontools.decimal_amount(value)

    @field_validator("original_amount", mode="before")
    @classmethod
    def validate_original_amount(cls, value: Decimal) -> Decimal:
        """validate_original_amount."""
        return bsontools.decimal_amount(value)

    @model_validator(mode="after")
    def validate_null_original_amount(self) -> Self:
        """validate_null_original_amount."""
        if not self.original_amount:
            self.original_amount = self.amount
        return self

    @field_serializer("status")
    @classmethod
    def serialize_status(cls, value: PurchaseStatus | str | object) -> str:
        """serialize_status."""
        if isinstance(value, PurchaseStatus):
            return value.value
        if isinstance(value, str):
            return value
        return str(value)


class PurchaseRetrieveSchema(PurchaseSchema):
    """PurchaseRetrieveSchema."""

    ipgs: list[str] | None = None
    wallets: list[WalletSchema] | WalletSchema | None = None


class Participant(BaseModel):
    """Participant."""

    wallet_id: str
    amount: Decimal


class ProposalCreateSchema(BaseModel):
    """ProposalCreateSchema."""

    amount: Decimal
    description: str | None = None
    note: str | None = None
    currency: Currency = Currency.IRR
    task_status: Literal["draft", "init"] = "draft"
    participants: list[Participant]
    meta_data: dict[str, object] | None = None


class PurchaseStartSchema(BaseModel):
    """PurchaseStartSchema."""

    name: str
    amount: Decimal
    currency: str
    callback_url: str
