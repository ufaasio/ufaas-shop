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

#### End of BaseModel ####


#### Start of Invoice ####
class Invoice(BaseEntity):
    """a mutable table based on class BaseEntity."""
    __tablename__ = "invoice"
    business_id: Mapped[uuid.UUID] = mapped_column(index=True)

    merchant: Mapped[str] = mapped_column(sa.JSON(), nullable=False)
    customer: Mapped[str] = mapped_column(sa.JSON(), nullable=False)

    proposal_id: Mapped[str] = mapped_column(index=True)
    transaction_id: Mapped[str] = mapped_column(index=True)

    items: Mapped[str] = mapped_column(sa.JSON(), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    enrollment_id: Mapped[uuid.UUID] = mapped_column(index=True)
    amount: Mapped[float] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    due_date: Mapped[datetime] = mapped_column(nullable=False)
    issued_date: Mapped[datetime] = mapped_column(nullable=False)


#### End of Invoice ####

#### Start of Revenue Sharing Rules ####
class RevenueSharingRule(ImmutableBase):
    """A mutable table based on class ImmutableBase.
    Each Item in basket model has a Revenue Sharing Rule.
    this table has an entity "is_deleted" which is set to False by default. this is the only entity that can be updated in this table. using as soft delete.
    """

    __tablename__ = "revenue_sharing_rule"
    uid: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(index=True)
    name: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column(nullable=True)
    is_default: Mapped[bool] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    shares: Mapped[list[dict]] = mapped_column(sa.JSON(), nullable=False)
