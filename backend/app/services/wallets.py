from decimal import Decimal

from app.bitcoin_rpc import BitcoinRpcClient, btc_to_sats
from app.schemas import AddressRead, BalanceRead


def format_btc(amount: Decimal) -> str:
    return f"{amount:.8f}"


def create_address(wallet_name: str) -> AddressRead:
    address = BitcoinRpcClient().get_new_address(wallet_name)
    return AddressRead(wallet_name=wallet_name, address=address)


def get_balance(wallet_name: str) -> BalanceRead:
    balances = BitcoinRpcClient().get_balances(wallet_name)
    return BalanceRead(
        wallet_name=wallet_name,
        confirmed_balance_btc=format_btc(balances["confirmed"]),
        unconfirmed_balance_btc=format_btc(balances["unconfirmed"]),
        total_balance_btc=format_btc(balances["total"]),
        confirmed_balance_sats=btc_to_sats(balances["confirmed"]),
        unconfirmed_balance_sats=btc_to_sats(balances["unconfirmed"]),
        total_balance_sats=btc_to_sats(balances["total"]),
    )
