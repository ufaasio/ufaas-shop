"""Unit tests for product schemas."""

from datetime import UTC, datetime
from decimal import Decimal

from apps.product.schemas import (
    ItemType,
    ProductCreateSchema,
    ProductSchema,
    ProductStatus,
    ProductUpdateSchema,
)


def test_product_create_coerces_decimals() -> None:
    """Create schema coerces price/stock via decimal_amount."""
    product = ProductCreateSchema(
        name="Pro",
        unit_price="99.5",
        stock_quantity="3",
        item_type=ItemType.retail_product,
    )
    assert product.unit_price == Decimal("99.5")
    assert product.stock_quantity == Decimal("3")


def test_product_schema_defaults_and_update() -> None:
    """Product schema defaults to active; update fields are optional."""
    now = datetime.now(UTC)
    product = ProductSchema(
        uid="p1",
        created_at=now,
        updated_at=now,
        user_id="u1",
        tenant_id="t1",
        name="Pro",
        unit_price=Decimal(10),
    )
    assert product.status == ProductStatus.active
    update = ProductUpdateSchema(name="Pro+", unit_price=Decimal(12))
    assert update.name == "Pro+"
    assert update.unit_price == Decimal(12)
