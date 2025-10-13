from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from fastapi_mongo_base.schemas import (
    BaseEntitySchema,
)
from pydantic import (
    BaseModel,
)
from ufaas.services import AccountingClient

from server.config import Settings


class PaymentStatus(StrEnum):
    INIT = "INIT"
    PENDING = "PENDING"
    FAILED = "FAILED"
    SUCCESS = "SUCCESS"
    REFUNDED = "REFUNDED"

    def is_open(self) -> bool:
        return self in [PaymentStatus.INIT, PaymentStatus.PENDING]


class PaymentSchema(BaseEntitySchema):
    ipg: str
    user_id: str | None = None

    phone: str | None = None

    status: PaymentStatus = PaymentStatus.INIT

    failure_reason: str | None = None
    verified_at: datetime | None = None


class IPGPaymentSchema(BaseModel):
    user_id: str | None = None
    wallet_id: str
    amount: Decimal

    phone: str | None = None
    description: str  # | None = None
    callback_url: str

    status: PaymentStatus = PaymentStatus.INIT


def get_payment_ipg_url(ipg: str) -> str:
    return f"{Settings.core_url}/api/{ipg}/v1/payments"


async def create_payment(
    tenant_id: str, ipg: str, ipg_schema: IPGPaymentSchema
) -> PaymentSchema:
    payment_ipg_url = get_payment_ipg_url(ipg)
    async with AccountingClient(tenant_id) as client:
        await client.get_token("create:finance/ipg/payment")
        response = await client.post(
            url=payment_ipg_url, json=ipg_schema.model_dump(mode="json")
        )
        response.raise_for_status()

    return PaymentSchema.model_validate(response.json() | {"ipg": ipg})
