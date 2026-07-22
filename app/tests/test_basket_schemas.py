"""Unit tests for basket schemas."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from apps.basket.schemas import (
    BasketDetailSchema,
    BasketItemChangeSchema,
    BasketItemSchema,
    BasketStatusEnum,
    DiscountSchema,
)


def _now() -> datetime:
    return datetime.now(UTC)


def test_discount_and_item_price_with_discount() -> None:
    """Item price subtracts discount and coerces decimal inputs."""
    item = BasketItemSchema(
        uid="p1",
        name="Plan",
        unit_price="10.5",
        quantity="2",
        discount=DiscountSchema(code="OFF", user_id="u1", discount="1.5"),
    )
    assert item.price == Decimal("19.5")
    assert item.exchange_fee("IRR") == 1


def test_exchange_fee_rejects_other_currency() -> None:
    """Cross-currency exchange is not implemented."""
    item = BasketItemSchema(
        uid="p1",
        name="Plan",
        unit_price=Decimal(1),
        quantity=Decimal(1),
        currency="USD",
    )
    with pytest.raises(NotImplementedError):
        item.exchange_fee("IRR")


def test_basket_item_change_quantity_rules() -> None:
    """Change schema requires exactly one of quantity_change/new_quantity."""
    with pytest.raises(ValidationError):
        BasketItemChangeSchema()
    with pytest.raises(ValidationError):
        BasketItemChangeSchema(quantity_change=1, new_quantity=2)
    assert BasketItemChangeSchema(quantity_change=1).quantity_change == Decimal(1)
    assert BasketItemChangeSchema(new_quantity=3).new_quantity == Decimal(3)


def test_basket_detail_items_dict_and_urls() -> None:
    """Detail schema flattens item dicts and builds purchase URL."""
    now = _now()
    detail = BasketDetailSchema(
        uid="b1",
        created_at=now,
        updated_at=now,
        user_id="u1",
        tenant_id="t1",
        items={
            "p1": {
                "uid": "p1",
                "name": "Plan",
                "unit_price": 10,
                "quantity": 1,
            }
        },
        subtotal="10",
        amount="10",
        purchase_id="pay-1",
        status=BasketStatusEnum.active,
    )
    assert len(detail.items) == 1
    assert detail.is_modifiable is True
    assert detail.purchase_detail_url is not None
    assert detail.purchase_detail_url.endswith("/purchases/pay-1")

    unpaid = BasketDetailSchema(
        uid="b2",
        created_at=now,
        updated_at=now,
        user_id="u1",
        tenant_id="t1",
        items=[],
        subtotal=0,
        amount=0,
        status=BasketStatusEnum.paid,
    )
    assert unpaid.is_modifiable is False
    assert unpaid.purchase_detail_url is None


@pytest.mark.asyncio
async def test_basket_item_product_hooks_are_noop() -> None:
    """Reserve/buy/release hooks are currently no-ops."""
    item = BasketItemSchema(
        uid="p1",
        name="Plan",
        unit_price=Decimal(1),
        quantity=Decimal(1),
    )
    await item.reserve_product()
    await item.buy_product()
    await item.release_product()
