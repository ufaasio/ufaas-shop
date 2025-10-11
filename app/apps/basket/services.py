import asyncio
import logging

from fastapi_mongo_base.core.exceptions import BaseHTTPException
from ufaas.services import AccountingClient

from apps.payment.models import Payment, PaymentStatus
from apps.tenant.models import Tenant
from server.config import Settings
from utils.saas import AcquisitionType, EnrollmentCreateSchema, EnrollmentSchema
from utils.wallets import get_or_create_user_wallet

from .models import Basket
from .schemas import (
    BasketItemSchema,
    BasketStatusEnum,
    DiscountSchema,
    ItemType,
    VoucherSchema,
)

# from ufaas.apps.saas.schemas import EnrollmentCreateSchema, EnrollmentSchema


async def reserve_basket(basket: Basket, *, save: bool = True) -> Basket:
    reserve_tasks = [item.reserve_product() for item in basket.items.values()]
    asyncio.gather(*reserve_tasks)
    basket.status = BasketStatusEnum.reserved
    if save:
        return await basket.save()
    return basket


async def buy_basket(basket: Basket, *, save: bool = True) -> Basket:
    buy_tasks = [item.buy_product() for item in basket.items.values()]
    asyncio.gather(*buy_tasks)
    basket.status = BasketStatusEnum.paid
    await purchase_basket_saas(basket, basket.tenant_id)
    if save:
        return await basket.save()
    return basket


async def cancel_basket(basket: Basket, *, save: bool = True) -> Basket:
    release_tasks = [item.release_product() for item in basket.items.values()]
    await asyncio.gather(*release_tasks)
    basket.status = BasketStatusEnum.cancelled
    if save:
        return await basket.save()
    return basket


async def create_basket_payment(
    basket: Basket, callback_url: str | None = None
) -> Payment:
    async with AccountingClient(basket.tenant_id) as client:
        await client.get_token([
            "create:finance/accounting/wallet",
            "create:finance/cashier/payment",
        ])
        wallet = await get_or_create_user_wallet(client, basket.user_id)
        tenant = await Tenant.get_by_tenant_id(basket.tenant_id)

        callback_url = (
            f"{Settings.core_url}{Settings.base_path}/baskets/{basket.uid}/validate"
        )
        payment = await Payment(
            tenant_id=basket.tenant_id,
            user_id=basket.user_id,
            wallet_id=wallet.uid,
            basket_id=basket.uid,
            amount=basket.amount,
            currency=basket.currency,
            description=basket.description,
            callback_url=callback_url,
            available_ipgs=tenant.ipgs,
            accept_wallet=True,
            voucher_code=basket.voucher.code if basket.voucher else None,
        ).save()
    return payment


async def create_checkout_basket_url(
    basket: Basket,
    callback_url: str | None = None,
) -> str:
    if basket.status in [BasketStatusEnum.locked, BasketStatusEnum.reserved]:
        if not basket.payment_detail_url:
            raise BaseHTTPException(400, "invalid_payment", "Payment not found")
        return basket.payment_detail_url
    if basket.status != BasketStatusEnum.active:
        raise BaseHTTPException(
            400,
            "invalid_status",
            f"Basket is not active. Basket status: {basket.status.value}",
        )
    if callback_url is not None:
        basket.callback_url = callback_url
        await basket.save()

    await reserve_basket(basket, save=False)

    payment = await create_basket_payment(basket, callback_url)
    basket.payment_id = payment.uid
    basket.status = BasketStatusEnum.locked
    await basket.save()
    return f"{basket.payment_detail_url}/start"


async def create_saas_enrollment(
    client: AccountingClient, basket: Basket, item: BasketItemSchema
) -> EnrollmentSchema | None:
    if item.item_type != ItemType.saas_package or not item.bundles:
        return None
    enrollment_data = EnrollmentCreateSchema(
        user_id=basket.user_id,
        bundles=item.bundles,
        price=item.unit_price,
        invoice_id=basket.invoice_id,
        # start_at=,
        duration=item.plan_duration,
        status="active",
        acquisition_type=AcquisitionType.purchased,
    )
    logging.info("enrollment_data %s", enrollment_data)
    enrollment_response = await client.post(
        url=f"{Settings.core_url}/api/saas/v1/enrollments",
        json=enrollment_data.model_dump(mode="json"),
    )
    enrollment_response.raise_for_status()
    enrollment = EnrollmentSchema.model_validate(enrollment_response.json())
    return enrollment


async def purchase_basket_saas(
    basket: Basket, tenant_id: str
) -> list[EnrollmentSchema]:
    try:
        async with AccountingClient(tenant_id) as client:
            await client.get_token("create:finance/saas/enrollment")
            enrollments = await asyncio.gather(*[
                create_saas_enrollment(client, basket, item)
                for item in basket.items.values()
            ])
            return [enrollment for enrollment in enrollments if enrollment]
    except Exception:
        logging.exception("Error purchasing basket saas")
        raise


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


async def validate_basket(basket: Basket) -> None:
    if not basket.payment_id:
        raise BaseHTTPException(400, "invalid_payment", "Payment not found")

    payment = await Payment.get_item(
        uid=basket.payment_id, tenant_id=basket.tenant_id, user_id=basket.user_id
    )

    if payment is None:
        raise BaseHTTPException(404, "invalid_payment", "Payment not found")
    if payment.status != PaymentStatus.SUCCESS:
        raise BaseHTTPException(400, "invalid_payment", "Payment is not successful")
