"""Currency enum utilities."""

from enum import StrEnum


class Currency(StrEnum):
    """Supported currencies."""

    none = "none"

    IRR = "IRR"
    IRT = "IRT"

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

    USDT = "USDT"
    BTC = "BTC"
    ETH = "ETH"
