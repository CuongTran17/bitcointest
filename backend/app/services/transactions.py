from decimal import Decimal

from sqlalchemy.orm import Session

from app.bitcoin_rpc import BitcoinRpcClient, btc_to_sats
from app.models import AppTransaction, WalletAddress
from app.schemas import FaucetRead, FaucetRequest, SendTransactionRead, SendTransactionRequest, TransactionRead
from app.services.wallets import find_wallet_by_address


def format_btc(amount: Decimal) -> str:
    return f"{amount:.8f}"


def record_app_transaction(
    db: Session,
    txid: str,
    from_wallet: str,
    to_wallet: str | None,
    to_address: str,
    amount_sats: int,
) -> AppTransaction:
    existing = db.query(AppTransaction).filter(AppTransaction.txid == txid).one_or_none()
    if existing is not None:
        return existing

    transaction = AppTransaction(
        txid=txid,
        from_wallet=from_wallet,
        to_wallet=to_wallet,
        to_address=to_address,
        amount_sats=amount_sats,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def remember_wallet_address(db: Session, wallet_name: str, address: str) -> None:
    existing = db.query(WalletAddress).filter(WalletAddress.address == address).one_or_none()
    if existing is None:
        db.add(WalletAddress(address=address, wallet_name=wallet_name))
        db.commit()


def send_transaction(payload: SendTransactionRequest, db: Session) -> SendTransactionRead:
    txid = BitcoinRpcClient().send_to_address(payload.from_wallet, payload.to_address, payload.amount_btc)
    to_wallet = find_wallet_by_address(payload.to_address, db)
    amount_sats = btc_to_sats(payload.amount_btc)
    record_app_transaction(db, txid, payload.from_wallet, to_wallet, payload.to_address, amount_sats)
    return SendTransactionRead(
        txid=txid,
        from_wallet=payload.from_wallet,
        to_wallet=to_wallet,
        to_address=payload.to_address,
        amount_btc=format_btc(payload.amount_btc),
        amount_sats=amount_sats,
    )


def fund_from_faucet(wallet_name: str, payload: FaucetRequest, db: Session) -> FaucetRead:
    rpc = BitcoinRpcClient()
    address = rpc.get_new_address(wallet_name)
    txid = rpc.send_to_address("miner", address, payload.amount_btc)
    remember_wallet_address(db, wallet_name, address)
    amount_sats = btc_to_sats(payload.amount_btc)
    record_app_transaction(db, txid, "miner", wallet_name, address, amount_sats)
    block_hashes = rpc.mine_blocks("miner", 1)
    return FaucetRead(
        txid=txid,
        from_wallet="miner",
        to_wallet=wallet_name,
        to_address=address,
        amount_btc=format_btc(payload.amount_btc),
        amount_sats=amount_sats,
        block_hashes=block_hashes,
    )


def list_transactions(wallet_name: str, db: Session) -> list[TransactionRead]:
    rows = BitcoinRpcClient().list_transactions(wallet_name, count=20)
    txids = [row["txid"] for row in rows]
    metadata_by_txid = {
        transaction.txid: transaction
        for transaction in db.query(AppTransaction).filter(AppTransaction.txid.in_(txids)).all()
    }
    transactions: list[TransactionRead] = []
    for row in rows:
        amount = Decimal(str(row["amount"]))
        confirmations = int(row.get("confirmations", 0))
        metadata = metadata_by_txid.get(row["txid"])
        transactions.append(
            TransactionRead(
                txid=row["txid"],
                from_wallet=metadata.from_wallet if metadata is not None else None,
                to_wallet=metadata.to_wallet if metadata is not None else None,
                category=row["category"],
                amount_btc=format_btc(amount),
                amount_sats=btc_to_sats(amount),
                confirmations=confirmations,
                status="confirmed" if confirmations > 0 else "pending",
                time=row.get("time"),
                blockhash=row.get("blockhash"),
                address=row.get("address"),
            )
        )
    return transactions
