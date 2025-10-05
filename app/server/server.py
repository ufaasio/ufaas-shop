from fastapi import APIRouter
from fastapi_mongo_base.core import app_factory

from apps.basket.routes import router as basket_router
from apps.payment.routes import router as payment_router
from apps.product.routes import router as product_router
from apps.tenant.routes import router as tenant_router
from apps.voucher.routes import router as voucher_router

from . import config

app = app_factory.create_app(settings=config.Settings())
server_router = APIRouter()

for router in [
    product_router,
    basket_router,
    voucher_router,
    payment_router,
    tenant_router,
]:
    server_router.include_router(router)

app.include_router(server_router, prefix=config.Settings.base_path)
