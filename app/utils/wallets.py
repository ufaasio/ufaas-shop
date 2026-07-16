"""Wallet utilities."""

from ufaas.services import AccountingClient
from ufaas.wallet import WalletDetailSchema


async def get_wallets(
    client: AccountingClient, user_id: str
) -> list[WalletDetailSchema]:
    """Get all wallets for a user."""
    return await client.get_wallets(owner_id=user_id)


async def get_or_create_user_wallet(
    client: AccountingClient, user_id: str
) -> WalletDetailSchema:
    """Get the default user wallet or create one if it does not exist."""
    wallets = await client.get_wallets(owner_id=user_id)
    for wallet in wallets:
        if wallet.is_default:
            return wallet

    response = await client.post(
        url="/wallets",
        json={"user_id": user_id},
    )
    response.raise_for_status()
    return WalletDetailSchema.model_validate(response.json())
