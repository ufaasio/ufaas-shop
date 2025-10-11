from decimal import Decimal

from fastapi_mongo_base.models import TenantUserEntity
from pydantic import Field

from .schemas import (
    BasketDataSchema,
    BasketDetailSchema,
    BasketItemChangeSchema,
    BasketItemSchema,
)


class Basket(BasketDataSchema, TenantUserEntity):
    items: dict[str, BasketItemSchema] = Field(default_factory=dict)

    @property
    def subtotal(self) -> Decimal:
        total = Decimal(
            sum(
                item.price * item.exchange_fee(self.currency)
                for item in self.items.values()
            )
        )
        return total

    @property
    def amount(self) -> Decimal:
        if self.discount:
            return self.subtotal - self.discount.discount
        return self.subtotal

    @property
    def description(self) -> str:
        return f"basket id = {self.uid} - total price = {self.subtotal}"

    async def add_basket_item(
        self, item: BasketItemSchema, exclusive: bool = False
    ) -> None:
        item_dict = item.model_dump(exclude=["uid", "quantity"])

        if exclusive:
            self.items.clear()

        for existing_item in self.items.values():
            if existing_item.model_dump(exclude=["uid", "quantity"]) == item_dict:
                existing_item.quantity += item.quantity
                await self.save()
                return

        self.items[item.uid] = item
        await self.save()

    async def update_basket_item(
        self, item_id: str, data: BasketItemChangeSchema, **kwargs: object
    ) -> None:
        basket_item: BasketItemSchema | None = self.items.get(item_id)

        if basket_item is None:
            if kwargs.get("raise_error"):
                return
            raise ValueError(f"Item with id {item_id} not found in the basket.")

        if data.new_quantity:
            basket_item.quantity = data.new_quantity
        else:
            basket_item.quantity = basket_item.quantity + data.quantity_change

        if basket_item.quantity <= 0:
            self.items.pop(item_id)

        await self.save()

    async def delete_basket_item(self, item_id: str) -> None:
        self.items.pop(item_id, None)
        await self.save()

    @property
    def detail(self) -> BasketDetailSchema:
        return BasketDetailSchema.model_validate(
            self.model_dump(exclude={"items"})
            | {
                "items": list(self.items.values()),
                "amount": self.amount,
                "subtotal": self.subtotal,
            }
        )
