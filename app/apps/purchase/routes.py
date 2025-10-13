import logging
from decimal import Decimal

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi_mongo_base.core.exceptions import BaseHTTPException
from fastapi_mongo_base.utils import usso_routes
from ufaas.services import AccountingClient
from usso import UserData

from apps.tenant.models import Tenant
from server.config import Settings
from utils.currency import Currency
from utils.schemas import RedirectUrlSchema
from utils.texttools import add_query_params
from utils.usso import get_usso
from utils.wallets import get_wallets

from .models import Purchase
from .schemas import (
    PurchaseCreateSchema,
    PurchaseRetrieveSchema,
    PurchaseSchema,
    PurchaseStatus,
)
from .services import (
    create_proposal,
    start_purchase,
    verify_purchase,
)


class PurchaseRouter(usso_routes.AbstractTenantUSSORouter):
    model = Purchase
    schema = PurchaseSchema

    def get_user_or_none(self, request: Request, **kwargs: object) -> UserData | None:
        usso = get_usso(raise_exception=False)
        return usso(request)

    def config_schemas(self, schema: type, **kwargs: object) -> None:
        super().config_schemas(schema)
        self.create_request_schema = PurchaseCreateSchema
        self.retrieve_response_schema = PurchaseRetrieveSchema

    def config_routes(self, **kwargs: object) -> None:
        super().config_routes(update_route=False, delete_route=False, **kwargs)
        self.router.add_api_route(
            "/start",
            self.start_direct_purchase,
            methods=["GET"],
            # response_model=self.retrieve_response_schema,
        )
        self.router.add_api_route(
            "/{uid}/start",
            self.start_purchase,
            methods=["GET"],
            # response_model=self.retrieve_response_schema,
        )
        self.router.add_api_route(
            "/{uid}/start",
            self.start_purchase_url,
            methods=["POST"],
            response_model=RedirectUrlSchema,
        )
        self.router.add_api_route(
            "/{uid}/verify",
            self.verify_purchase,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{uid}/verify",
            self.verify_purchase,
            methods=["POST"],
        )

    async def retrieve_item(self, request: Request, uid: str) -> PurchaseRetrieveSchema:
        user = await self.get_user(request)
        item: Purchase = await self.get_item(uid, tenant_id=user.tenant_id)
        if user.user_id:
            async with AccountingClient(user.tenant_id) as client:
                wallets = await get_wallets(client, user.user_id)
        else:
            wallets = None
        return self.retrieve_response_schema(
            **item.model_dump(), ipgs=item.available_ipgs, wallets=wallets
        )

    async def create_item(
        self, request: Request, data: PurchaseCreateSchema
    ) -> PurchaseSchema:
        user = await self.get_user(request)
        tenant = await Tenant.get_by_tenant_id(user.tenant_id)

        if "currency" not in data.model_fields_set:
            data.currency = Currency(Settings.currency)

        if not data.available_ipgs:
            data.available_ipgs = tenant.ipgs

        if data.user_id:
            await self.authorize(
                action="create",
                user=user,
                filter_data=data.model_dump(exclude_none=True),
            )

        item = Purchase(
            tenant_id=user.tenant_id,
            user_id=data.user_id or user.user_id,
            **data.model_dump(exclude=["user_id"]),
        )  # type: ignore[missing-argument]
        await item.save()
        return item

        # return await super().create_item(request, item.model_dump())

    async def start_direct_purchase(
        self,
        request: Request,
        wallet_id: str,
        amount: Decimal,
        description: str,
        user_id: str,
        callback_url: str,
    ) -> dict:
        purchase: Purchase = await self.create_item(
            request,
            PurchaseCreateSchema(
                user_id=user_id,
                wallet_id=wallet_id,
                amount=amount,
                description=description,
                callback_url=callback_url,
            ),
        )
        return await self.start_purchase(request, purchase.uid)

    async def start_purchase_url(
        self,
        request: Request,
        uid: str,
        ipg: str | None = None,
        amount: Decimal | None = None,
    ) -> RedirectUrlSchema:
        # user = await self.get_user(request)
        # item: Purchase = await self.get_item(uid, tenant_id=user.tenant_id)
        user = self.get_user_or_none(request)
        item = await self.model.get_by_uid(uid)

        if ipg is None:
            ipg = item.available_ipgs[0]

        start_data = await start_purchase(
            purchase=item,
            tenant_id=item.tenant_id,
            ipg=ipg,
            amount=amount,
            user_id=item.user_id,
            phone=user.phone if user else None,
        )

        if start_data["status"]:
            return RedirectUrlSchema(redirect_url=start_data["url"])

        error = start_data.pop("error")
        raise BaseHTTPException(status_code=400, error=error, **start_data)

    async def start_purchase(
        self,
        request: Request,
        uid: str,
        ipg: str | None = None,
        amount: Decimal | None = None,
    ) -> RedirectResponse:
        redirect_dict = await self.start_purchase_url(request, uid, ipg, amount)
        return RedirectResponse(url=redirect_dict.redirect_url)

    async def verify_purchase(
        self,
        request: Request,
        uid: str,
    ) -> RedirectResponse:
        item: Purchase = await self.model.get_by_uid(uid)
        purchase_status = item.status

        purchase: Purchase = await verify_purchase(
            tenant_id=item.tenant_id, purchase=item
        )
        purchase_redirect_url = add_query_params(
            purchase.callback_url,
            {"purchase_id": purchase.uid, "status": purchase.status.value},
        )

        if purchase.status == PurchaseStatus.PENDING:
            return RedirectResponse(url=purchase_redirect_url, status_code=303)
            # return proper response
            return purchase
        if purchase.status == PurchaseStatus.SUCCESS:
            if purchase_status == PurchaseStatus.PENDING:
                await create_proposal(purchase)
            else:
                logging.info("purchase was not pending %s", purchase_status)

        return RedirectResponse(url=purchase_redirect_url, status_code=303)


router = PurchaseRouter().router
