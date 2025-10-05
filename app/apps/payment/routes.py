import logging
from decimal import Decimal

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi_mongo_base.core.exceptions import BaseHTTPException
from fastapi_mongo_base.utils import usso_routes
from ufaas.services import AccountingClient

from apps.tenant.models import Tenant
from server.config import Settings
from utils.schemas import RedirectUrlSchema
from utils.texttools import add_query_params
from utils.wallets import get_wallets

from .models import Payment
from .schemas import (
    PaymentCreateSchema,
    PaymentRetrieveSchema,
    PaymentSchema,
    PaymentStatus,
)
from .services import (
    create_proposal,
    start_payment,
    verify_payment,
)


class PaymentRouter(usso_routes.AbstractTenantUSSORouter):
    model = Payment
    schema = PaymentSchema

    # async def get_user(self, request: Request, **kwargs: object) -> UserData:
    #     usso = utils.usso.get_usso()
    #     return usso(request)

    def config_schemas(self, schema: type, **kwargs: object) -> None:
        super().config_schemas(schema)
        self.create_request_schema = PaymentCreateSchema
        self.retrieve_response_schema = PaymentRetrieveSchema

    def config_routes(self, **kwargs: object) -> None:
        super().config_routes(update_route=False, delete_route=False, **kwargs)
        self.router.add_api_route(
            "/start",
            self.start_direct_payment,
            methods=["GET"],
            # response_model=self.retrieve_response_schema,
        )
        self.router.add_api_route(
            "/{uid}/start",
            self.start_payment,
            methods=["GET"],
            # response_model=self.retrieve_response_schema,
        )
        self.router.add_api_route(
            "/{uid}/start",
            self.start_payment_url,
            methods=["POST"],
            response_model=RedirectUrlSchema,
        )
        self.router.add_api_route(
            "/{uid}/verify",
            self.verify_payment,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{uid}/verify",
            self.verify_payment,
            methods=["POST"],
        )

    async def retrieve_item(self, request: Request, uid: str) -> PaymentRetrieveSchema:
        user = await self.get_user(request)
        item: Payment = await self.get_item(uid, tenant_id=user.tenant_id)
        if user.user_id:
            async with AccountingClient(user.tenant_id) as client:
                wallets = await get_wallets(client, user.user_id)
        else:
            wallets = None
        return self.retrieve_response_schema(
            **item.model_dump(), ipgs=item.available_ipgs, wallets=wallets
        )

    async def create_item(
        self, request: Request, data: PaymentCreateSchema
    ) -> PaymentSchema:
        user = await self.get_user(request)
        tenant = await Tenant.get_by_tenant_id(user.tenant_id)

        if "currency" not in data.model_fields_set:
            data.currency = Settings.currency

        if not data.available_ipgs:
            data.available_ipgs = tenant.ipgs

        if data.user_id:
            await self.authorize(
                action="create",
                user=user,
                filter_data=data.model_dump(exclude_none=True),
            )

        item = Payment(
            tenant_id=user.tenant_id,
            user_id=data.user_id or user.user_id,
            **data.model_dump(exclude=["user_id"]),
        )
        await item.save()
        return item

        # return await super().create_item(request, item.model_dump())

    async def start_direct_payment(
        self,
        request: Request,
        wallet_id: str,
        amount: Decimal,
        description: str,
        callback_url: str,
    ) -> dict:
        payment: Payment = await self.create_item(
            request,
            PaymentCreateSchema(
                wallet_id=wallet_id,
                amount=amount,
                description=description,
                callback_url=callback_url,
            ),
        )
        return await self.start_payment(request, payment.uid)

    async def start_payment_url(
        self,
        request: Request,
        uid: str,
        ipg: str | None = None,
        amount: Decimal | None = None,
    ) -> RedirectUrlSchema:
        user = await self.get_user(request)
        item: Payment = await self.get_item(uid, tenant_id=user.tenant_id)

        if ipg is None:
            ipg = item.available_ipgs[0]

        start_data = await start_payment(
            payment=item,
            tenant_id=user.tenant_id,
            ipg=ipg,
            amount=amount,
            user_id=item.user_id,
            phone=user.phone if user else None,
        )

        if start_data["status"]:
            return RedirectUrlSchema(redirect_url=start_data["url"])

        raise BaseHTTPException(status_code=400, **start_data)

    async def start_payment(
        self,
        request: Request,
        uid: str,
        ipg: str | None = None,
        amount: Decimal | None = None,
    ) -> RedirectResponse:
        redirect_dict = await self.start_payment_url(request, uid, ipg, amount)
        return RedirectResponse(url=redirect_dict.redirect_url)

    async def verify_payment(
        self,
        request: Request,
        uid: str,
    ) -> RedirectResponse:
        user = await self.get_user(request)

        item: Payment = await self.get_item(uid, tenant_id=user.tenant_id)
        payment_status = item.status

        payment: Payment = await verify_payment(tenant_id=user.tenant_id, payment=item)
        payment_redirect_url = add_query_params(
            payment.callback_url,
            {"payment_id": payment.uid, "status": payment.status.value},
        )

        if payment.status == PaymentStatus.PENDING:
            return RedirectResponse(url=payment_redirect_url, status_code=303)
            # return proper response
            return payment
        if payment.status == PaymentStatus.SUCCESS:
            if payment_status == PaymentStatus.PENDING:
                await create_proposal(payment)
            else:
                logging.info("payment was not pending %s", payment_status)

        return RedirectResponse(url=payment_redirect_url, status_code=303)


router = PaymentRouter().router
