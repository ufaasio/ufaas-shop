from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Self

from fastapi_mongo_base.schemas import TenantUserEntitySchema
from fastapi_mongo_base.utils.bsontools import decimal_amount
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# from .schemas import Bundle, EnrollmentSchema


class Bundle(BaseModel):
    asset: str
    quota: Decimal
    order: Literal[0, 1, 2] = 1
    unit: str | None = None
    meta_data: dict | None = None

    model_config = ConfigDict(allow_inf_nan=True)

    @field_validator("quota", mode="before")
    @classmethod
    def validate_quota(cls, value: Decimal) -> Decimal:
        return decimal_amount(value)


class AcquisitionType(StrEnum):
    trial = "trial"
    # credit = "credit"
    purchased = "purchased"
    gifted = "gifted"
    # deferred = "deferred"
    promotion = "promotion"
    # subscription = "subscription"
    # on_demand = "on_demand"
    borrowed = "borrowed"
    # freemium = "freemium"
    postpaid = "postpaid"

    @classmethod
    def normal_types(cls) -> list[str]:
        return [
            cls.trial,
            cls.purchased,
            cls.gifted,
            cls.promotion,
            # cls.borrowed,
            cls.postpaid,
        ]


class EnrollmentCreateSchema(BaseModel):
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
        if self.expire_at and self.duration:
            raise ValueError(
                "Only one of expire_at or duration_days should be provided"
            )
        # if self.duration:
        #     self.expire_at = self.start_at + timedelta(days=self.duration)
        #     # self.duration = None

        return self

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, value: Decimal) -> Decimal:
        return decimal_amount(value)

    @field_validator("bundles", mode="after")
    @classmethod
    def validate_bundles(cls, value: list[Bundle]) -> list[Bundle]:
        if not value:
            raise ValueError("Bundles are required")
        return value


class EnrollmentSchema(EnrollmentCreateSchema, TenantUserEntitySchema):
    # price: Decimal = Decimal(0)
    # acquisition_type: AcquisitionType = AcquisitionType.purchased
    # invoice_id: str | None = None
    # start_at: datetime = Field(default_factory=datetime.now)
    # expire_at: datetime | None = None
    # duration: int | None = None
    # status: Literal["active", "inactive"] = "active"

    # bundles: list[Bundle]
    # variant: str | None = None

    # due_date: datetime | None = None
    paid_at: datetime | None = None

    @model_validator(mode="after")
    def validate_duration(self) -> Self:
        return self

    @model_validator(mode="after")
    def validate_due_date(self) -> Self:
        if self.acquisition_type == AcquisitionType.borrowed and not self.due_date:
            raise ValueError("Due date must be provided for borrowed acquisitions")
        if self.acquisition_type == AcquisitionType.borrowed:
            self.paid_at = False if self.paid_at is None else self.paid_at
        return self

    def summary(self, tabs: int = 0) -> str:
        now = datetime.now()
        exp = (self.expire_at - now).seconds if self.expire_at else "inf"
        s = f"{'\t' * tabs}{self.uid}: ({self.variant}) {exp} ["
        for b in self.bundles:
            s += f"({b.asset}: {b.quota}) "
        s += "]\n"
        return s

    @classmethod
    def summaries(cls, enrollments: list[Self], tabs: int = 0) -> str:
        s = ""
        for e in enrollments:
            s += e.summary(tabs + 1)
        return s


class EnrollmentDetailSchema(EnrollmentSchema):
    leftover_bundles: list[Bundle]
