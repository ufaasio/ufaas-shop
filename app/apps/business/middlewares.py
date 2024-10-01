import uuid
from typing import Literal

from fastapi import Request
from pydantic import BaseModel

from core.exceptions import BaseHTTPException

from .auth_middlewares import UserData, Usso
from .models import Business


class AuthorizationData(BaseModel):
    user: UserData | None = None
    user_id: uuid.UUID | None = None
    business: Business | None = None
    auth_type: Literal["Business", "User", "App"] | None = None
    authorized: bool = False
    app_id: str | None = None

    scopes: list[str] | None = None


class AuthorizationException(BaseHTTPException):
    def __init__(self, message: str):
        super().__init__(401, "authorization_error", message)


async def get_business(
    request: Request,
) -> Business:
    business = await Business.get_by_origin(request.url.hostname)
    if not business:
        raise BaseHTTPException(404, "business_not_found", "business not found")
    return business


async def authorized_request(request: Request) -> bool:
    return True


async def business_or_user(
    request: Request,
) -> tuple[Literal["Business", "User", "App"], UserData]:
    business = await get_business(request)
    user = await Usso(jwt_config=business.config.jwt_config).jwt_access_security(
        request
    )

    if business.user_id == user.uid:
        return "Business", user
    return "User", user


async def get_request_body_dict(request: Request):
    body_bytes = await request.body()
    if not body_bytes:
        return {}
    return await request.json()


async def authorization_middleware(request: Request) -> AuthorizationData:
    authorization = AuthorizationData()

    authorization.business = await get_business(request)
    authorization.user = await Usso(
        jwt_config=authorization.business.config.jwt_config
    ).jwt_access_security(request)

    if (
        authorization.user.data
        and authorization.user.data.get("authentication_method") == "app"
    ):
        authorization.auth_type = "App"
        authorization.user_id = authorization.user.data.get("app_id")
        authorization.app_id = authorization.user.data.get("app_id")
        authorization.scopes = authorization.user.data.get("scopes")

    elif authorization.business.user_id == authorization.user.uid:
        authorization.auth_type = "Business"
        authorization.user_id = (
            request.query_params.get("user_id")
            or request.path_params.get("user_id")
            or (await get_request_body_dict(request)).get("user_id")
        )
    else:
        authorization.auth_type = "User"
        authorization.user_id = authorization.user.uid

    # authorization.app_id = request.headers.get("X-App-Id")
    authorization.authorized = await authorized_request(request)

    return authorization
