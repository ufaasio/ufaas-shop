"""SaaS enrollment schemas and utilities."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Self

from fastapi_mongo_base.schemas import TenantUserEntitySchema
from fastapi_mongo_base.utils.bsontools import decimal_amount
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Bundle(BaseModel):
    """A bundle of asset quota."""

    asset: str
    quota: Decimal
    order: Literal[0, 1, 2] = 1
    unit: str | None = None
    meta_data: dict | None = None

    model_config = ConfigDict(allow_inf_nan=True)

    @field_validator("quota", mode="before")
    @classmethod
    def validate_quota(cls, value: Decimal) -> Decimal:
        """Validate and convert the quota amount."""
        return decimal_amount(value)


class AcquisitionType(StrEnum):
    """Acquisition type enum for enrollments."""

    trial = "trial"
    purchased = "purchased"
    gifted = "gifted"
    promotion = "promotion"
    borrowed = "borrowed"
    postpaid = "postpaid"

    @classmethod
    def normal_types(cls) -> list[str]:
        """Get the list of normal acquisition types."""
        return [
            cls.trial,
            cls.purchased,
            cls.gifted,
            cls.promotion,
            cls.postpaid,
        ]


class DurationConflictError(ValueError):
    """Raised when both expire_at and duration_days are provided."""

    def __init__(self) -> None:
        """Initialize the error with a default message."""
        super().__init__("Only one of expire_at or duration_days should be provided")


class BundlesRequiredError(ValueError):
    """Raised when no bundles are provided."""

    def __init__(self) -> None:
        """Initialize the error with a default message."""
        super().__init__("Bundles are required")


class EnrollmentCreateSchema(BaseModel):
    """Schema for creating a new enrollment."""

    user_id: str
    bundles: list[Bundle]

    price: Decimal = Decimal(0)
    invoice_id: str | None = None
    start_at: datetime = Field(default_factory=datetime.now)
    expire_at: datetime | None = None
    duration: int | None = Field(None, description="Duration in days")
    status: Literal["active", "inactive"] = "active"
    acquisition_type: AcquisitionType = AcquisitionType.purchased

    variant: str | None = None
    meta_data: dict | None = None

    due_date: datetime | None = None

    model_config = ConfigDict(allow_inf_nan=True)

    @model_validator(mode="after")
    def validate_duration(self) -> Self:
        """Validate that expire_at and duration are not both set."""
        if self.expire_at and self.duration:
            raise DurationConflictError()

        return self

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, value: Decimal) -> Decimal:
        """Validate and convert the price amount."""
        return decimal_amount(value)

    @field_validator("bundles", mode="after")
    @classmethod
    def validate_bundles(cls, value: list[Bundle]) -> list[Bundle]:
        """Validate that bundles list is not empty."""
        if not value:
            raise BundlesRequiredError()
        return value


class DueDateRequiredError(ValueError):
    """Raised when due date is missing for borrowed acquisitions."""

    def __init__(self) -> None:
        """Initialize the error with a default message."""
        super().__init__("Due date must be provided for borrowed acquisitions")


class EnrollmentSchema(EnrollmentCreateSchema, TenantUserEntitySchema):
    """Schema for an existing enrollment."""

    paid_at: datetime | None = None

    @model_validator(mode="after")
    def validate_duration(self) -> Self:
        """Validate enrollment duration (overridden from parent)."""
        return self

    @model_validator(mode="after")
    def validate_due_date(self) -> Self:
        """Validate that due date is provided for borrowed acquisitions."""
        if self.acquisition_type == AcquisitionType.borrowed and not self.due_date:
            raise DueDateRequiredError()
        if self.acquisition_type == AcquisitionType.borrowed:
            self.paid_at = False if self.paid_at is None else self.paid_at
        return self

    def summary(self, tabs: int = 0) -> str:
        """Return a text summary of the enrollment."""
        now = datetime.now()
        exp = (self.expire_at - now).seconds if self.expire_at else "inf"
        s = f"{'\t' * tabs}{self.uid}: ({self.variant}) {exp} ["
        for b in self.bundles:
            s += f"({b.asset}: {b.quota}) "
        s += "]\n"
        return s

    @classmethod
    def summaries(cls, enrollments: list[Self], tabs: int = 0) -> str:
        """Return a text summary of multiple enrollments."""
        s = ""
        for e in enrollments:
            s += e.summary(tabs + 1)
        return s


class EnrollmentDetailSchema(EnrollmentSchema):
    """Schema for an enrollment with leftover bundles."""

    leftover_bundles: list[Bundle]
