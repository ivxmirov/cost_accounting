from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enum import (
    CurrencyEnum,
    OperationType,
    WalletType,
    currency_type_enum,
    operation_type_enum,
    wallet_type_enum,
)


class Operation(Base):
    __tablename__ = "operations"
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[UUID] = mapped_column(unique=True, nullable=False, index=True)
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[OperationType] = mapped_column(operation_type_enum, nullable=False)
    amount: Mapped[Decimal]
    currency: Mapped[CurrencyEnum] = mapped_column(currency_type_enum, nullable=False)
    category: Mapped[str | None] = mapped_column(default=None)
    subcategory: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.now, server_default=func.now(), nullable=False
    )
    wallet: Mapped["Wallet"] = relationship(back_populates="operations")


group_members = Table(
    "group_members",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    wallets: Mapped[list["Wallet"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    groups: Mapped[list["Group"]] = relationship(secondary=group_members, back_populates="members")


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    creator: Mapped[int] = mapped_column(
        ForeignKey(column="users.id", ondelete="CASCADE"), nullable=False
    )
    members: Mapped[list["User"]] = relationship(secondary=group_members, back_populates="groups")


class Wallet(Base):
    __tablename__ = "wallets"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    balance: Mapped[Decimal]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    currency: Mapped[CurrencyEnum] = mapped_column(currency_type_enum, nullable=False)
    user: Mapped["User"] = relationship(back_populates="wallets")
    operations: Mapped[list["Operation"]] = relationship(
        back_populates="wallet", cascade="all, delete-orphan", passive_deletes=True
    )
    type: Mapped[WalletType] = mapped_column(wallet_type_enum, nullable=False)
    credit_limit: Mapped[Decimal | None] = mapped_column(nullable=True)
