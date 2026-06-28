from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enum import CurrencyEnum


class Operation(Base):
    __tablename__ = "operation"

    id: Mapped[int] = mapped_column(primary_key=True)
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallet.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str]
    amount: Mapped[Decimal]
    currency: Mapped[CurrencyEnum]
    category: Mapped[str | None] = mapped_column(default=None)
    subcategory: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    wallet: Mapped["Wallet"] = relationship(back_populates="operations")


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(unique=True)

    wallets: Mapped[list["Wallet"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class Wallet(Base):
    __tablename__ = "wallet"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    balance: Mapped[Decimal]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    currency: Mapped[CurrencyEnum]

    user: Mapped["User"] = relationship(back_populates="wallets")
    operations: Mapped[list["Operation"]] = relationship(
        back_populates="wallet", cascade="all, delete-orphan", passive_deletes=True
    )
