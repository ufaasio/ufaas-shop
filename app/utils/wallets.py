"""Wallet utilities."""

from ufaas.services import AccountingClient
from ufaas.wallet import WalletDetailSchema


async def get_wallets(
    client: AccountingClient, owner_id: str
) -> list[WalletDetailSchema]:
    """Get all wallets for an owner (workspace)."""
    return await client.get_wallets(owner_id=owner_id)


async def get_or_create_owner_wallet(
    client: AccountingClient, owner_id: str
) -> WalletDetailSchema:
    """Get the default wallet for an owner (workspace) or create one."""
    wallets = await client.get_wallets(owner_id=owner_id)
    for wallet in wallets:
        if wallet.is_default:
            return wallet

    response = await client.post(
        url="/wallets",
        json={"owner_id": owner_id},
    )
    response.raise_for_status()
    return WalletDetailSchema.model_validate(response.json())
