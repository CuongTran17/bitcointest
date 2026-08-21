from decimal import Decimal

from app.bitcoin_rpc import BitcoinRpcClient, btc_to_sats
from app.schemas import UtxoRead, UtxoSummaryRead


def format_btc(amount: Decimal) -> str:
    return f"{amount:.8f}"


def list_utxos(wallet_name: str) -> UtxoSummaryRead:
    rows = BitcoinRpcClient().list_unspent(wallet_name, min_conf=0, max_conf=9999999)
    normalized = []
    for row in rows:
        amount = Decimal(str(row["amount"]))
        normalized.append(
            UtxoRead(
                txid=row["txid"],
                vout=int(row["vout"]),
                address=row.get("address"),
                amount_btc=format_btc(amount),
                amount_sats=btc_to_sats(amount),
                confirmations=int(row.get("confirmations", 0)),
                spendable=bool(row.get("spendable", False)),
                solvable=bool(row.get("solvable", False)),
                safe=bool(row.get("safe", False)),
            )
        )

    normalized.sort(
        key=lambda item: (
            item.confirmations == 0,
            -item.amount_sats,
            item.txid,
            item.vout,
        )
    )
    confirmed_count = sum(item.confirmations > 0 for item in normalized)
    total_sats = sum(item.amount_sats for item in normalized)
    return UtxoSummaryRead(
        wallet_name=wallet_name,
        utxo_count=len(normalized),
        confirmed_count=confirmed_count,
        unconfirmed_count=len(normalized) - confirmed_count,
        total_amount_btc=format_btc(Decimal(total_sats) / Decimal("100000000")),
        total_amount_sats=total_sats,
        utxos=normalized,
    )
