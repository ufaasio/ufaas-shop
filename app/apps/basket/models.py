import uuid
from decimal import Decimal

from fastapi_mongo_base.models import BusinessOwnedEntity

from .schemas import BasketDataSchema, BasketItemSchema


class Basket(BasketDataSchema, BusinessOwnedEntity):
    items: dict[uuid.UUID, BasketItemSchema] = {}

    @property
    def total(self):
        total = sum(
            [
                item.price * item.exchange_fee(self.currency)
                for item in self.items.values()
            ]
        )
        if self.discount:
            total -= self.discount.apply_discount(total)
        return total

    async def add_basket_item(self, item: BasketItemSchema):
        item_dict = item.model_dump(exclude=["uid", "quantity"])
        for existing_item in self.items.values():
            if (
                existing_item.model_dump(exclude=["uid", "quantity"])
                == item_dict
            ):
                existing_item.quantity += item.quantity
                await self.save()
                return

        self.items[item.uid] = item
        await self.save()

    async def update_basket_item(
        self, item_id: uuid.UUID, quantity_change: Decimal, **kwargs
    ):
        basket_item = self.items.get(item_id)

        if basket_item is None:
            if kwargs.get("raise_error", False):
                return
            raise ValueError(f"Item with id {item_id} not found in the basket.")

        new_quantity = basket_item.quantity + quantity_change
        if new_quantity <= 0:
            self.items.pop(item_id)
        else:
            basket_item.quantity = new_quantity

        await self.save()

    async def delete_basket_item(self, item_id: uuid.UUID):
        self.items.pop(item_id, None)
        await self.save()
