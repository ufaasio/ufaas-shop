import uuid
from typing import TypeVar

from fastapi import Depends, Query, Request
from fastapi_mongo_base.handlers import create_dto
from fastapi_mongo_base.models import BusinessEntity
from fastapi_mongo_base.routes import AbstractBaseRouter
from fastapi_mongo_base.schemas import BusinessEntitySchema, PaginatedResponse
from usso.fastapi import jwt_access_security

from server.config import Settings

from .middlewares import AuthorizationData, authorization_middleware, get_business
from .models import Business
from .schemas import BusinessDataCreateSchema, BusinessDataUpdateSchema, BusinessSchema

T = TypeVar("T", bound=BusinessEntity)
TS = TypeVar("TS", bound=BusinessEntitySchema)


class AbstractBusinessBaseRouter(AbstractBaseRouter[T, TS]):
    async def list_items(
        self,
        request: Request,
        offset: int = 0,
        limit: int = 10,
        business: Business = Depends(get_business),
    ):
        user_id = await self.get_user_id(request)
        limit = max(1, min(limit, Settings.page_max_limit))

        items, total = await self.model.list_total_combined(
            user_id=user_id,
            business_name=business.name,
            offset=offset,
            limit=limit,
        )
        items_in_schema = [self.list_item_schema(**item.model_dump()) for item in items]

        return PaginatedResponse(
            items=items_in_schema,
            total=total,
            offset=offset,
            limit=limit,
        )

    async def retrieve_item(
        self,
        request: Request,
        uid,
        business: Business = Depends(get_business),
    ):
        user_id = await self.get_user_id(request)
        item = await self.get_item(uid, user_id=user_id, business_name=business.name)
        return item

    async def create_item(
        self,
        request: Request,
        business: Business = Depends(get_business),
    ):
        user_id = await self.get_user_id(request)
        item_data: TS = await create_dto(self.create_response_schema)(
            request, user_id=user_id, business_name=business.name
        )
        item = await self.model.create_item(item_data.model_dump())

        await item.save()
        return item

    async def update_item(
        self,
        request: Request,
        uid,
        data: dict,
        business: Business = Depends(get_business),
    ):
        user_id = await self.get_user_id(request)
        item = await self.get_item(uid, user_id=user_id, business_name=business.name)
        # item = await update_dto(self.model)(request, user)
        item = await self.model.update_item(item, data)
        return item

    async def delete_item(
        self,
        request: Request,
        uid,
        business: Business = Depends(get_business),
    ):
        user_id = await self.get_user_id(request)
        item = await self.get_item(uid, user_id=user_id, business_name=business.name)
        item = await self.model.delete_item(item)
        return item


class AbstractAuthRouter(AbstractBusinessBaseRouter[T, TS]):
    async def get_auth(self, request: Request) -> AuthorizationData:
        return await authorization_middleware(request)

    async def list_items(
        self,
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=0, le=Settings.page_max_limit),
    ):
        auth = await self.get_auth(request)
        items, total = await self.model.list_total_combined(
            user_id=auth.user_id,
            business_name=auth.business.name,
            offset=offset,
            limit=limit,
        )

        items_in_schema = [self.list_item_schema(**item.model_dump()) for item in items]

        return PaginatedResponse(
            items=items_in_schema, offset=offset, limit=limit, total=total
        )

    async def retrieve_item(self, request: Request, uid: uuid.UUID):
        auth = await self.get_auth(request)
        item = await self.get_item(
            uid, user_id=auth.user_id, business_name=auth.business.name
        )
        return item

    async def create_item(self, request: Request, data: dict):
        auth = await self.get_auth(request)
        item = self.model(
            business_name=auth.business.name,
            user_id=auth.user_id if auth.user_id else auth.user.uid,
            **data,
        )
        await item.save()
        return self.create_response_schema(**item.model_dump())

    async def update_item(self, request: Request, uid: uuid.UUID, data: dict):
        auth = await self.get_auth(request)
        item = await self.get_item(
            uid, user_id=auth.user_id, business_name=auth.business.name
        )

        item = await self.model.update_item(item, data)
        return item

    async def delete_item(self, request: Request, uid: uuid.UUID):
        auth = await self.get_auth(request)
        item = await self.get_item(
            uid, user_id=auth.user_id, business_name=auth.business.name
        )
        item = await self.model.delete_item(item)
        return item


class BusinessRouter(AbstractBaseRouter[Business, BusinessSchema]):
    def __init__(self):
        super().__init__(
            model=Business,
            schema=BusinessSchema,
            user_dependency=jwt_access_security,
            prefix="/businesses",
        )

    def config_schemas(self, schema, **kwargs):
        super().config_schemas(schema, **kwargs)

        self.create_request_schema = BusinessDataCreateSchema
        self.update_request_schema = BusinessDataUpdateSchema

    async def create_item(
        self,
        request: Request,
        item: BusinessDataCreateSchema,
    ):
        return await super().create_item(request, item.model_dump())

    async def update_item(
        self,
        request: Request,
        uid: uuid.UUID,
        data: BusinessDataUpdateSchema,
    ):
        return await super().update_item(
            request, uid, data.model_dump(exclude_none=True)
        )


router = BusinessRouter().router
