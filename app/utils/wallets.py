from ufaas.services import AccountingClient
from ufaas.wallet import WalletDetailSchema

from server.config import Settings


async def get_wallets(
    client: AccountingClient, user_id: str
) -> list[WalletDetailSchema]:
    response = await client.get(
        url=f"{Settings.core_url}/api/accounting/v1/wallets",
        params={"user_id": user_id},
    )
    response.raise_for_status()
    wallets: dict[str, object] = response.json()
    return [
        WalletDetailSchema.model_validate(wallet) for wallet in wallets.get("items", [])
    ]


async def get_or_create_user_wallet(
    client: AccountingClient, user_id: str
) -> WalletDetailSchema:
    wallets = await get_wallets(client, user_id)
    for wallet in wallets:
        if wallet.is_default:
            return wallet

    response = await client.post(
        url=f"{Settings.core_url}/api/accounting/v1/wallets",
        json={"user_id": user_id},
    )
    response.raise_for_status()
    return WalletDetailSchema.model_validate(response.json())
