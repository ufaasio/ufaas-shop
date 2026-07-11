import logging
import os
from collections.abc import AsyncGenerator, Generator

import httpx
import pytest
import pytest_asyncio
from beanie import init_beanie
from fastapi_mongo_base import models
from fastapi_mongo_base.utils import basic

from server.config import Settings
from server.server import app as fastapi_app


@pytest.fixture(scope="session", autouse=True)
def setup_debugpy() -> None:
    if os.getenv("DEBUGPY", "False").lower() in ("true", "1", "yes"):
        import debugpy  # noqa: T100

        debugpy.listen(("127.0.0.1", 3020))  # noqa: T100
        logging.info("Waiting for debugpy client")
        debugpy.wait_for_client()  # noqa: T100


@pytest.fixture(scope="session")
def mongo_client() -> Generator[object]:
    from mongomock_motor import AsyncMongoMockClient

    yield AsyncMongoMockClient()


# Async setup function to initialize the database with Beanie
async def init_db(mongo_client: object) -> None:
    database = mongo_client.get_database("test_db")
    await init_beanie(
        database=database,
        document_models=basic.get_all_subclasses(models.BaseEntity),
    )


@pytest_asyncio.fixture(scope="session", autouse=True)
async def db(mongo_client: object) -> AsyncGenerator[None]:
    Settings.config_logger()
    logging.info("Initializing database")
    await init_db(mongo_client)
    logging.info("Database initialized")
    yield
    logging.info("Cleaning up database")


@pytest_asyncio.fixture(scope="session")
async def client() -> AsyncGenerator[httpx.AsyncClient]:
    """Fixture to provide an AsyncClient for FastAPI app."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url=f"https://test.uln.me{Settings.base_path}",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(scope="session")
async def authenticated_client(
    client: httpx.AsyncClient,
) -> AsyncGenerator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url=client.base_url,
        headers={"x-api-key": os.getenv("API_KEY")},
    ) as ac:
        yield ac
