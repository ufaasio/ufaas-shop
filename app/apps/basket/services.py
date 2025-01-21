import asyncio
import json
import logging
import uuid
from datetime import datetime

from fastapi_mongo_base.core.exceptions import BaseHTTPException
from fastapi_mongo_base.utils import aionetwork
from json_advanced import dumps
from ufaas.apps.saas.schemas import EnrollmentCreateSchema, EnrollmentSchema
from ufaas.schemas import WalletSchema
from ufaas_fastapi_business.models import Business

from .models import Basket
from .schemas import BasketStatusEnum, DiscountSchema, ItemType


async def reserve_basket(basket: Basket):
    reserve_tasks = []
    for item in basket.items.values():
        if item.reserve_url:
            reserve_tasks.append(item.reserve_product())

    asyncio.gather(*reserve_tasks)
    basket.status = "reserved"

    await basket.save()


async def validate_basket(basket: Basket):
    for item in basket.items.values():
        if not await item.validate_product():
            raise ValueError("Product validation failed")


async def webhook_basket(basket: Basket):
    for item in basket.items.values():
        await item.webhook_product()


async def cancel_basket(basket: Basket):
    basket.status = "cancel"
    await basket.save()

    for item in basket.items.values():
        await item.webhook_product()


async def get_wallets(business: Business, user_id: uuid.UUID) -> list[WalletSchema]:
    wallets = await aionetwork.aio_request(
        url=f"{business.config.core_url}api/v1/wallets/",
        params={"user_id": str(user_id), "limit": 100},
        headers={
            "Authorization": f"Bearer {await business.get_access_token()}",
            "Accept-Encoding": "identity",
        },
    )

    return (
        [WalletSchema(**wallet) for wallet in wallets.get("items")] if wallets else None
    )


async def get_default_wallet(business: Business, user_id: uuid.UUID) -> WalletSchema:
    wallets = await get_wallets(business, user_id)
    for wallet in wallets:
        if wallet.is_default:
            return wallet

    raise ValueError("No default wallet found")


# @basic.try_except_wrapper
async def create_payment_detail(basket: Basket, business: Business):
    wallet = await get_default_wallet(business, basket.user_id)
    # TODO make payment detail a model
    payment_detail = json.loads(
        dumps(
            {
                "user_id": basket.user_id,
                "wallet_id": wallet.uid,
                "basket_id": basket.uid,
                "amount": basket.subtotal,
                "description": basket.description,
                "currency": basket.currency,
                "callback_url": f"{business.config.core_url}api/v1/apps/basket/baskets/{basket.uid}/validate",
            }
        )
    )
    payment = await aionetwork.aio_request(
        method="POST",
        url=f"{business.config.core_url}api/v1/apps/cashier/payments/",
        headers={
            "Authorization": f"Bearer {await business.get_access_token()}",
            "Accept-Encoding": "identity",
        },
        json=payment_detail,
    )
    return payment


async def checkout_basket(
    basket: Basket,
    business: Business,
    callback_url: str | None = None,
):
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

    # TODO check all items in basket
    # await validate_basket(basket)
    # TODO reserve items
    # await reserve_basket(basket)

    payment = await create_payment_detail(basket, business)
    logging.info(f"{payment=}")

    payment_uid = payment.get("uid")
    basket.payment_detail_url = (
        f"{business.config.core_url}api/v1/apps/cashier/payments/{payment_uid}"
    )
    basket.status = "locked"
    await basket.save()

    # TODO connect to frontend

    return basket.payment_detail_url


async def purchase_basket_saas(basket: Basket, business: Business):
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
            logging.info(f"{enrollment_data=}")
            enrollment = await aionetwork.aio_request(
                method="POST",
                url=f"{business.config.core_url}api/v1/apps/saas/enrollments/",
                headers={
                    "Authorization": f"Bearer {await business.get_access_token()}",
                    "Accept-Encoding": "identity",
                },
                json=enrollment_data.model_dump(mode="json"),
            )
            enrollment = EnrollmentSchema(**enrollment)


async def validate_basket(basket: Basket, business: Business):
    # TODO Check if basket is locked
    if basket.status != "locked":
        raise BaseHTTPException(
            400,
            "invalid_status",
            f"Basket is not locked. Basket status: {basket.status.value}",
        )

    payment = await aionetwork.aio_request(
        url=basket.payment_detail_url,
        headers={
            "Authorization": f"Bearer {await business.get_access_token()}",
            "Accept-Encoding": "identity",
        },
    )
    if payment["status"] != "SUCCESS":
        raise BaseHTTPException(
            400, "invalid_status", f"Payment is not successful. {payment['status']}"
        )

    # TODO webhook basket
    await webhook_basket(basket)

    # TODO purchase basket saas
    await purchase_basket_saas(basket, business)

    # TODO checkout_at from payment
    basket.checkout_at = datetime.now()
    basket.status = "paid"
    await basket.save()

    return payment


async def apply_discount(basket: Basket, discount_code: str) -> Basket:
    from apps.voucher.models import Voucher
    from apps.voucher.schemas import VoucherStatus

    voucher = await Voucher.get_by_code(basket.business_name, discount_code)
    if not voucher:
        return basket

    if voucher.status != VoucherStatus.ACTIVE:
        return basket

    if basket.discount:
        prev_discount = await Voucher.get_by_code(
            basket.business_name, basket.discount.code
        )
        prev_discount.redeemed -= 1
        await prev_discount.save()

    discount_value = voucher.calculate_discount(basket.amount)
    basket.discount = DiscountSchema(
        code=voucher.code, discount=discount_value, user_id=basket.user_id
    )
    await basket.save()

    voucher.redeemed += 1
    await voucher.save()

    return basket
