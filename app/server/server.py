from fastapi import APIRouter
from fastapi_mongo_base.core import app_factory

from apps.basket.routes import router as basket_router
from apps.voucher.routes import router as voucher_router

from . import config

app = app_factory.create_app(settings=config.Settings())
server_router = APIRouter()

for router in [basket_router, voucher_router]:
    server_router.include_router(router)

app.include_router(server_router, prefix=config.Settings.base_path)
