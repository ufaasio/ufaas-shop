from apps.basket.routes import router as basket_router
from apps.voucher.routes import router as voucher_router
from fastapi_mongo_base.core import app_factory

from . import config

app = app_factory.create_app(
    settings=config.Settings(), original_host_middleware=True, serve_coverage=False
)
app.include_router(basket_router, prefix=f"{config.Settings.base_path}")
app.include_router(voucher_router, prefix=f"{config.Settings.base_path}")
