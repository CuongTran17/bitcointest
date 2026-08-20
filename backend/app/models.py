from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    wallet_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)


class WalletAddress(Base):
    __tablename__ = "wallet_addresses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    address: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    wallet_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AppTransaction(Base):
    __tablename__ = "app_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    txid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    from_wallet: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    to_wallet: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    to_address: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    amount_sats: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
