import uuid

from fastapi import Request

from apps.business.middlewares import AuthorizationException
from apps.business.routes import AbstractAuthRouter

from core.exceptions import BaseHTTPException

from .models import Basket
from .schemas import (
    BasketCreateSchema,
    BasketItemChangeSchema,
    BasketDetailSchema,
    BasketItemSchema,
    BasketUpdateSchema,
)


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
            "/{uid}/purchase",
            self.checkout,
            methods=["POST"],
        )

    async def create_item(self, request: Request, data: BasketCreateSchema):
        await super().create_item(request, data.model_dump())

    async def update_item(
        self, request: Request, uid: uuid.UUID, data: BasketUpdateSchema
    ):
        return await super().update_item(
            request, uid, data.model_dump(exclude_none=True)
        )

    async def add_basket_item(
        self, request: Request, uid: uuid.UUID, data: BasketItemSchema
    ):
        basket: Basket = await self.get_item(uid)
        if not basket.is_modifiable:
            raise BaseHTTPException(400, "Basket is not active")
        await basket.add_basket_item(data)
        return basket

    async def update_basket_item(
        self,
        request: Request,
        uid: uuid.UUID,
        item_uid: uuid.UUID,
        data: BasketItemChangeSchema,
    ):
        basket: Basket = await self.get_item(uid)
        if not basket.is_modifiable:
            raise BaseHTTPException(400, "Basket is not active")
        await basket.update_basket_item(item_uid, data.quantity_change)
        return basket

    async def delete_basket_item(
        self, request: Request, uid: uuid.UUID, item_uid: uuid.UUID
    ):
        basket: Basket = await self.get_item(uid)
        if not basket.is_modifiable:
            raise BaseHTTPException(400, "Basket is not active")
        await basket.delete_basket_item(item_uid)
        return basket

    async def checkout(self, request: Request, uid: uuid.UUID):
        basket: Basket = await self.get_item(uid)

        raise NotImplementedError()


router = BasketRouter().router
