from .models import Basket


async def reserve_basket(basket: Basket):
    basket.status = "reserve"

    for item in basket.items.values():
        if item.reserve_url:
            raise ValueError("Product validation failed")

    await basket.save()


async def validate_basket(basket: Basket):
    for item in basket.items.values():
        if not await item.validate_product():
            raise ValueError("Product validation failed")


async def webhook_basket(basket: Basket):
    for item in basket.items.values():
        await item.webhook_product()


async def cancel_basket(basket: Basket):
    basket.status = "cancel"
    await basket.save()

    for item in basket.items.values():
        await item.webhook_product()


async def create_payment_detail(basket: Basket):
    # Create payment detail
    pass


async def purchase_basket(basket: Basket):
    pass


async def checkout_basket(basket: Basket):
    pass
