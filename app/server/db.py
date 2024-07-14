from server.config import Settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(Settings.DATABASE_URL, future=True, echo=True)
async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

from apps.accounting import models as accounting_models
from apps.applications import models as applications_models

# Base = declarative_base()  # model base class
from apps.base.models import Base
from apps.business import models as business_models

__all__ = ["accounting_models", "applications_models", "business_models"]


async def get_session():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
