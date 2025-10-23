import logging

from fastapi import Query, Request
from fastapi.responses import RedirectResponse
from fastapi_mongo_base.core.exceptions import BaseHTTPException
from fastapi_mongo_base.schemas import PaginatedResponse
from fastapi_mongo_base.utils import usso_routes

from server.config import Settings
from utils.schemas import RedirectUrlSchema
from utils.texttools import add_query_params

from .models import Basket
from .schemas import (
    BasketCreateSchema,
    BasketDetailSchema,
    BasketItemChangeSchema,
    BasketItemCreateSchema,
    BasketStatusEnum,
    BasketUpdateSchema,
)
from .services import (
    apply_discount,
    buy_basket,
    create_checkout_basket_url,
    validate_basket,
)


class BasketRouter(usso_routes.AbstractTenantUSSORouter):
    model = Basket
    schema = BasketDetailSchema

    def config_routes(self, **kwargs: object) -> None:
        super().config_routes(**kwargs)

        self.router.add_api_route(
            "/items/purchase",
            self.purchasse_exclusive_item,
            methods=["POST"],
            response_model=RedirectUrlSchema,
        )
        self.router.add_api_route(
            "/{uid}/items",
            self.add_basket_item,
            methods=["POST"],
            response_model=self.retrieve_response_schema,
        )
        self.router.add_api_route(
            "/items",
            self.add_basket_item,
            methods=["POST"],
            response_model=self.retrieve_response_schema,
        )
        self.router.add_api_route(
            "/{uid}/items/{item_uid}",
            self.update_basket_item,
            methods=["PATCH"],
            response_model=self.retrieve_response_schema,
        )
        self.router.add_api_route(
            "/{uid}/items/{item_uid}",
            self.delete_basket_item,
            methods=["DELETE"],
            response_model=self.retrieve_response_schema,
        )

        self.router.add_api_route(
            "/{uid}/checkout",
            self.checkout,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{uid}/checkout",
            self.checkout_url,
            methods=["POST"],
            response_model=RedirectUrlSchema,
        )
        self.router.add_api_route(
            "/{uid}/validate",
            self.validate,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{uid}/validate",
            self.validate_url,
            methods=["POST"],
            response_model=RedirectUrlSchema,
        )

    async def get_or_create_for_user(
        self,
        user_id: str,
        tenant_id: str,
        callback_url: str | None = None,
        **kwargs: object,
    ) -> Basket:
        items = await Basket.list_items(
            user_id=user_id, tenant_id=tenant_id, status="active", **kwargs
        )
        if items:
            return items[0]

        item = Basket(
            tenant_id=tenant_id,
            user_id=user_id,
            callback_url=callback_url,
            status=BasketStatusEnum.active,
        )
        await item.save()

        return item

    async def retrieve_item(self, request: Request, uid: str) -> BasketDetailSchema:
        basket: Basket = await super().retrieve_item(request, uid)

        return basket.detail

    async def list_items(
        self,
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=0, le=Settings.page_max_limit),
        status: BasketStatusEnum | None = None,
        sort_field: str = "created_at",
        sort_direction: int = -1,
    ) -> PaginatedResponse[BasketDetailSchema]:
        user = await self.get_user(request)
        items, total = await Basket.list_total_combined(
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            offset=offset,
            limit=limit,
            status=status,
            sort_field=sort_field,
            sort_direction=sort_direction,
        )

        items_in_schema = [basket.detail for basket in items]

        return PaginatedResponse(
            items=items_in_schema, offset=offset, limit=limit, total=total
        )

    async def create_item(
        self, request: Request, data: BasketCreateSchema
    ) -> BasketDetailSchema:
        user = await self.get_user(request)
        if data.user_id:
            await self.authorize(
                action="create",
                user=user,
                filter_data=data.model_dump(exclude_none=True),
            )

        basket: Basket = await Basket.create_item({
            "tenant_id": user.tenant_id,
            "user_id": data.user_id or user.user_id,
            **data.model_dump(exclude=["user_id"]),
        })
        return basket.detail

    async def update_item(
        self, request: Request, uid: str, data: BasketUpdateSchema
    ) -> BasketDetailSchema:
        basket: Basket = await super().update_item(
            request, uid, data.model_dump(exclude_unset=True)
        )
        basket = await apply_discount(basket, data.voucher)

        return basket.detail

    async def delete_item(self, request: Request, uid: str) -> BasketDetailSchema:
        basket: Basket = await super(
            usso_routes.AbstractTenantUSSORouter, self
        ).delete_item(request, uid)
        return basket.detail

    async def purchasse_exclusive_item(
        self,
        request: Request,
        data: BasketItemCreateSchema,
        user_id: str | None = None,
        callback_url: str | None = None,
    ) -> RedirectUrlSchema:
        try:
            user = await self.get_user(request)
            if user_id:
                await self.authorize(
                    action="create",
                    user=user,
                    filter_data=data.model_dump(exclude_none=True)
                    | {"user_id": user_id},
                )
            basket: Basket = await Basket(
                tenant_id=user.tenant_id,
                user_id=user_id or user.user_id,
                callback_url=callback_url,
                status=BasketStatusEnum.active,
            ).save()
            await basket.add_basket_item(await data.get_basket_item(), exclusive=True)
            url = await create_checkout_basket_url(basket, callback_url)
            return RedirectUrlSchema(redirect_url=url)
        except Exception:
            logging.exception("Error purchasing exclusive item")
            raise

    async def add_basket_item(
        self,
        request: Request,
        data: BasketItemCreateSchema,
        uid: str | None = None,
        exclusive: bool = False,
        callback_url: str | None = None,
    ) -> BasketDetailSchema:
        user = await self.get_user(request)

        basket: Basket = await self.get_item(
            uid=uid,
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            **({"callback_url": callback_url} if callback_url else {}),
        )
        if not basket.is_modifiable:
            raise BaseHTTPException(400, "Basket is not active")
        await basket.add_basket_item(await data.get_basket_item(), exclusive=exclusive)
        return basket.detail

    async def update_basket_item(
        self,
        request: Request,
        uid: str,
        item_uid: str,
        data: BasketItemChangeSchema,
    ) -> BasketDetailSchema:
        user = await self.get_user(request)
        basket: Basket = await self.get_item(
            uid=uid, user_id=user.user_id, tenant_id=user.tenant_id
        )
        if not basket.is_modifiable:
            raise BaseHTTPException(400, "Basket is not active")
        await basket.update_basket_item(item_uid, data)
        return basket.detail

    async def delete_basket_item(
        self, request: Request, uid: str, item_uid: str
    ) -> BasketDetailSchema:
        user = await self.get_user(request)
        basket: Basket = await self.get_item(
            uid=uid, user_id=user.user_id, tenant_id=user.tenant_id
        )
        if not basket.is_modifiable:
            raise BaseHTTPException(400, "Basket is not active")
        await basket.delete_basket_item(item_uid)
        return basket.detail

    async def checkout_url(
        self,
        request: Request,
        uid: str,
        callback_url: str | None = None,
    ) -> RedirectUrlSchema:
        user = await self.get_user(request)
        basket: Basket = await self.get_item(
            uid, user_id=user.user_id, tenant_id=user.tenant_id
        )
        url = await create_checkout_basket_url(basket, callback_url)
        return RedirectUrlSchema(redirect_url=url)

    async def checkout(
        self,
        request: Request,
        uid: str,
        callback_url: str | None = None,
    ) -> RedirectResponse:
        redirect_dict = await self.checkout_url(request, uid, callback_url)
        return RedirectResponse(url=redirect_dict.redirect_url)

    async def validate_url(self, request: Request, uid: str) -> RedirectUrlSchema:
        # await self.get_user(request)
        basket = await Basket.get_by_uid(uid)
        if not basket:
            raise BaseHTTPException(404, "basket_not_found", "Basket not found")
        await validate_basket(basket)
        await buy_basket(basket)
        if not basket.callback_url:
            raise BaseHTTPException(
                400, "invalid_callback_url", "Callback URL not found"
            )
        redirect_url = add_query_params(basket.callback_url, dict(request.query_params))

        return RedirectUrlSchema(redirect_url=redirect_url)

    async def validate(self, request: Request, uid: str) -> RedirectResponse:
        redirect_dict = await self.validate_url(request, uid)
        return RedirectResponse(url=redirect_dict.redirect_url)


router = BasketRouter().router
