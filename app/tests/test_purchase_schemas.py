"""Unit tests for purchase schemas."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from apps.purchase.schemas import PurchaseSchema


def test_purchase_schema_overdue_and_original_amount() -> None:
    """Purchase marks overdue after duration and fills original_amount."""
    created = datetime.now(UTC) - timedelta(hours=2)
    purchase = PurchaseSchema(
        uid="p1",
        created_at=created,
        updated_at=created,
        user_id="u1",
        tenant_id="t1",
        wallet_id="w1",
        amount="1000",
        description="test",
        callback_url="https://example.test/cb",
        duration=60,
    )
    assert purchase.amount == Decimal("1000")
    assert purchase.original_amount == Decimal("1000")
    assert purchase.is_overdue() is True

    fresh = PurchaseSchema(
        uid="p2",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        user_id="u1",
        tenant_id="t1",
        wallet_id="w1",
        amount=Decimal(10),
        original_amount=Decimal(10),
        description="test",
        callback_url="https://example.test/cb",
        duration=3600,
    )
    assert fresh.is_overdue() is False
