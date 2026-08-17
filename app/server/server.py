"""FastAPI application factory."""

import tomllib
from pathlib import Path

from fastapi import APIRouter
from fastapi_mongo_base.core import app_factory
from ufaas.fastapi import EXCEPTION_HANDLERS

from apps.basket.routes import router as basket_router
from apps.product.routes import router as product_router
from apps.purchase.routes import router as purchase_router
from apps.tenant.routes import router as tenant_router
from apps.voucher.routes import router as voucher_router

from . import config

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
with _PYPROJECT.open("rb") as _pyproject:
    _APP_VERSION = tomllib.load(_pyproject)["project"]["version"]

exception_handlers = {}
exception_handlers.update(EXCEPTION_HANDLERS)

app = app_factory.create_app(
    settings=config.Settings(),
    version=_APP_VERSION,
    exception_handlers=exception_handlers,
)
server_router = APIRouter()

for router in [
    product_router,
    basket_router,
    voucher_router,
    purchase_router,
    tenant_router,
]:
    server_router.include_router(router)

app.include_router(server_router, prefix=config.Settings.base_path)
