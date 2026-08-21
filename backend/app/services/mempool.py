from decimal import Decimal

from sqlalchemy.orm import Session

from app.bitcoin_rpc import BitcoinRpcClient, BitcoinRpcError, btc_to_sats
from app.models import AppTransaction, WalletAddress
from app.schemas import MempoolSummaryRead, MempoolTransactionRead


def format_btc(amount: Decimal) -> str:
    return f"{amount:.8f}"


def format_fee_rate(fee_sats: int, vsize: int) -> str | None:
    if vsize <= 0:
        return None
    return f"{Decimal(fee_sats) / Decimal(vsize):.8f}"


def output_addresses(raw_transaction: dict) -> list[str]:
    addresses = []
    for output in raw_transaction.get("vout", []):
        script = output.get("scriptPubKey", {})
        address = script.get("address")
        candidates = [address] if isinstance(address, str) else script.get("addresses", [])
        for address in candidates:
            if address not in addresses:
                addresses.append(address)
    return addresses


def list_mempool_transactions(db: Session) -> MempoolSummaryRead:
    rpc = BitcoinRpcClient()
    raw_entries = rpc.get_raw_mempool(verbose=True)
    if not raw_entries:
        return MempoolSummaryRead(
            transaction_count=0,
            total_vsize=0,
            total_fee_btc="0.00000000",
            total_fee_sats=0,
            transactions=[],
        )

    txids = list(raw_entries)
    metadata_by_txid = {
        row.txid: row
        for row in db.query(AppTransaction).filter(AppTransaction.txid.in_(txids)).all()
    }
    known_addresses = {
        row.address: row.wallet_name
        for row in db.query(WalletAddress).all()
    }

    transactions = []
    for txid, entry in raw_entries.items():
        fee_value = entry.get("fees", {}).get("base", entry.get("fee", "0"))
        fee_btc = Decimal(str(fee_value))
        fee_sats = btc_to_sats(fee_btc)
        vsize = int(entry.get("vsize", 0))
        try:
            raw_transaction = rpc.get_raw_transaction(txid, verbosity=1)
        except BitcoinRpcError as exc:
            if exc.status_code == 404:
                continue  # The transaction left the mempool after the snapshot.
            raise
        addresses = output_addresses(raw_transaction)
        metadata = metadata_by_txid.get(txid)
        mapped_wallets = {known_addresses[address] for address in addresses if address in known_addresses}
        inferred_wallet = next(iter(mapped_wallets)) if len(mapped_wallets) == 1 else None
        inferred_address = next(
            (address for address in addresses if known_addresses.get(address) == inferred_wallet),
            None,
        )
        to_wallet = metadata.to_wallet if metadata is not None else inferred_wallet
        to_address = metadata.to_address if metadata is not None else inferred_address
        transactions.append(
            MempoolTransactionRead(
                txid=txid,
                wtxid=entry.get("wtxid"),
                vsize=vsize,
                weight=int(entry.get("weight", 0)),
                fee_btc=format_btc(fee_btc),
                fee_sats=fee_sats,
                fee_rate_sat_vb=format_fee_rate(fee_sats, vsize),
                time=entry.get("time"),
                entry_height=entry.get("height"),
                confirmations=0,
                from_wallet=metadata.from_wallet if metadata is not None else None,
                to_wallet=to_wallet,
                to_address=to_address,
                status="pending",
                ancestor_count=int(entry.get("ancestorcount", 0)),
                descendant_count=int(entry.get("descendantcount", 0)),
                depends=list(entry.get("depends", [])),
                spent_by=list(entry.get("spentby", [])),
                replaceable=bool(entry.get("bip125-replaceable", False)),
                unbroadcast=bool(entry.get("unbroadcast", False)),
                output_addresses=addresses,
            )
        )

    transactions.sort(key=lambda item: (-(item.time or 0), item.txid))
    total_fee_sats = sum(item.fee_sats for item in transactions)
    return MempoolSummaryRead(
        transaction_count=len(transactions),
        total_vsize=sum(item.vsize for item in transactions),
        total_fee_btc=format_btc(Decimal(total_fee_sats) / Decimal("100000000")),
        total_fee_sats=total_fee_sats,
        transactions=transactions,
    )
