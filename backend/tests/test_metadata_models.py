from app.models import AppTransaction, WalletAddress


def test_metadata_models_have_unique_lookup_fields():
    assert WalletAddress.__table__.columns.address.unique is True
    assert AppTransaction.__table__.columns.txid.unique is True
    assert AppTransaction.__table__.columns.amount_sats.type.python_type is int
