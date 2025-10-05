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


class PurchaseStatus(StrEnum):
    INIT = "INIT"
    PENDING = "PENDING"
    FAILED = "FAILED"
    SUCCESS = "SUCCESS"
    REFUNDED = "REFUNDED"

    def is_open(self) -> bool:
        return self in [PurchaseStatus.INIT, PurchaseStatus.PENDING]


class PurchaseSchema(BaseEntitySchema):
    ipg: str
    user_id: str | None = None

    phone: str | None = None

    status: PurchaseStatus = PurchaseStatus.INIT

    failure_reason: str | None = None
    verified_at: datetime | None = None


class IPGPurchaseSchema(BaseModel):
    user_id: str | None = None
    wallet_id: str
    amount: Decimal

    phone: str | None = None
    description: str  # | None = None
    callback_url: str

    status: PurchaseStatus = PurchaseStatus.INIT


def get_purchase_ipg_url(ipg: str) -> str:
    return f"{Settings.core_url}/api/{ipg}/v1/purchases"


async def create_purchase(
    tenant_id: str, ipg: str, ipg_schema: IPGPurchaseSchema
) -> PurchaseSchema:
    purchase_ipg_url = get_purchase_ipg_url(ipg)
    async with AccountingClient(tenant_id) as client:
        await client.get_token("create:finance/ipg/purchase")
        response = await client.post(
            url=purchase_ipg_url, json=ipg_schema.model_dump(mode="json")
        )
        response.raise_for_status()

    return PurchaseSchema.model_validate(response.json() | {"ipg": ipg})
