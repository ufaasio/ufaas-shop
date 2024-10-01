from decimal import Decimal


def decimal_amount(value):
    from bson.decimal128 import Decimal128

    if type(value) == Decimal128:
        return Decimal(value.to_decimal())
    return value
