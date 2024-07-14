import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BaseEntitySchema(BaseModel):
    uid: uuid.UUID = Field(default_factory=uuid.uuid4, index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_deleted: bool = False
    metadata: dict[str, Any] | None = None


class OwnedEntitySchema(BaseEntitySchema):
    user_id: uuid.UUID


class BusinessEntitySchema(BaseEntitySchema):
    business_id: uuid.UUID


class BusinessOwnedEntitySchema(OwnedEntitySchema, BusinessEntitySchema):
    pass
