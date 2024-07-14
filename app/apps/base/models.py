import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Mapped, declared_attr, mapped_column
from sqlalchemy.sql import func

# Base = declarative_base()


@as_declarative()
class BaseEntity:
    id: Any
    __name__: str
    __abstract__ = True

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    uid: Mapped[uuid.UUID] = mapped_column(
        # pgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        # DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), onupdate=func.now()
    )
    is_deleted: Mapped[bool] = mapped_column(
        default=False
    )  # Column(Boolean, default=False)
    metadata: Mapped[dict | None] = mapped_column(
        nullable=True
    )  # Column(JSON, nullable=True)
    # name: Mapped[str | None] = mapped_column(nullable=True)

    # def __init__(self, **kwargs):
    #     super().__init__(**kwargs)
    #     self.uid = uuid.uuid4()
    #     self.created_at = datetime.now(timezone.utc)
    #     self.updated_at = datetime.now(timezone.utc)
    #     self.is_deleted = False
    #     self.metadata = None


class ImmutableBase(BaseEntity):
    __abstract__ = True

    @staticmethod
    def prevent_update(mapper, connection, target):
        if connection.in_transaction() and target.id is not None:
            raise ValueError("Updates are not allowed for this object")

    @classmethod
    def __declare_last__(cls):
        event.listen(cls, "before_update", cls.prevent_update)


Base = BaseEntity


class OwnedEntity(BaseEntity):
    __abstract__ = True

    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    # Column(pgUUID(as_uuid=True), index=True)


class BusinessEntity(BaseEntity):
    __abstract__ = True

    business_id: Mapped[uuid.UUID] = mapped_column(index=True)
    # Column(pgUUID(as_uuid=True), index=True)


class BusinessOwnedEntity(BaseEntity):
    __abstract__ = True

    business_id: Mapped[uuid.UUID] = mapped_column(index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(index=True)


class OwnedEntity(BaseEntity):
    __abstract__ = True

    owner_id: Mapped[uuid.UUID] = mapped_column(index=True)


class BusinessEntity(BaseEntity):
    __abstract__ = True

    business_id: Mapped[uuid.UUID] = mapped_column(index=True)


class BusinessOwnedEntity(BusinessEntity, OwnedEntity):
    __abstract__ = True

    # owner_id: Mapped[uuid.UUID] = mapped_column(index=True)
    # business_id: Mapped[uuid.UUID] = mapped_column(index=True)


class ImmutableBase(BaseEntity):
    __abstract__ = True

    @staticmethod
    def prevent_update(mapper, connection, target):
        if connection.in_transaction() and target.id is not None:
            raise ValueError("Updates are not allowed for this object")

    @classmethod
    def __declare_last__(cls):
        event.listen(cls, "before_update", cls.prevent_update)


class ImmutableOwnedEntity(ImmutableBase, OwnedEntity):
    __abstract__ = True


class ImmutableBusinessEntity(ImmutableBase, BusinessEntity):
    __abstract__ = True


class ImmutableBusinessOwnedEntity(ImmutableBase, BusinessOwnedEntity):
    __abstract__ = True
