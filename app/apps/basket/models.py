import uuid
from decimal import Decimal
from typing import Literal

from fastapi_mongo_base.models import BusinessOwnedEntity

from .schemas import (
    BasketDataSchema,
    BasketDetailSchema,
    BasketItemSchema,
    BasketItemChangeSchema,
)


class Basket(BasketDataSchema, BusinessOwnedEntity):
    items: dict[uuid.UUID, BasketItemSchema] = {}

    class Settings:
        indexes = BusinessOwnedEntity.Settings.indexes

    @property
    def subtotal(self):
        total = sum(
            [
                item.price * item.exchange_fee(self.currency)
                for item in self.items.values()
            ]
        )
        return total

    @property
    def amount(self):
        if self.discount:
            return self.subtotal - self.discount.discount
        return self.subtotal

    @property
    def description(self):
        return f"basket id = {self.uid} - total price = {self.subtotal}"

    @classmethod
    def get_query(
        cls,
        user_id: uuid.UUID = None,
        business_name: str = None,
        is_deleted: bool = False,
        status: (
            Literal["active", "inactive", "paid", "reserve", "cancel"] | None
        ) = None,
        *args,
        **kwargs,
    ):
        query = super().get_query(user_id, business_name, is_deleted, *args, **kwargs)
        if status:
            query.find({"status": status})
        return query

    async def add_basket_item(self, item: BasketItemSchema):
        item_dict = item.model_dump(exclude=["uid", "quantity"])
        for existing_item in self.items.values():
            if existing_item.model_dump(exclude=["uid", "quantity"]) == item_dict:
                existing_item.quantity += item.quantity
                await self.save()
                return

        self.items[item.uid] = item
        await self.save()

    async def update_basket_item(
        self, item_id: uuid.UUID, data: BasketItemChangeSchema, **kwargs
    ):
        basket_item = self.items.get(item_id)

        if basket_item is None:
            if kwargs.get("raise_error", False):
                return
            raise ValueError(f"Item with id {item_id} not found in the basket.")

        if data.new_quantity:
            basket_item.quantity = data.new_quantity
        else:
            basket_item.quantity = basket_item.quantity + data.quantity_change

        if basket_item.quantity <= 0:
            self.items.pop(item_id)
        
        await self.save()

    async def delete_basket_item(self, item_id: uuid.UUID):
        self.items.pop(item_id, None)
        await self.save()

    @property
    def detail(self) -> BasketDetailSchema:
        return BasketDetailSchema(
            **self.model_dump(exclude={"items"}),
            items=list(self.items.values()),
            amount=self.amount,
            subtotal=self.subtotal,
        )
