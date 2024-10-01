from fastapi_mongo_base.models import OwnedEntity
from pydantic import model_validator
from pymongo import ASCENDING, IndexModel

from server.config import Settings

from .schemas import AppAuth, Config


class Business(OwnedEntity):
    name: str
    domain: str

    description: str | None = None
    config: Config = Config()

    class Settings:
        indexes = [
            IndexModel([("name", ASCENDING)], unique=True),
            IndexModel([("domain", ASCENDING)], unique=True),
        ]

    @property
    def root_url(self):
        if self.domain.startswith("http"):
            return self.domain
        return f"https://{self.domain}"

    @classmethod
    async def get_by_origin(cls, origin: str):
        return await cls.find_one(cls.domain == origin)

    @classmethod
    async def get_by_name(cls, name: str):
        return await cls.find_one(cls.name == name)

    @model_validator(mode="before")
    def validate_domain(cls, data: dict):
        if not data.get("domain"):
            business_name_domain = f"{data.get('name')}.{Settings.root_url}"
            data["domain"] = business_name_domain

        return data

    @classmethod
    async def create_item(cls, data: dict):
        business = await super().create_item(data)
        return business

    async def get_access_token(self):
        from utils.aionetwork import aio_request

        # TODO set scopes
        # TODO add caching
        app_auth = AppAuth(
            app_id=Settings.app_id,
            scopes=[],
            sso_url=self.config.sso_url,
        )
        app_auth.secret = app_auth.get_secret(app_secret=Settings.app_secret)

        response_data: dict = await aio_request(
            method="post", url=self.config.core_sso_url, json=app_auth.model_dump()
        )
        return response_data.get("access_token")
