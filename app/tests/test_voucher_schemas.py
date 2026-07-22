"""Unit tests for voucher schemas."""

from decimal import Decimal

from apps.voucher.schemas import VoucherCreateSchema, VoucherStatus


def test_voucher_create_coerces_rate_and_defaults() -> None:
    """Create schema coerces rate and defaults to active status."""
    voucher = VoucherCreateSchema(rate="12.5", cap="1000")
    assert voucher.rate == Decimal("12.5")
    assert voucher.cap == Decimal("1000")
    assert voucher.status == VoucherStatus.ACTIVE
    assert voucher.code
