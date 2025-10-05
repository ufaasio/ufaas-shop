import asyncio
import logging
from decimal import Decimal

from fastapi_mongo_base.core.exceptions import BaseHTTPException
from ufaas.proposal import ProposalSchema
from ufaas.services import AccountingClient

from apps.tenant.models import Tenant
from server.config import Settings
from utils.ipg import create_purchase, get_purchase_ipg_url

from .models import Payment
from .schemas import (
    IPGPurchaseSchema,
    PurchaseSchema,
    PurchaseStatus,
)


async def payments_options(payment: Payment) -> list[str]:
    tenant = await Tenant.get_by_tenant_id(payment.tenant_id)
    return tenant.ipgs


async def start_payment(
    payment: Payment,
    tenant_id: str,
    ipg: str,
    *,
    amount: Decimal | None = None,
    user_id: str | None = None,
    phone: str | None = None,
    **kwargs: object,
) -> dict:
    if payment.is_overdue():
        await payment.fail("Payment is overdue")
        return {
            "status": False,
            "message": "Payment is overdue",
            "error": "payment_overdue",
        }

    if amount is None:
        amount = payment.amount

    if not payment.status.is_open():
        return {
            "status": False,
            "message": f"Payment was {payment.status}",
            "error": "invalid_payment",
        }

    callback_url = (
        f"{Settings.core_url}{Settings.base_path}/payments/{payment.uid}/verify"
    )

    if amount == 0:
        return {"status": True, "uid": payment.uid, "url": callback_url}

    ipg_schema = IPGPurchaseSchema(
        user_id=user_id,
        wallet_id=payment.wallet_id,
        amount=amount,
        description=payment.description,
        callback_url=callback_url,
        phone=phone,
    )
    logging.info("IPGPurchaseSchema: %s", ipg_schema)

    purchase = await create_purchase(tenant_id, ipg, ipg_schema)
    payment.tries[purchase.uid] = purchase
    payment.status = PurchaseStatus.PENDING
    await payment.save()
    return {
        "status": True,
        "uid": payment.uid,
        "url": f"{get_purchase_ipg_url(ipg)}/{purchase.uid}/start",
    }


async def verify_purchase(
    client: AccountingClient, purchase_trials: PurchaseSchema
) -> PurchaseStatus:
    if not purchase_trials.status.is_open():
        return purchase_trials.status

    url = "/".join([
        get_purchase_ipg_url(purchase_trials.ipg),
        purchase_trials.uid,
    ])

    response = await client.get(url=url)
    response.raise_for_status()
    purchase = PurchaseSchema(**response.json(), ipg=purchase_trials.ipg)
    return purchase.status


async def verify_payment(tenant_id: str, payment: Payment, **kwargs: object) -> Payment:
    # if payment.status in ["SUCCESS", "FAILED"]:
    #     return payment

    if payment.amount == 0:
        return await payment.success(None)

    async with AccountingClient(tenant_id) as client:
        await client.get_token("read:finance/ipg/purchase")

        purchase_statuses = await asyncio.gather(*[
            verify_purchase(client, purchase_trials)
            for purchase_trials in payment.tries.values()
        ])

    for purchase_trial, purchase_status in zip(
        payment.tries.values(), purchase_statuses, strict=True
    ):
        if purchase_status == PurchaseStatus.SUCCESS:
            await payment.success_purchase(purchase_trial.uid, save=False)
        elif purchase_status == PurchaseStatus.FAILED:
            await payment.fail_purchase(purchase_trial.uid, save=False)

    return await payment.save()


async def create_proposal(payment: Payment) -> ProposalSchema | None:
    tenant_id = payment.tenant_id

    if payment.amount == 0:
        return

    async with AccountingClient(tenant_id) as client:
        wallet = await client.get_wallet(payment.wallet_id)

        balance = wallet.balance.get(payment.currency)
        if not balance or balance.available < payment.amount:
            available = balance.available if balance else 0
            logging.error(
                "insufficient_funds: amount=%s\navailable balance=%s (out of %s)",
                payment.amount,
                available,
                balance.total if balance else 0,
            )
            raise BaseHTTPException(
                status_code=402,
                error="insufficient_funds",
                detail=(
                    "Not enough available balance in the wallet: "
                    f"needed={payment.amount} available={available}"
                ),
            )

        tenant = await Tenant.find_one({"tenant_id": payment.tenant_id})

        proposal = await client.create_proposal(
            from_wallet_id=payment.wallet_id,
            to_wallet_id=tenant.wallet_id,
            currency=payment.currency,
            amount=payment.amount,
            description=payment.description,
        )
    return proposal
