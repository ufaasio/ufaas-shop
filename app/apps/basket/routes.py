import uuid

from fastapi import Query, Request
from fastapi.responses import RedirectResponse
from fastapi_mongo_base.core.exceptions import BaseHTTPException
from fastapi_mongo_base.schemas import PaginatedResponse
from server.config import Settings
from ufaas_fastapi_business.middlewares import authorization_middleware
from ufaas_fastapi_business.routes import AbstractAuthRouter

from .models import Basket
from .schemas import (
    BasketCreateSchema,
    BasketDetailSchema,
    BasketItemChangeSchema,
    BasketItemCreateSchema,
    BasketStatusEnum,
    BasketUpdateSchema,
)
from .services import apply_discount, checkout_basket, validate_basket


class BasketRouter(AbstractAuthRouter[Basket, BasketDetailSchema]):
    def __init__(self):
        super().__init__(model=Basket, schema=BasketDetailSchema, user_dependency=None)

    def config_routes(self, **kwargs):
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
            methods=["GET", "POST"],
        )
        self.router.add_api_route(
            "/{uid}/validate",
            self.validate,
            methods=["GET", "POST"],
        )

    async def get_item(
        self,
        uid: uuid.UUID = None,
        user_id: uuid.UUID = None,
        business_name: str = None,
        creation: bool = False,
        callback_url=None,
        **kwargs,
    ):
        item = None
        if uid:
            item = await self.model.get_item(
                uid, user_id=user_id, business_name=business_name, **kwargs
            )
        if item is None:
            items = await self.model.list_items(
                user_id=user_id, business_name=business_name, status="active"
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
                business_name=business_name,
                user_id=user_id,
                # TODO: correct basket management domain
                callback_url=callback_url,
                status=BasketStatusEnum.active,
            )
            await item.save()

        return item

    async def retrieve_item(self, request: Request, uid: uuid.UUID):
        basket: Basket = await super().retrieve_item(request, uid)

        return basket.detail

    async def list_items(
        self,
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=0, le=Settings.page_max_limit),
        status: BasketStatusEnum = None,
    ):
        auth = await self.get_auth(request)
        items, total = await self.model.list_total_combined(
            user_id=auth.user_id,
            business_name=auth.business.name,
            offset=offset,
            limit=limit,
            status=status,
        )

        items_in_schema = [basket.detail for basket in items]

        return PaginatedResponse(
            items=items_in_schema, offset=offset, limit=limit, total=total
        )

    async def create_item(self, request: Request, data: BasketCreateSchema):
        basket = await super().create_item(request, data.model_dump())
        return basket.detail

    async def update_item(
        self, request: Request, uid: uuid.UUID, data: BasketUpdateSchema
    ):
        basket = await super().update_item(
            request, uid, data.model_dump(exclude_unset=True)
        )
        basket = await apply_discount(basket, data.voucher)

        return basket.detail

    async def delete_item(self, request: Request, uid: uuid.UUID):
        basket = await super().delete_item(request, uid)
        return basket.detail

    async def add_basket_item(
        self,
        request: Request,
        data: BasketItemCreateSchema,
        uid: uuid.UUID | None = None,
    ):
        auth = await self.get_auth(request)

        origin = request.headers.get("origin") or auth.business.main_domain

        basket: Basket = await self.get_item(
            uid=uid,
            user_id=auth.user_id,
            business_name=auth.business.name,
            creation=True,
            callback_url=origin,
        )
        if not basket.is_modifiable:
            raise BaseHTTPException(400, "Basket is not active")
        await basket.add_basket_item(await data.get_basket_item())
        return basket.detail

    async def update_basket_item(
        self,
        request: Request,
        uid: uuid.UUID,
        item_uid: uuid.UUID,
        data: BasketItemChangeSchema,
    ):
        auth = await self.get_auth(request)
        basket: Basket = await self.get_item(
            uid=uid, user_id=auth.user_id, business_name=auth.business.name
        )
        if not basket.is_modifiable:
            raise BaseHTTPException(400, "Basket is not active")
        await basket.update_basket_item(item_uid, data)
        return basket.detail

    async def delete_basket_item(
        self, request: Request, uid: uuid.UUID, item_uid: uuid.UUID
    ):
        auth = await self.get_auth(request)
        basket: Basket = await self.get_item(
            uid=uid, user_id=auth.user_id, business_name=auth.business.name
        )
        if not basket.is_modifiable:
            raise BaseHTTPException(400, "Basket is not active")
        await basket.delete_basket_item(item_uid)
        return basket.detail

    async def checkout(
        self,
        request: Request,
        uid: uuid.UUID,
        callback_url: str = None,
    ):
        auth = await self.get_auth(request)
        basket: Basket = await self.get_item(
            uid, user_id=auth.user_id, business_name=auth.business.name
        )
        url = await checkout_basket(basket, auth.business, callback_url)
        if request.method == "GET":
            return RedirectResponse(url=url)
        return {"redirect_url": url}

    async def validate(self, request: Request, uid: uuid.UUID):
        auth = await authorization_middleware(request, anonymous_accepted=True)
        basket: Basket = await Basket.get_by_uid(uid)
        await validate_basket(basket, auth.business)
        # if basket.status == "paid":
        #     if request.method == "GET":
        #         return RedirectResponse(url=basket.callback_url)
        #     return {"redirect_url": basket.callback_url}

        import logging
        logging.info(f"{request.query_params}")

        redirect_url = f"{basket.callback_url}{'&' if '?' in basket.callback_url else '?'}{request.query_params}"

        if request.method == "GET":
            return RedirectResponse(url=redirect_url)
        return {"redirect_url": redirect_url}
        raise BaseHTTPException(400, "Basket is not paid")


router = BasketRouter().router
