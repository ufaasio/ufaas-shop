import asyncio
import logging
from decimal import Decimal

from fastapi_mongo_base.core.exceptions import BaseHTTPException
from ufaas.proposal import ProposalSchema
from ufaas.services import AccountingClient

from apps.tenant.models import Tenant
from server.config import Settings
from utils.ipg import (
    IPGPaymentSchema,
    PaymentSchema,
    PaymentStatus,
    create_payment,
    get_payment_ipg_url,
)

from .models import Purchase


async def purchases_options(purchase: Purchase) -> list[str]:
    tenant = await Tenant.get_by_tenant_id(purchase.tenant_id)
    return tenant.ipgs


async def start_purchase(
    purchase: Purchase,
    tenant_id: str,
    ipg: str,
    *,
    amount: Decimal | None = None,
    user_id: str | None = None,
    phone: str | None = None,
    **kwargs: object,
) -> dict:
    if purchase.is_overdue():
        await purchase.fail("Purchase is overdue")
        return {
            "status": False,
            "message": "Purchase is overdue",
            "error": "purchase_overdue",
        }

    if amount is None:
        amount = purchase.amount

    if not purchase.status.is_open():
        return {
            "status": False,
            "message": f"Purchase was {purchase.status}",
            "error": "invalid_purchase",
        }

    callback_url = (
        f"{Settings.core_url}{Settings.base_path}/purchases/{purchase.uid}/verify"
    )

    if amount == 0:
        return {"status": True, "uid": purchase.uid, "url": callback_url}

    ipg_schema = IPGPaymentSchema(
        user_id=user_id,
        wallet_id=purchase.wallet_id,
        amount=amount,
        description=purchase.description,
        callback_url=callback_url,
        phone=phone,
    )
    logging.info("IPGPaymentSchema: %s", ipg_schema)

    payment: PaymentSchema = await create_payment(tenant_id, ipg, ipg_schema)
    purchase.tries[payment.uid] = payment
    purchase.status = PaymentStatus.PENDING
    await purchase.save()
    return {
        "status": True,
        "uid": purchase.uid,
        "url": f"{get_payment_ipg_url(ipg)}/{payment.uid}/start",
    }


async def verify_payment(
    client: AccountingClient, payment_trials: PaymentSchema
) -> PaymentStatus:
    if not payment_trials.status.is_open():
        return payment_trials.status

    url = "/".join([
        get_payment_ipg_url(payment_trials.ipg),
        payment_trials.uid,
    ])

    response = await client.get(url=url)
    response.raise_for_status()
    payment = PaymentSchema(**response.json(), ipg=payment_trials.ipg)
    return payment.status


async def verify_purchase(
    tenant_id: str, purchase: Purchase, **kwargs: object
) -> Purchase:
    # if purchase.status in ["SUCCESS", "FAILED"]:
    #     return purchase

    if purchase.amount == 0:
        return await purchase.success(None)

    async with AccountingClient(tenant_id) as client:
        await client.get_token("read:finance/ipg/payment")

        payment_statuses = await asyncio.gather(*[
            verify_payment(client, payment_trials)
            for payment_trials in purchase.tries.values()
        ])

    for payment_trial, payment_status in zip(
        purchase.tries.values(), payment_statuses, strict=True
    ):
        if payment_status == PaymentStatus.SUCCESS:
            await purchase.success_payment(payment_trial.uid, save=False)
        elif payment_status == PaymentStatus.FAILED:
            await purchase.fail_payment(payment_trial.uid, save=False)

    return await purchase.save()


async def create_proposal(purchase: Purchase) -> ProposalSchema | None:
    tenant_id = purchase.tenant_id

    if purchase.amount == 0:
        return

    async with AccountingClient(tenant_id) as client:
        wallet = await client.get_wallet(purchase.wallet_id)

        balance = wallet.balance.get(purchase.currency)
        if not balance or balance.available < purchase.amount:
            available = balance.available if balance else 0
            logging.error(
                "insufficient_funds: amount=%s\navailable balance=%s (out of %s)",
                purchase.amount,
                available,
                balance.total if balance else 0,
            )
            raise BaseHTTPException(
                status_code=402,
                error="insufficient_funds",
                detail=(
                    "Not enough available balance in the wallet: "
                    f"needed={purchase.amount} available={available}"
                ),
            )

        tenant = await Tenant.find_one({"tenant_id": purchase.tenant_id})

        proposal = await client.create_proposal(
            from_wallet_id=purchase.wallet_id,
            to_wallet_id=tenant.wallet_id,
            currency=purchase.currency,
            amount=purchase.amount,
            description=purchase.description,
        )
    return proposal
