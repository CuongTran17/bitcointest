from decimal import Decimal

from sqlalchemy.orm import Session

from app.bitcoin_rpc import BitcoinRpcClient, btc_to_sats
from app.models import WalletAddress
from app.schemas import AddressRead, BalanceRead


def format_btc(amount: Decimal) -> str:
    return f"{amount:.8f}"


def create_address(wallet_name: str, db: Session) -> AddressRead:
    address = BitcoinRpcClient().get_new_address(wallet_name)
    existing = db.query(WalletAddress).filter(WalletAddress.address == address).one_or_none()
    if existing is None:
        db.add(WalletAddress(address=address, wallet_name=wallet_name))
        db.commit()
    return AddressRead(wallet_name=wallet_name, address=address)


def find_wallet_by_address(address: str, db: Session) -> str | None:
    wallet_address = db.query(WalletAddress).filter(WalletAddress.address == address).one_or_none()
    if wallet_address is None:
        return None
    return wallet_address.wallet_name


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
