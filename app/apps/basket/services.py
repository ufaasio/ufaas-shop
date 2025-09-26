import asyncio
import json
import logging
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
import json_advanced
from fastapi_mongo_base.core.exceptions import BaseHTTPException
from ufaas.services import AccountingClient
from ufaas.wallet import WalletSchema

from server.config import Settings

from .models import Basket
from .schemas import BasketStatusEnum, DiscountSchema, ItemType, VoucherSchema

# from ufaas.apps.saas.schemas import EnrollmentCreateSchema, EnrollmentSchema


def add_query_params(url: str, new_params: dict) -> str:
    parsed = urlparse(url)
    existing_params = parse_qs(parsed.query)
    flat_params = {k: v[0] for k, v in existing_params.items()}
    flat_params.update(new_params)
    query = urlencode(flat_params)
    new_url = urlunparse(parsed._replace(query=query))
    return new_url


async def reserve_basket(basket: Basket) -> None:
    reserve_tasks = [
        item.reserve_product() for item in basket.items.values() if item.reserve_url
    ]

    asyncio.gather(*reserve_tasks)
    basket.status = "reserved"

    await basket.save()


async def validate_basket(basket: Basket) -> None:
    for item in basket.items.values():
        if not await item.validate_product():
            raise ValueError("Product validation failed")


async def webhook_basket(basket: Basket) -> None:
    for item in basket.items.values():
        await item.webhook_product()


async def cancel_basket(basket: Basket) -> None:
    basket.status = "cancel"
    await basket.save()

    for item in basket.items.values():
        await item.webhook_product()


async def get_default_wallet(tenant_id: str, user_id: str) -> WalletSchema:
    async with AccountingClient(tenant_id) as client:
        wallet = await client.get_wallet(user_id)
        return wallet


async def create_payment_detail(
    basket: Basket, tenant_id: str, callback_url: str | None = None
) -> dict:
    wallet = await get_default_wallet(tenant_id, basket.user_id)
    callback_url = (
        f"{business.config.core_url}api/basket/v1/baskets/{basket.uid}/validate"
    )
    payment_detail = json.loads(
        json_advanced.dumps({
            "user_id": basket.user_id,
            "wallet_id": wallet.uid,
            "basket_id": basket.uid,
            "amount": basket.amount,
            "description": basket.description,
            "currency": basket.currency,
            "callback_url": callback_url,
        })
    )
    async with httpx.AsyncClient() as client:
        payment = await client.post(
            f"{business.config.core_url}api/cashier/v1/payments/",
            headers={
                "Authorization": f"Bearer {await business.get_access_token()}",
                "Accept-Encoding": "identity",
            },
            json=payment_detail,
        )
    return payment


async def checkout_basket(
    basket: Basket,
    tenant_id: str,
    callback_url: str | None = None,
) -> dict:
    # TODO Check if basket is active
    if basket.status in [BasketStatusEnum.locked, BasketStatusEnum.reserved]:
        return basket.payment_detail_url
    if basket.status != "active":
        raise BaseHTTPException(
            400,
            "invalid_status",
            f"Basket is not active. Basket status: {basket.status.value}",
        )
    if callback_url is not None:
        basket.callback_url = callback_url
        await basket.save()

    logging.info("%s", basket.callback_url)

    # TODO check all items in basket
    # await validate_basket(basket)
    # TODO reserve items
    # await reserve_basket(basket)

    payment = await create_payment_detail(basket, tenant_id, callback_url)
    logging.info("%s", payment)

    payment_uid = payment.get("uid")
    basket.payment_detail_url = (
        f"{tenant_id}{Settings.base_path}/payments/{payment_uid}"
    )
    basket.status = "locked"
    await basket.save()

    # TODO connect to frontend

    return basket.payment_detail_url


async def purchase_basket_saas(basket: Basket, tenant_id: str) -> None:
    for item in basket.items.values():
        if item.item_type == ItemType.saas_package:
            enrollment_data = EnrollmentCreateSchema(
                user_id=basket.user_id,
                bundles=item.bundles,
                price=item.unit_price,
                invoice_id=basket.invoice_id,
                # start_at=,
                duration=item.plan_duration,
                status="active",
                acquisition_type="purchased",
            )
            logging.info("%s", enrollment_data)
            async with httpx.AsyncClient() as client:
                enrollment = await client.post(
                    url=f"{tenant_id}{Settings.base_path}/enrollments/",
                    headers={
                        "Authorization": f"Bearer {await tenant_id.get_access_token()}",
                        "Accept-Encoding": "identity",
                    },
                    json=enrollment_data.model_dump(mode="json"),
                )
            enrollment = EnrollmentSchema(**enrollment)


async def apply_discount(basket: Basket, voucher_code: VoucherSchema | None) -> Basket:
    from apps.voucher.models import Voucher
    from apps.voucher.schemas import VoucherStatus

    if not voucher_code:
        return basket

    discount_code = voucher_code.code
    if basket.discount:
        prev_discount = await Voucher.get_by_code(
            basket.tenant_id, basket.discount.code
        )
        if prev_discount:
            prev_discount.redeemed -= 1
            await prev_discount.save()

    if not discount_code:
        basket.discount = None
        await basket.save()
        return basket

    logging.info(
        "Applying discount %s to basket %s %s",
        discount_code,
        basket.uid,
        basket.user_id,
    )

    voucher: Voucher | None = await Voucher.get_by_code(
        basket.tenant_id, discount_code, basket.user_id
    )
    if not voucher:
        logging.error("Voucher %s not found for user %s", discount_code, basket.user_id)
        raise BaseHTTPException(
            404, "invalid_voucher", f"Voucher {discount_code} not found for user"
        )

    if voucher.status != VoucherStatus.ACTIVE:
        return basket

    # TODO check if voucher is limited products
    discount_value = voucher.calculate_discount(basket.subtotal)
    basket.discount = DiscountSchema(
        code=voucher.code, discount=discount_value, user_id=basket.user_id
    )
    await basket.save()

    voucher.redeemed += 1
    await voucher.save()

    return basket
