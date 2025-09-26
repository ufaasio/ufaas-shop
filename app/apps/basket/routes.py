from fastapi import Query, Request
from fastapi.responses import RedirectResponse
from fastapi_mongo_base.core.exceptions import BaseHTTPException
from fastapi_mongo_base.schemas import PaginatedResponse
from fastapi_mongo_base.utils import usso_routes

from server.config import Settings

from .models import Basket
from .schemas import (
    BasketCreateSchema,
    BasketDetailSchema,
    BasketItemChangeSchema,
    BasketItemCreateSchema,
    BasketStatusEnum,
    BasketUpdateSchema,
)
from .services import add_query_params, apply_discount, checkout_basket, validate_basket


class BasketRouter(usso_routes.AbstractTenantUSSORouter):
    model = Basket
    schema = BasketDetailSchema

    def config_routes(self, **kwargs: object) -> None:
        super().config_routes(**kwargs)

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
            self.checkout,
            methods=["POST"],
        )
        self.router.add_api_route(
            "/{uid}/validate",
            self.validate,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{uid}/validate",
            self.validate,
            methods=["POST"],
        )

    async def get_item(
        self,
        uid: str | None = None,
        user_id: str | None = None,
        tenant_id: str | None = None,
        creation: bool = False,
        callback_url: str | None = None,
        **kwargs: object,
    ) -> Basket:
        item = None
        if uid:
            item = await self.model.get_item(
                uid, user_id=user_id, tenant_id=tenant_id, **kwargs
            )
        if item is None:
            items = await self.model.list_items(
                user_id=user_id, tenant_id=tenant_id, status="active"
            )
            if items:
                return items[0]

            if not creation and callback_url is None:
                raise BaseHTTPException(
                    status_code=404,
                    error="item_not_found",
                    message=f"{self.model.__name__.capitalize()} not found",
                )

            item = self.model(
                tenant_id=tenant_id,
                user_id=user_id,
                # TODO: correct basket management domain
                callback_url=callback_url,
                status=BasketStatusEnum.active,
            )
            await item.save()

        return item

    async def retrieve_item(self, request: Request, uid: str) -> Basket:
        basket: Basket = await super().retrieve_item(request, uid)

        return basket.detail

    async def list_items(
        self,
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=0, le=Settings.page_max_limit),
        status: BasketStatusEnum | None = None,
    ) -> PaginatedResponse[BasketDetailSchema]:
        user = await self.get_user(request)
        items, total = await self.model.list_total_combined(
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            offset=offset,
            limit=limit,
            status=status,
        )

        items_in_schema = [basket.detail for basket in items]

        return PaginatedResponse(
            items=items_in_schema, offset=offset, limit=limit, total=total
        )

    async def create_item(self, request: Request, data: BasketCreateSchema) -> Basket:
        basket: Basket = await super().create_item(request, data.model_dump())
        return basket.detail

    async def update_item(
        self, request: Request, uid: str, data: BasketUpdateSchema
    ) -> Basket:
        basket: Basket = await super().update_item(
            request, uid, data.model_dump(exclude_unset=True)
        )
        basket = await apply_discount(basket, data.voucher)

        return basket.detail

    async def delete_item(self, request: Request, uid: str) -> Basket:
        basket: Basket = await super().delete_item(request, uid)
        return basket.detail

    async def add_basket_item(
        self,
        request: Request,
        data: BasketItemCreateSchema,
        uid: str | None = None,
        single: bool = False,
    ) -> Basket:
        user = await self.get_user(request)

        origin = request.headers.get("origin")

        basket: Basket = await self.get_item(
            uid=uid,
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            creation=True,
            callback_url=origin,
        )
        if not basket.is_modifiable:
            raise BaseHTTPException(400, "Basket is not active")
        await basket.add_basket_item(await data.get_basket_item(), single=single)
        return basket.detail

    async def update_basket_item(
        self,
        request: Request,
        uid: str,
        item_uid: str,
        data: BasketItemChangeSchema,
    ) -> Basket:
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
    ) -> Basket:
        user = await self.get_user(request)
        basket: Basket = await self.get_item(
            uid=uid, user_id=user.user_id, tenant_id=user.tenant_id
        )
        if not basket.is_modifiable:
            raise BaseHTTPException(400, "Basket is not active")
        await basket.delete_basket_item(item_uid)
        return basket.detail

    async def checkout(  # noqa: ANN201
        self,
        request: Request,
        uid: str,
        callback_url: str | None = None,
    ):
        user = await self.get_user(request)
        basket: Basket = await self.get_item(
            uid, user_id=user.user_id, tenant_id=user.tenant_id
        )
        url = await checkout_basket(basket, user.tenant_id, callback_url)
        if request.method == "GET":
            return RedirectResponse(url=url)
        return {"redirect_url": url}

    async def validate(self, request: Request, uid: str):  # noqa: ANN201
        user = await self.get_user(request)
        basket: Basket = await Basket.get_by_uid(uid)
        await validate_basket(basket, user.tenant_id)
        # if basket.status == "paid":
        #     if request.method == "GET":
        #         return RedirectResponse(url=basket.callback_url)
        #     return {"redirect_url": basket.callback_url}

        redirect_url = add_query_params(basket.callback_url, request.query_params)

        if request.method == "GET":
            return RedirectResponse(url=redirect_url)
        return {"redirect_url": redirect_url}
        raise BaseHTTPException(400, "Basket is not paid")


router = BasketRouter().router
